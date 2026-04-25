# Fancia

Fancia is a social platform connecting people with shared interests for offline, in-person group gatherings and community building.

## infra-helm

This repository contains Helm charts for provisioning Fancia services on Kubernetes clusters.

### IMPORTANT

- It is recommended to use fancia-infra-pipeline to deploy the infrastructure and manage releases in CI/CD.

- The `prod` environment enables AWS-managed services (for example AWS Private Certificate Authority) that can incur significant recurring costs (Private CA ~£300/month). Only enable `prod` for true production deployments after reviewing costs; consider alternatives such as cert-manager with Let's Encrypt or re-using an existing ACM certificate to avoid or reduce those charges.

### Prerequisites

- AWS CLI installed and configured for the target account and profile
- kubectl configured for the target cluster
- Helm installed

### Quick start (local deployment)

1. Define the profile and namespace (e.g. $PROJECT_NAME-$ENVIRONMENT) to be used for deployment:

   ```bash
   export AWS_PROFILE=<your-aws-profile>
   export NAMESPACE=<your-namespace>
   ```

2. Set up Kubernetes context (example for EKS):

   ```bash
   aws eks update-kubeconfig --region <your-aws-region> --name <your-eks-cluster-name>
   ```

3. Prepare values.json for Helm (example).

    ```json
    {
        "awsAccountId": "<your-aws-account-id>",
        "domainName": "<your-dev-domain>",
        "vpcId": "<your-vpc-id>",
        "acmCertificateArn": "<your-acm-certificate-arn>",
        "repositories": [
            {
                "name": "<your-next-service-name>",
                "databaseSecretName": "<your-rds-secret-name-for-this-service>",
                "port": "<your-port>",
                "imageVersion": "<your-image-tag>"
            }
        ]
    }
    ```

4. Execute values-gen.py which generates a values.yaml file in the main-chart directory to be used as Helm input:

   ```bash
   python3 values-gen.py --out-dir=<your-output-dir>
   ```

    ```bash
    --var-file VAR_FILE  Path to tf_outputs.json
    --out-dir OUT_DIR    Path to output values.json and values.yaml (default: current directory)
    ```

5. Deploy the Helm charts:

    ```bash
    helm upgrade --install "$NAMESPACE" ./main-chart --namespace "$NAMESPACE" --create-namespace
    ```

### Notes

- The `--take-ownership` flag is used because Helm adds ownership annotations to CRDs during installation. Without it, the install fails if the CRD already exists with different metadata.
For example, you might see this error if the CRD was previously deployed to a different namespace:

    ```text
    Error: Unable to continue with install: ... invalid ownership metadata; annotation validation error: key "meta.helm.sh/release-namespace" must equal "fancia-dev": current value is "fancia"
    ```

    By using `--take-ownership`, Helm overwrites the existing annotations and adopts the resource into the current release.

- Before running helm install, we execute `kubectl rollout restart deployment aws-load-balancer-controller`. This triggers a fresh reconciliation loop, ensuring the controller immediately processes any recent changes, such as updated ACM certificates.

- `cert-manager` is a prerequisite, the `aws-privateca-issuer` enables it to interface with AWS Private CA to fulfill and sign certificate requests.

- If you change a domain or update certificates you may see `terraform apply` hang while destroying `aws_acm_certificate`. This often happens because the ALB keeps the previous certificate as the Default SSL/TLS server certificate even after you remove or change the `alb.ingress.kubernetes.io/certificate-arn` annotation on the Ingress.

  Cause: the `alb.ingress.kubernetes.io/certificate-arn` annotation is evaluated by the AWS Load Balancer Controller at Ingress creation time. Updating the annotation on an existing Ingress does not always update the ALB listener in-place, so the old certificate can remain associated with the ALB and block Terraform from deleting it.

  Remediation and best practices:
  - Recreate the Ingress so the controller applies the new certificate: `kubectl delete -f ingress.yaml && kubectl apply -f ingress.yaml` (or remove and re-create the resource). This ensures the controller provisions the desired certificate on the ALB listener.
  - Alternatively, update the ALB listener directly with the AWS CLI (e.g. `aws elbv2 modify-listener --listener-arn <arn> --certificates CertificateArn=<new-arn>`), then re-run Terraform.
  - Restart the aws-load-balancer-controller (`kubectl rollout restart deployment aws-load-balancer-controller`) to force reconciliation if changes are not picked up.
  - Use `alb.ingress.kubernetes.io/group.name` when you have multiple Ingress resources behind the same ALB; this enables safer certificate swaps and coordinated updates.
  - As a last resort, manually remove the ALB listener or the ALB (with caution) before running `terraform apply` if the certificate cannot be detached automatically.

  These steps help avoid Terraform timeout issues by ensuring the ALB listener is updated or recreated with the correct certificate before Terraform attempts to destroy the ACM resource.

