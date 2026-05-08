# infra/CLAUDE.md

> Lokalna pravila za AWS CDK infrastrukturu.
> Root pravila: `/CLAUDE.md`. Backend pravila: `/backend/CLAUDE.md`.

---

## 1. Stack

- AWS CDK v2 (Python)
- Region: `eu-central-1`
- Bootstrap: `cdk bootstrap aws://ACCOUNT/eu-central-1`

---

## 2. Stack-ovi

```
infra/
├── app.py                       # CDK app entry
└── stacks/
    ├── shared_layer.py          # Lambda layer (Powertools, boto3, pydantic, ulid)
    ├── data_stack.py            # DynamoDB tabela + GSI-ji
    ├── auth_stack.py            # Cognito User Pool + post-confirmation Lambda
    ├── api_stack.py             # API Gateway + sve Lambde + materials S3
    ├── reports_stack.py         # V2: reports S3 + EventBridge Scheduler role
    ├── frontend_stack.py        # CloudFront + S3 frontend
    └── monitoring_stack.py      # Dashboards, alarms, budget
```

### Dependency order

```
SharedLayer
    ↓
DataStack          (no deps)
    ↓
AuthStack          (uses DataStack table)
    ↓
ApiStack           (uses Data, Auth, SharedLayer)
ReportsStack (V2)  (uses Data)
    ↓
FrontendStack      (uses ApiStack outputs)
MonitoringStack    (uses Api, Reports)
```

Sve cross-stack reference idu preko CDK `props` ili explicit `Stack.of(scope).account`. **Nikad** hardkodovani ARN-ovi.

---

## 3. Naming conventions

- Stack ime: PascalCase, sufiks `Stack` (`AuthStack`, `DataStack`)
- Resource ime u CDK: PascalCase (`UserPool`, `MainTable`)
- Logical ID: short, descriptive
- Resource physical name (gde je dozvoljeno):
  - DDB tabela: `KonsultacijeTable`
  - Cognito pool: `KonsultacijeUserPool`
  - S3 buckets: `konsultacije-{purpose}-{accountId}`
    - `konsultacije-materials-{accountId}`
    - `konsultacije-reports-{accountId}`
    - `konsultacije-frontend-{accountId}`

---

## 4. Lambda definicija (template)

```python
from aws_cdk import (
    aws_lambda as lambda_,
    aws_logs as logs,
    Duration
)

submit_feedback = lambda_.Function(
    self, "SubmitFeedback",
    function_name="konsultacije-submitFeedback",
    runtime=lambda_.Runtime.PYTHON_3_12,
    architecture=lambda_.Architecture.ARM_64,  # OBAVEZNO
    handler="lambdas.feedback.submit.handler",
    code=lambda_.Code.from_asset("../backend"),
    layers=[shared_layer],
    memory_size=256,  # default; AI/rezime = 1024
    timeout=Duration.seconds(10),  # default; AI/rezime = 60
    environment={
        "TABLE_NAME": table.table_name,
        "POWERTOOLS_SERVICE_NAME": "konsultacije",
        "LOG_LEVEL": "INFO"
    },
    tracing=lambda_.Tracing.ACTIVE,
    log_retention=logs.RetentionDays.ONE_WEEK
)

# IAM
table.grant_read_write_data(submit_feedback)
```

### Memory & timeout cheatsheet

| Lambda type | Memory | Timeout |
|-------------|--------|---------|
| Read-heavy (gets, lists) | 256 MB | 10s |
| Write-heavy (creates, updates) | 512 MB | 10s |
| AI processor | 1024 MB | 60s |
| Rezime generator | 1024 MB | 60s |
| Pre-signed URL | 256 MB | 5s |

---

## 5. DynamoDB

```python
table = dynamodb.Table(
    self, "MainTable",
    table_name="KonsultacijeTable",
    partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
    sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # OBAVEZNO on-demand
    point_in_time_recovery=False,  # off za V1 (cost)
    removal_policy=RemovalPolicy.RETAIN  # ne briši pri cdk destroy (V1)
)

# GSI definicije
table.add_global_secondary_index(
    index_name="GSI1",
    partition_key=dynamodb.Attribute(name="GSI1PK", type=dynamodb.AttributeType.STRING),
    sort_key=dynamodb.Attribute(name="GSI1SK", type=dynamodb.AttributeType.STRING)
)
# isto za GSI2, GSI3, GSI4
```

