#!/usr/bin/env python3
"""CDK entry point za Konsultacije aplikaciju.

Stack-ovi se kreiraju u ovom redosledu:
  1. data       — DynamoDB tabela
  2. auth       — Cognito User Pool + post-confirmation Lambda (sa lokalnim shared layer-om)
  3. api        — API Gateway + sve API Lambde + AI processor + materials S3 (sa lokalnim shared layer-om)
  4. frontend   — CloudFront + frontend S3 + asset deployment
  5. monitoring — CloudWatch dashboards i alarmi (opciono)

NAPOMENA: shared Lambda Layer je definisan per-stack (helper `make_shared_layer`)
umesto cross-stack export-a, jer LayerVersion update preko import-a pati od
"Cannot update export ... in use" problema. CDK asset cache deli ZIP između
stack-ova kad je hash isti, tako da nema duplikacije na disku.
"""
from __future__ import annotations

import os

import aws_cdk as cdk

from stacks.auth_stack import AuthStack
from stacks.data_stack import DataStack
from stacks.api_stack import ApiStack
from stacks.frontend_stack import FrontendStack
from stacks.monitoring_stack import MonitoringStack
from stacks.reports_stack import ReportsStack


app = cdk.App()

app_name = app.node.try_get_context("appName") or "Konsultacije"
env_name = app.node.try_get_context("envName") or "dev"

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "eu-central-1"),
)

common_tags = {
    "App": app_name,
    "Env": env_name,
    "ManagedBy": "CDK",
}


def stack_id(name: str) -> str:
    return f"{app_name}-{name}-{env_name}"


data_stack = DataStack(app, stack_id("Data"), env=env)

reports_stack = ReportsStack(app, stack_id("Reports"), env=env)

auth_stack = AuthStack(
    app,
    stack_id("Auth"),
    table=data_stack.table,
    env=env,
)

api_stack = ApiStack(
    app,
    stack_id("Api"),
    table=data_stack.table,
    user_pool=auth_stack.user_pool,
    reports_bucket=reports_stack.bucket,
    env=env,
)

frontend_stack = FrontendStack(
    app,
    stack_id("Frontend"),
    api_url=api_stack.api_url,
    user_pool_id=auth_stack.user_pool.user_pool_id,
    user_pool_client_id=auth_stack.user_pool_client.user_pool_client_id,
    region=env.region or "eu-central-1",
    env=env,
)

MonitoringStack(
    app,
    stack_id("Monitoring"),
    api=api_stack.api,
    table=data_stack.table,
    ai_processor=api_stack.ai_processor,
    rezime_generator=api_stack.rezime_generator,
    ai_ask=api_stack.ai_ask,
    env=env,
)

for k, v in common_tags.items():
    cdk.Tags.of(app).add(k, v)

app.synth()
