# Fancia

Fancia is a social platform connecting people with shared interests for offline, in-person group gatherings and community building.

## infra-helm

This repository contains Helm charts for provisioning Fancia services on Kubernetes clusters.

### IMPORTANT

It is recommended to use fancia-infra-pipeline to deploy the infrastructure and manage releases in CI/CD.

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
        "privateCaArn": "<your-private-ca-arn>",
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

-- Before running helm install, we execute `kubectl rollout restart deployment aws-load-balancer-controller`. This triggers a fresh reconciliation loop, ensuring the controller immediately processes any recent changes, such as updated ACM certificates.

-- `cert-manager` is a prerequisite, the `aws-privateca-issuer` enables it to interface with AWS Private CA to fulfill and sign certificate requests.
