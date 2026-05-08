"""CloudFront distribucija + S3 frontend bucket + deployment.

- Bucket je u istom stack-u kao distribucija da bismo izbegli cross-stack cyclic dependency
- OAC (Origin Access Control) za sigurnost
- SPA fallback: 403/404 → /index.html
- Frontend build se uploaduje preko BucketDeployment iz frontend/dist
"""
from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


class FrontendStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        api_url: str,
        user_pool_id: str,
        user_pool_client_id: str,
        region: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account_id = cdk.Aws.ACCOUNT_ID
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"konsultacije-frontend-{account_id}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
        )

        self.distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.minutes(5),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            comment="Konsultacije SPA frontend",
        )

        if FRONTEND_DIST.exists():
            s3deploy.BucketDeployment(
                self,
                "FrontendDeploy",
                sources=[s3deploy.Source.asset(str(FRONTEND_DIST))],
                destination_bucket=self.frontend_bucket,
                distribution=self.distribution,
                distribution_paths=["/*"],
                memory_limit=512,
            )

        cdk.CfnOutput(self, "DistributionUrl", value=f"https://{self.distribution.domain_name}")
        cdk.CfnOutput(self, "ApiUrlOutput", value=api_url)
        cdk.CfnOutput(self, "UserPoolIdOutput", value=user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientIdOutput", value=user_pool_client_id)
        cdk.CfnOutput(self, "RegionOutput", value=region)
        cdk.CfnOutput(self, "FrontendBucketName", value=self.frontend_bucket.bucket_name)