**Removal policy:** Za prod, `RETAIN`. Za dev, može `DESTROY` da `cdk destroy` cleanup-uje sve.

---

## 6. S3 buckets

```python
materials_bucket = s3.Bucket(
    self, "MaterialsBucket",
    bucket_name=f"konsultacije-materials-{self.account}",
    encryption=s3.BucketEncryption.S3_MANAGED,
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    cors=[s3.CorsRule(
        allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
        allowed_origins=["*"],  # tighten u prod-u
        allowed_headers=["*"],
        max_age=3000
    )],
    lifecycle_rules=[
        s3.LifecycleRule(
            id="transition-to-ia",
            transitions=[s3.Transition(
                storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                transition_after=Duration.days(30)
            )]
        ),
        s3.LifecycleRule(
            id="delete-after-year",
            expiration=Duration.days(365)
        )
    ]
)

# S3 trigger za AI processor
materials_bucket.add_event_notification(
    s3.EventType.OBJECT_CREATED,
    s3n.LambdaDestination(ai_processor),
    s3.NotificationKeyFilter(prefix="materials/")
)
```

**OBAVEZNO za sve buckete:**
- `block_public_access=BLOCK_ALL`
- `encryption=S3_MANAGED`
- Lifecycle rule (cost-saving)

---

## 7. API Gateway

```python
api = apigateway.RestApi(
    self, "Api",
    rest_api_name="konsultacije-api",
    deploy_options=apigateway.StageOptions(
        stage_name="v1",
        logging_level=apigateway.MethodLoggingLevel.INFO,
        # access_log_destination=...,  # OFF za cost (vidi root CLAUDE.md note)
    ),
    default_cors_preflight_options=apigateway.CorsOptions(
        allow_origins=apigateway.Cors.ALL_ORIGINS,  # tighten prod
        allow_methods=apigateway.Cors.ALL_METHODS,
        allow_headers=["Content-Type", "Authorization"]
    )
)

authorizer = apigateway.CognitoUserPoolsAuthorizer(
    self, "Authorizer",
    cognito_user_pools=[user_pool]
)

# Endpoint primer
termini = api.root.add_resource("termini")
termini.add_method(
    "GET",
    apigateway.LambdaIntegration(list_termini_lambda),
    authorizer=authorizer,
    authorization_type=apigateway.AuthorizationType.COGNITO
)
```

### Public routes

`/health` ide bez authorizer-a:
```python
api.root.add_resource("health").add_method(
    "GET",
    apigateway.LambdaIntegration(health_lambda)
    # bez authorizer
)
```

---

## 8. EventBridge Scheduler (V2)

```python
# Role da scheduler može da invoke-uje Lambda
scheduler_role = iam.Role(
    self, "SchedulerRole",
    assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com")
)
rezime_generator_lambda.grant_invoke(scheduler_role)

# Schedule kreiranje radi Lambda u runtime-u (ne CDK), 
# jer se schedule pravi po terminu

# CDK kreira samo IAM role i prosleđuje ARN u objaviTermin Lambdu env-u
objavi_termin_lambda.add_environment("SCHEDULER_ROLE_ARN", scheduler_role.role_arn)
objavi_termin_lambda.add_environment("REZIME_LAMBDA_ARN", rezime_generator_lambda.function_arn)

# Permission za objaviTermin da kreira/briše schedule
objavi_termin_lambda.add_to_role_policy(iam.PolicyStatement(
    actions=[
        "scheduler:CreateSchedule",
        "scheduler:DeleteSchedule",
        "scheduler:GetSchedule"
    ],
    resources=["*"]  # tighten ako moguće
))

objavi_termin_lambda.add_to_role_policy(iam.PolicyStatement(
    actions=["iam:PassRole"],
    resources=[scheduler_role.role_arn]
))
```

---

## 9. CloudFront + Frontend

```python
oac = cloudfront.S3OriginAccessControl(self, "OAC")

distribution = cloudfront.Distribution(
    self, "Distribution",
    default_behavior=cloudfront.BehaviorOptions(
        origin=origins.S3BucketOrigin.with_origin_access_control(
            frontend_bucket,
            origin_access_control=oac
        ),
        viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
    ),
    default_root_object="index.html",
    error_responses=[
        cloudfront.ErrorResponse(
            http_status=403,
            response_http_status=200,
            response_page_path="/index.html"
        ),
        cloudfront.ErrorResponse(
            http_status=404,
            response_http_status=200,
            response_page_path="/index.html"
        )
    ],
    price_class=cloudfront.PriceClass.PRICE_CLASS_100  # samo US/EU edges = jeftinije
)

# Deploy frontend build
s3_deployment.BucketDeployment(
    self, "DeployFrontend",
    sources=[s3_deployment.Source.asset("../frontend/dist")],
    destination_bucket=frontend_bucket,
    distribution=distribution,
    distribution_paths=["/*"]  # invalidate cache
)
```

