"""Helper za kreiranje shared Lambda Layer-a.

LayerVersion ne može biti deljen preko cross-stack import-a bez problema —
kad se hash izvornog koda promeni, CFN pravi novu LayerVersion sa novom ARN,
a postojeći export ne sme menjati vrednost dok ga consumer-i koriste
("Cannot update export ... as it is in use by ..."). Zato svaki stack
bundle-uje sopstveni layer iz iste backend/shared/ folder strukture.
CDK asset cache deli ZIP između stack-ova kad je hash isti, tako da
duplikacija nije skupa.
"""
from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_lambda as _lambda
from constructs import Construct


BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


def make_shared_layer(scope: Construct, construct_id: str = "SharedLayer") -> _lambda.LayerVersion:
    """Kreira ARM64 Python 3.12 layer sa shared kodom + boto3/pydantic deps."""
    return _lambda.LayerVersion(
        scope,
        construct_id,
        code=_lambda.Code.from_asset(
            str(BACKEND_DIR),
            bundling=cdk.BundlingOptions(
                image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                command=[
                    "bash",
                    "-c",
                    " && ".join(
                        [
                            "mkdir -p /asset-output/python",
                            "cp -r shared /asset-output/python/",
                            (
                                "pip install -r shared/requirements.txt "
                                "-t /asset-output/python --no-cache-dir "
                                "--platform manylinux2014_aarch64 "
                                "--implementation cp "
                                "--python-version 3.12 "
                                "--only-binary=:all: "
                                "--upgrade"
                            ),
                        ]
                    ),
                ],
            ),
            exclude=[
                "lambdas",
                "tests",
                "**/__pycache__",
                "**/*.pyc",
            ],
        ),
        compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
        compatible_architectures=[_lambda.Architecture.ARM_64],
        description="Konsultacije shared modul + boto3/pydantic (ARM64)",
    )
