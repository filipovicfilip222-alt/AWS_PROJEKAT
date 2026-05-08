"""Reports stack — V2.

Drži samo Reports S3 bucket (CSV + AI insights JSON izlaz Rezime generatora).
Scheduler IAM role je definisan u ApiStack-u da bi se izbegao cyclic ref između
ReportsStack ↔ ApiStack (`grant_invoke` na Lambdu iz ApiStack-a + `iam:PassRole`
za scheduler role iz ApiStack-a).
"""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct


class ReportsStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account_id = cdk.Aws.ACCOUNT_ID

        self.bucket = s3.Bucket(
            self,
            "ReportsBucket",
            bucket_name=f"konsultacije-reports-{account_id}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="reports-expire-after-year",
                    enabled=True,
                    prefix="rezime/",
                    expiration=cdk.Duration.days(365),
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
                ),
            ],
        )

        cdk.CfnOutput(self, "ReportsBucketName", value=self.bucket.bucket_name)
