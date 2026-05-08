#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "WARNING: This will destroy ALL Konsultacije CDK stacks (DynamoDB data will be lost!)."
read -r -p "Type 'destroy' to continue: " confirm
if [ "$confirm" != "destroy" ]; then
  echo "Aborted."
  exit 1
fi

pushd "$ROOT_DIR/infra" > /dev/null
# shellcheck disable=SC1091
source .venv/bin/activate
cdk destroy --all --force
popd > /dev/null

echo "==> Teardown complete."
