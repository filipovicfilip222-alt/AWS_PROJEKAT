#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-eu-central-1}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> 1/3 Building frontend"
pushd "$ROOT_DIR/frontend" > /dev/null
npm install
npm run build
popd > /dev/null

echo "==> 2/3 CDK deploy (region=$REGION)"
pushd "$ROOT_DIR/infra" > /dev/null
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
cdk deploy --all --require-approval never
popd > /dev/null

echo "==> 3/3 Done. Check CloudFront URL in CDK outputs."