- In this project Kafka listeners do not use TLS — TLS is terminated at the AWS ALB. To enable TLS on the Kafka cluster itself (Strimzi) set the external listener's `tls: true`.

    ```yaml
    apiVersion: kafka.strimzi.io/v1
    kind: Kafka
    spec:
      kafka:
        listeners:
          - name: external
            type: loadbalancer
            tls: true
    ```

  What Strimzi creates:
  - Strimzi generates a cluster CA and stores it in a Kubernetes Secret (example name: `<your-namespace>-kafka-cluster-ca-cert`). The secret typically contains:
    - `ca.crt` — PEM encoded CA certificate
    - `ca.p12` — PKCS#12 truststore (binary, base64)
    - `ca.password` — password for the PKCS#12 (base64)

  Inspect the secret:

    ```bash
    kubectl -n <your-namespace> get secret <your-namespace>-kafka-cluster-ca-cert -o yaml
    ```

  Export the PKCS#12 truststore and decode the password:

    ```bash
    kubectl -n <your-namespace> get secret <your-namespace>-kafka-cluster-ca-cert -o jsonpath='{.data.ca\.p12}' | base64 -d > ca.p12
    kubectl -n <your-namespace> get secret <your-namespace>-kafka-cluster-ca-cert -o jsonpath='{.data.ca\.password}' | base64 -d
    ```

  Spring Boot `application.yaml` using the PKCS12 truststore:

    ```yaml
    spring:
      kafka:
        properties:
          security.protocol: SSL
          ssl.truststore.location: ca.p12
          ssl.truststore.password: <decoded-ca.password>
          ssl.truststore.type: PKCS12
    ```

  - If you use the PEM CA (`ca.crt`), you may convert it to a PKCS12 or JKS truststore if required by your client.

- Minimal steps to use Spring Cloud OpenFeign
  - Add the OpenFeign dependency to your project (Maven or Gradle). Example (Maven):

    ```xml
    <dependency>
      <groupId>org.springframework.cloud</groupId>
      <artifactId>spring-cloud-starter-openfeign</artifactId>
    </dependency>
    ```

  - Enable Feign clients in your application by placing the annotation on the main application class or a configuration class:

    ```java
    @SpringBootApplication
    @EnableFeignClients
    public class Application { ... }
    ```

  - Define a Feign client interface. Example:

    ```java
    @FeignClient(name = "example-service", path = "/example/api")
    public interface ExampleServiceClient {
    }
    ```

  - Configure client settings in application.yaml. If you use Kubernetes service discovery, enable discovery; otherwise provide explicit URLs for clients.

    ```yaml
    cloud:
        kubernetes:
            discovery:
                enabled: true
        openfeign:
            autoconfiguration:
                jackson:
                    enabled: true
        client:
            config:
                example-service:
                    url: ${EXAMPLE_SERVICE_URL:#{null}}
    ```

- When an Ingress address (ALB) changes, the existing Route53 record may continue pointing to the old ALB.

ExternalDNS uses TXT ownership records to determine which DNS entries it can manage. If an A/ALIAS record exists without a matching TXT owner (or with a different owner), external-dns will not overwrite it.

Use `--set txtPrefix=external-dns-` (or set `txtPrefix: "external-dns-"` in Helm values) to ensure proper ownership tracking and propagation.  

Alternatively, manually delete the stale `A` and `AAAA` records in Route 53. ExternalDNS will then recreate them pointing to the new ALB.

- This project uses KEDA (Kubernetes Event-driven Autoscaling) to automatically scale down infrastructure during non-business hours to reduce costs. This is particularly useful for demo and development environments where 24/7 availability is not required. 

  To disable autoscaling for a specific deployment, add the following annotation to the ScaledObject:

  ```yaml
  apiVersion: keda.sh/v1alpha1
  kind: ScaledObject
  metadata:
    annotations:
      autoscaling.keda.sh/paused: "true"
  ```

  After pausing KEDA, manually scale the deployment to maintain a minimum number of replicas:

  ```bash
  kubectl -n <your-namespace> scale deployment <your-deployment-name> --replicas=1
  ```

  This pauses the KEDA scaler without removing the ScaledObject configuration, allowing you to re-enable scaling later by removing the annotation.