---

## 10. IAM least privilege

❌ **Nikad** `actions=["*"]` ili `resources=["*"]` osim ako apsolutno nužno (i sa komentarom).

✅ Koristi CDK helpers gde god moguće:
```python
table.grant_read_write_data(my_lambda)  # umesto custom IAM policy
bucket.grant_put(my_lambda)
bucket.grant_read(other_lambda, "rezime/*")
```

✅ Granular CloudWatch:
```python
my_lambda.add_to_role_policy(iam.PolicyStatement(
    actions=["bedrock:InvokeModel"],
    resources=[
        f"arn:aws:bedrock:eu-central-1::foundation-model/anthropic.claude-haiku-4-5-*"
    ]
))
```

---

## 11. Outputs

Svaki stack izvozi relevantne podatke:

```python
CfnOutput(self, "ApiUrl", value=api.url)
CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
CfnOutput(self, "FrontendUrl", value=f"https://{distribution.domain_name}")
```

Output-i se konzumiraju iz `frontend/.env.local` (ručno copy paste posle deploy-a, ili automatizovano kroz `scripts/deploy.sh`).

---

## 12. Cost optimization checklist

- [x] Sve Lambde ARM64
- [x] DynamoDB on-demand
- [x] CloudWatch retention 7 dana
- [x] S3 lifecycle rules (IA posle 30 dana)
- [x] CloudFront price class 100 (samo US/EU)
- [x] Bedrock model: Haiku (najjeftiniji Claude)
- [x] Lambda memory minimum potreban (ne over-provision)
- [x] API Gateway access logs OFF (postoji Lambda log)
- [x] X-Ray sampling rate < 100% u prod-u (default 5%)

---

## 13. CDK workflow

```bash
# Setup (jednom)
cd infra
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap

# Pre svake promene
cdk diff

# Deploy specific stack
cdk deploy ApiStack

# Deploy sve
cdk deploy --all

# Destroy (CAREFUL)
cdk destroy --all
```

---

## 14. Infra-specific don'ts

- ❌ Hardkodovani region (uvek iz `Stack.of(scope).region`)
- ❌ Hardkodovani account ID (uvek iz `Stack.of(scope).account`)
- ❌ `cdk deploy --require-approval never` u CI bez review-a
- ❌ Naming bez prefixa (collision sa drugim CDK app-ovima)
- ❌ Mutable resource names u prod-u (zamena = data loss)
- ❌ Skipping `cdk diff` pre prod deploy-a
- ❌ Hardkodovani Lambda ARN-ovi (uvek `lambda.function_arn`)
- ❌ Cross-stack export bez razloga (često se može preko props)

---

## 15. Monitoring (V1 baseline)

```python
# CloudWatch dashboard
dashboard = cloudwatch.Dashboard(self, "Dashboard", dashboard_name="Konsultacije")

dashboard.add_widgets(
    cloudwatch.GraphWidget(
        title="API Errors",
        left=[api.metric_client_error(), api.metric_server_error()]
    ),
    cloudwatch.GraphWidget(
        title="AI Processor Duration",
        left=[ai_processor.metric_duration()]
    ),
    cloudwatch.GraphWidget(
        title="DynamoDB Throttles",
        left=[table.metric("ThrottledRequests")]
    )
)

# Alarm: AI processor errors > 3 u 5 min
ai_error_alarm = cloudwatch.Alarm(
    self, "AiProcessorErrors",
    metric=ai_processor.metric_errors(),
    threshold=3,
    evaluation_periods=1,
    datapoints_to_alarm=1
)

# Budget alert
budgets.CfnBudget(self, "MonthlyBudget",
    budget=budgets.CfnBudget.BudgetDataProperty(
        budget_name="konsultacije-monthly",
        budget_type="COST",
        time_unit="MONTHLY",
        budget_limit=budgets.CfnBudget.SpendProperty(amount=5, unit="USD")
    ),
    notifications_with_subscribers=[...]
)
```

---

**End of infra/CLAUDE.md.**
