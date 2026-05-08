"""Smoke testovi za CDK stack-ove."""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk.assertions import Template

from stacks.data_stack import DataStack


def test_data_stack_creates_table():
    app = cdk.App()
    stack = DataStack(app, "TestData")
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::DynamoDB::Table", 1)
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {"BillingMode": "PAY_PER_REQUEST"},
    )
