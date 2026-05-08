"""Cognito User Pool + App Client + post-confirmation Lambda trigger.

Custom attributes:
- custom:rola      ("student" | "profesor", set at sign-up)
- custom:ime
- custom:prezime

Post-confirmation Lambda kreira USER item u DynamoDB.
"""
from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    aws_cognito as cognito,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

from .shared_layer import make_shared_layer


BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


class AuthStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: ddb.ITable,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.shared_layer = make_shared_layer(self)

        self.user_pool = cognito.UserPool(
            self,
            "KonsultacijeUserPool",
            user_pool_name="KonsultacijeUserPool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=False),
            ),
            custom_attributes={
                "rola": cognito.StringAttribute(min_len=1, max_len=20, mutable=False),
                "ime": cognito.StringAttribute(min_len=1, max_len=64, mutable=True),
                "prezime": cognito.StringAttribute(min_len=1, max_len=64, mutable=True),
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            mfa=cognito.Mfa.OFF,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.post_confirmation_fn = _lambda.Function(
            self,
            "UserPostConfirmationFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler="post_confirmation.handler",
            code=_lambda.Code.from_asset(
                str(BACKEND_DIR / "lambdas" / "user"),
                exclude=["**/__pycache__", "**/*.pyc"],
            ),
            layers=[self.shared_layer],
            memory_size=256,
            timeout=cdk.Duration.seconds(10),
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "TABLE_NAME": table.table_name,
                "POWERTOOLS_SERVICE_NAME": "konsultacije-user",
                "LOG_LEVEL": "INFO",
            },
        )
        table.grant_read_write_data(self.post_confirmation_fn)

        self.user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            self.post_confirmation_fn,
        )

        self.user_pool_client = self.user_pool.add_client(
            "WebAppClient",
            user_pool_client_name="KonsultacijeWebApp",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            access_token_validity=cdk.Duration.hours(1),
            id_token_validity=cdk.Duration.hours(1),
            refresh_token_validity=cdk.Duration.days(30),
            generate_secret=False,
            prevent_user_existence_errors=True,
        )

        cdk.CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
