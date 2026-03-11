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

1. Define the profile and project name to be used for deployment:

   ```bash
   export AWS_PROFILE=<your-aws-profile>
   export NAMESPACE=<your-namespace>
   ```

2. Set up Kubernetes context (example for EKS):

   ```bash
   aws eks update-kubeconfig --region <your-aws-region> --name <your-eks-cluster-name>
   ```

3. Prepare values.json for Helm (example). Note some keys are environment-prefixed:

    ```json
    {
        "dev_aws_account_id": {
            "value": "<your-account-id>"
        },
        "dev_private_ca_arn": {
            "value": "<your-private-ca-arn>"
        },
        "dev_rds_secret_name_map": { 
            "value": {
                 "<your-service-name>": "<your-service-rds-secret>" 
            } 
        },
        "dev_vpc_id": {
            "value": "<your-vpc-id>"
        }
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

- Update variables in `terraform.tfvars` (project_name, region, profile, GitHub connection details, and infra_credentials) before applying. Create a local `terraform.tfvars` file if it does not exist and ensure it is not checked into version control.
