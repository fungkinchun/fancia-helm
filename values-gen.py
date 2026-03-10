import json
import yaml
import os
import argparse
from pathlib import Path

def snake_to_camel(s: str) -> str:
    parts = s.split('_')
    return (
        parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])
        if parts
        else s
    )

def camel_to_snake(s: str) -> str:
    result = []
    for char in s:
        if char.isupper() and result:
            result.append('_')
        result.append(char.lower())
    return ''.join(result)

def upper_snake_to_camel(s: str) -> str:
    parts = s.split('_')
    return ''.join(p.capitalize() for p in parts) if parts else s

def camel_to_upper_snake(s: str) -> str:
    result = []
    for char in s:
        if char.isupper() and result:
            result.append('_')
        result.append(char.upper())
    return ''.join(result)

def load_tf_outputs(path: Path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Terraform outputs file not found at {path}")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: could not decode JSON from {path}")
        exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Generate Helm values from Terraform outputs (tf_outputs.json).'
    )
    parser.add_argument(
        '--var-file', type=Path, default=Path('tf_outputs.json'),
        help='Path to tf_outputs.json'
    )
    parser.add_argument(
        '--out-dir', type=Path, default=Path('.'),
        help='Path to output values.json and values.yaml (default: current directory)'
    )
    args = parser.parse_args()

    input_path = Path(args.var_file)
    out_path = Path(args.out_dir)

    if input_path.is_file():
        tf_path = input_path
    else:
        print(f"Error: provided path does not exist: {input_path}")
        exit(1)

    tf_outputs = load_tf_outputs(tf_path)
    out_path.mkdir(parents=True, exist_ok=True)

    values = {}
    keys_to_extract = ['environment', 'projectName', 'awsAccountId', 'awsRegion']
    for key in keys_to_extract:
        upper_snake_key = camel_to_upper_snake(key)
        try:
            values[key] = os.environ[upper_snake_key]
        except KeyError:
            try:
                snake_key = camel_to_snake(key)
                values[key] = tf_outputs[snake_key]['value']
            except Exception:
                if key == 'environment':
                    print(
                        f"Error: {upper_snake_key} not found in environment variables or tf_outputs. 'environment' is required to map other values."
                    )
                    exit(1)
                print(
                    f"Warning: {upper_snake_key} not found in environment variables or tf_outputs."
                )

    env_keys_to_extract = ['vpcId', 'privateCaArn', 'acmCertificateArn']
    for key in env_keys_to_extract:
        snake_key = camel_to_snake(key)
        map_key = f"{values.get('environment','')}_{snake_key}"
        try:
            values[key] = tf_outputs[map_key]['value']
        except Exception:
            print(f"Warning: {map_key} not found in tf_outputs.")

    values["repositories"] = []
    rds_name_map_key = f"{values.get('environment','')}_rds_secret_name_map"
    if (
        rds_name_map_key in tf_outputs
        and isinstance(tf_outputs[rds_name_map_key].get('value'), dict)
    ):
        for idx, (k, v) in enumerate(tf_outputs[rds_name_map_key]["value"].items()):
            values["repositories"].append({
                "name": k,
                "databaseSecretName": v,
                "port": 8080 + idx,
                "imageVersion": "latest",
            })
    else:
        print(f"Warning: {rds_name_map_key} not found or not a map in tf_outputs.")

    # Write JSON
    json_output = json.dumps(values, indent=2)
    json_path = out_path / 'values.json'
    with open(json_path, 'w') as f:
        f.write(json_output)
    print(f"values.json generated successfully at {json_path}.")

    # Write YAML
    yaml_output = yaml.dump(values, default_flow_style=False)
    yaml_path = out_path / 'values.yaml'
    with open(yaml_path, 'w') as f:
        f.write(yaml_output)
    print(f"values.yaml generated successfully at {yaml_path}.")

if __name__ == '__main__':
    main()