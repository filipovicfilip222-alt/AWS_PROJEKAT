"""CloudWatch monitoring + budget alarm.

Minimalan setup za V1: jedan dashboard sa ključnim metrikama, budget alarm na $5/mesec.
"""
from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    aws_apigateway as apigw,
    aws_budgets as budgets,
    aws_cloudwatch as cw,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
)
from constructs import Construct


class MonitoringStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        api: apigw.IRestApi,
        table: ddb.ITable,
        ai_processor: _lambda.IFunction,
        rezime_generator: _lambda.IFunction | None = None,
        ai_ask: _lambda.IFunction | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        dashboard = cw.Dashboard(
            self,
            "KonsultacijeDashboard",
            dashboard_name="Konsultacije",
        )

        api_4xx = cw.Metric(
            namespace="AWS/ApiGateway",
            metric_name="4XXError",
            dimensions_map={"ApiName": api.rest_api_name},
            statistic="Sum",
            period=cdk.Duration.minutes(5),
        )
        api_5xx = cw.Metric(
            namespace="AWS/ApiGateway",
            metric_name="5XXError",
            dimensions_map={"ApiName": api.rest_api_name},
            statistic="Sum",
            period=cdk.Duration.minutes(5),
        )
        api_latency = cw.Metric(
            namespace="AWS/ApiGateway",
            metric_name="Latency",
            dimensions_map={"ApiName": api.rest_api_name},
            statistic="Average",
            period=cdk.Duration.minutes(5),
        )

        ai_errors = ai_processor.metric_errors(period=cdk.Duration.minutes(5))
        ai_duration = ai_processor.metric_duration(period=cdk.Duration.minutes(5))

        ddb_throttle = cw.Metric(
            namespace="AWS/DynamoDB",
            metric_name="UserErrors",
            dimensions_map={"TableName": table.table_name},
            statistic="Sum",
            period=cdk.Duration.minutes(5),
        )

        dashboard.add_widgets(
            cw.GraphWidget(title="API errors", left=[api_4xx, api_5xx], width=12),
            cw.GraphWidget(title="API latency", left=[api_latency], width=12),
        )
        dashboard.add_widgets(
            cw.GraphWidget(title="AI Processor", left=[ai_errors, ai_duration], width=12),
            cw.GraphWidget(title="DynamoDB user errors", left=[ddb_throttle], width=12),
        )

        cw.Alarm(
            self,
            "AiProcessorErrorAlarm",
            metric=ai_errors,
            threshold=3,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="AI processor errors >= 3 in 5 min",
        )

        if rezime_generator is not None:
            rezime_errors = rezime_generator.metric_errors(period=cdk.Duration.minutes(5))
            rezime_duration = rezime_generator.metric_duration(period=cdk.Duration.minutes(5))
            dashboard.add_widgets(
                cw.GraphWidget(
                    title="Rezime Generator",
                    left=[rezime_errors, rezime_duration],
                    width=12,
                ),
            )
            cw.Alarm(
                self,
                "RezimeGeneratorErrorAlarm",
                metric=rezime_errors,
                threshold=2,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                alarm_description="Rezime generator errors >= 2 in 5 min",
            )

        if ai_ask is not None:
            ai_ask_errors = ai_ask.metric_errors(period=cdk.Duration.minutes(5))
            ai_ask_invocations = ai_ask.metric_invocations(period=cdk.Duration.hours(1))
            ai_ask_duration = ai_ask.metric_duration(period=cdk.Duration.minutes(5))
            dashboard.add_widgets(
                cw.GraphWidget(
                    title="AI Tutor (V3)",
                    left=[ai_ask_errors, ai_ask_duration],
                    right=[ai_ask_invocations],
                    width=12,
                ),
            )
            cw.Alarm(
                self,
                "AiTutorAskErrorAlarm",
                metric=ai_ask_errors,
                threshold=5,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                alarm_description="AI tutor errors >= 5 in 5 min",
            )
            cw.Alarm(
                self,
                "AiTutorAskCostSpikeAlarm",
                metric=ai_ask_invocations,
                threshold=500,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                alarm_description="AI tutor invocations > 500 in 1h (cost spike guard)",
            )

        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name="KonsultacijeMonthlyBudget",
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=5,
                    unit="USD",
                ),
            ),
        )
