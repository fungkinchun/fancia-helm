import json
import os

def snake_to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:]) if parts else s

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



try:
    with open('tf_outputs.json', 'r') as f:
        tf_outputs = json.load(f)
except FileNotFoundError:
    print("tf_outputs.json not found.")
    exit(1)
except json.JSONDecodeError:
    print("Error decoding tf_outputs.json.")
    exit(1)

print(tf_outputs)

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
        except KeyError:
            print(f"Warning: {upper_snake_key} not found in environment variables.")
env_keys_to_extract = ['defaultVpcId']
for key in env_keys_to_extract:
    snake_key = camel_to_snake(key)
    map_key = f"{values['environment']}_{snake_key}"
    try:
        values[key] = tf_outputs[map_key]['value']
    except KeyError:
        print(f"Warning: {map_key} not found in tf_outputs.")

values["repositories"] = []
rds_name_map_key = f"{values['environment']}_rds_secret_name_map"
for idx,(k,v) in enumerate(tf_outputs[rds_name_map_key]["value"].items()):
    values["repositories"].append({
        "name": k,
        "databaseSecretName": v,
        "port": 8080 + idx,
        "imageVersion": "latest"
    })

json_output = json.dumps(values, indent=2)
with open('./main-chart/values.json', 'w') as f:
    f.write(json_output)
print("values.json generated successfully.")