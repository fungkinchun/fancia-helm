#!/usr/bin/env bash
# Bump imageVersion for a service in main-chart/values.yaml (static) after ECR push.
# Usage: REPO_NAME=auth IMAGE_TAG=abc1234 ./scripts/bump-image-version.sh
set -euo pipefail

REPO_NAME="${REPO_NAME:?REPO_NAME is required}"
IMAGE_TAG="${IMAGE_TAG:?IMAGE_TAG is required}"
VALUES_FILE="${VALUES_FILE:-main-chart/values.yaml}"

if ! command -v yq >/dev/null 2>&1; then
  echo "Error: yq is required"
  exit 1
fi

yq -i ".services.${REPO_NAME}.imageVersion = \"${IMAGE_TAG}\"" "${VALUES_FILE}"
echo "Updated services.${REPO_NAME}.imageVersion to ${IMAGE_TAG} in ${VALUES_FILE}"
