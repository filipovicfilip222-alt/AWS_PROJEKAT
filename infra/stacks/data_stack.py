"""DynamoDB single-table data store.

Tabela: KonsultacijeTable
- PK (String) + SK (String)
- GSI1: tag-free per-predmet termin browsing
- GSI2: profesor's termin lookup
- GSI3: student's rezervacije lookup (RESERVATION items in V2)
- GSI4: V2 — feedback aggregation per termin (TERMIN#{id}#FEEDBACK)
- GSI5: V3 — approved questions per predmet (PREDMET#{predmet}#APPROVED) for semantic retrieval
- TTL: V3 — single global TTL attribute "ttl" (used by RATELIMIT and AI_CHAT items)
- Billing: PAY_PER_REQUEST (on-demand)
"""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    aws_dynamodb as ddb,
)
from constructs import Construct


class DataStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = ddb.Table(
            self,
            "KonsultacijeTable",
            table_name="KonsultacijeTable",
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,  # MVP / edukativno
            point_in_time_recovery=False,
            time_to_live_attribute="ttl",
        )

        # GSI1 — Studentski browse termina po predmetu
        self.table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=ddb.Attribute(name="GSI1PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI1SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL,
        )

        # GSI2 — Profesor vidi svoje termine
        self.table.add_global_secondary_index(
            index_name="GSI2",
            partition_key=ddb.Attribute(name="GSI2PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI2SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL,
        )

        # GSI3 — Student vidi svoje rezervacije
        self.table.add_global_secondary_index(
            index_name="GSI3",
            partition_key=ddb.Attribute(name="GSI3PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI3SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL,
        )

        # GSI4 — V2: feedback aggregation per termin (TERMIN#{id}#FEEDBACK)
        self.table.add_global_secondary_index(
            index_name="GSI4",
            partition_key=ddb.Attribute(name="GSI4PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI4SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL,
        )

        # GSI5 — V3: approved questions per predmet (PREDMET#{predmet}#APPROVED)
        self.table.add_global_secondary_index(
            index_name="GSI5",
            partition_key=ddb.Attribute(name="GSI5PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI5SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL,
        )

        cdk.CfnOutput(
            self,
            "TableName",
            value=self.table.table_name,
            export_name="KonsultacijeTableName",
        )
