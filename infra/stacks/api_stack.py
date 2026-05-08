"""API Gateway (REST) + sve API Lambde + AI processor.

Sve API Lambde:
  - Python 3.12, ARM64
  - shared layer (backend/shared/) sa boto3 helperima
  - Cognito JWT authorizer (osim /health)
  - Powertools logger configured

S3 PUT event na materials bucket → aiProcessor Lambda.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import aws_cdk as cdk
from aws_cdk import (
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
)
from constructs import Construct

from .shared_layer import make_shared_layer


BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


class ApiStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: ddb.ITable,
        user_pool: cognito.IUserPool,
        reports_bucket: s3.IBucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._table = table
        self.shared_layer = make_shared_layer(self)
        self._reports_bucket = reports_bucket

        scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
            description="EventBridge Scheduler role for rezime generator Lambda",
        )
        self._scheduler_role = scheduler_role

        account_id = cdk.Aws.ACCOUNT_ID
        materials_bucket = s3.Bucket(
            self,
            "MaterialsBucket",
            bucket_name=f"konsultacije-materials-{account_id}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.GET],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"],
                    max_age=3000,
                )
            ],
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="Materials-IA-then-Expire",
                    enabled=True,
                    prefix="materials/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=cdk.Duration.days(30),
                        )
                    ],
                    expiration=cdk.Duration.days(365),
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
                ),
            ],
        )
        self.materials_bucket = materials_bucket
        cdk.CfnOutput(self, "MaterialsBucketName", value=materials_bucket.bucket_name)

        # ---------- API Gateway ----------
        # NAPOMENA: API Gateway access logging (logging_level + metrics) zahteva
        # account-wide CloudWatch Logs role ARN. Da bismo izbegli account setup,
        # za V1 koristimo SAMO Lambda logove (preko Powertools) — sve potrebne
        # info su tamo. Ako želiš da uključiš access logs kasnije, otkomentariši
        # logging_level/metrics_enabled i u AWS konzoli pod
        # `API Gateway → Settings` postavi CloudWatch Logs role ARN.
        self.api = apigw.RestApi(
            self,
            "KonsultacijeApi",
            rest_api_name="KonsultacijeApi",
            cloud_watch_role=False,  # eksplicitno: ne pravi account-level role
            deploy_options=apigw.StageOptions(
                stage_name="v1",
                throttling_burst_limit=200,
                throttling_rate_limit=100,
                # logging_level=apigw.MethodLoggingLevel.INFO,
                # metrics_enabled=True,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
                max_age=cdk.Duration.minutes(5),
            ),
        )

        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="KonsultacijeCognitoAuth",
        )

        # ---------- API Lambdas ----------
        common_env = {
            "TABLE_NAME": table.table_name,
            "MATERIALS_BUCKET": materials_bucket.bucket_name,
            "POWERTOOLS_SERVICE_NAME": "konsultacije",
            "LOG_LEVEL": "INFO",
        }

        # User
        get_me = self._mk_fn("GetMeFn", "user", "get_me", common_env)
        table.grant_read_data(get_me)

        # Termini
        create_termin = self._mk_fn("CreateTerminFn", "termini", "create", common_env)
        list_termini = self._mk_fn("ListTerminiFn", "termini", "list", common_env)
        get_termin = self._mk_fn("GetTerminFn", "termini", "get", common_env)
        update_termin = self._mk_fn("UpdateTerminFn", "termini", "update", common_env)
        delete_termin = self._mk_fn("DeleteTerminFn", "termini", "delete", common_env)
        objavi_termin = self._mk_fn("ObjaviTerminFn", "termini", "objavi", common_env)
        moji_termini = self._mk_fn("MojiTerminiFn", "termini", "moji", common_env)
        for fn in [create_termin, update_termin, delete_termin, objavi_termin]:
            table.grant_read_write_data(fn)
        for fn in [list_termini, get_termin, moji_termini]:
            table.grant_read_data(fn)

        # Materials
        get_upload_url = self._mk_fn("GetUploadUrlFn", "materials", "get_upload_url", common_env)
        list_materials = self._mk_fn("ListMaterialsFn", "materials", "list", common_env)
        delete_material = self._mk_fn("DeleteMaterialFn", "materials", "delete", common_env)
        table.grant_read_write_data(get_upload_url)
        table.grant_read_data(list_materials)
        table.grant_read_write_data(delete_material)
        materials_bucket.grant_put(get_upload_url)
        materials_bucket.grant_delete(delete_material)

        # Slots
        rezervisi = self._mk_fn("RezervisiSlotFn", "slots", "rezervisi", common_env)
        otkazi = self._mk_fn("OtkaziRezervacijuFn", "slots", "otkazi", common_env)
        moje_rezervacije = self._mk_fn("MojeRezervacijeFn", "slots", "moje", common_env)
        for fn in [rezervisi, otkazi]:
            table.grant_read_write_data(fn)
        table.grant_read_data(moje_rezervacije)

        # Questions
        list_questions = self._mk_fn("ListQuestionsFn", "questions", "list", common_env)
        create_question = self._mk_fn("CreateQuestionFn", "questions", "create", common_env)
        update_question = self._mk_fn("UpdateQuestionFn", "questions", "update", common_env)
        delete_question = self._mk_fn("DeleteQuestionFn", "questions", "delete", common_env)
        approve_question = self._mk_fn("ApproveQuestionFn", "questions", "approve", common_env)
        table.grant_read_data(list_questions)
        for fn in [create_question, update_question, delete_question, approve_question]:
            table.grant_read_write_data(fn)
        # V3: approve i update mogu generisati embedding (lazy/refresh) → Titan IAM
        for fn in [approve_question, update_question]:
            fn.add_to_role_policy(self._titan_invoke_policy())

        # Search
        search_questions = self._mk_fn("SearchQuestionsFn", "search", "questions", common_env)
        list_tags = self._mk_fn("ListTagsFn", "search", "tags", common_env)
        list_predmeti = self._mk_fn("ListPredmetiFn", "search", "predmeti", common_env)
        for fn in [search_questions, list_tags, list_predmeti]:
            table.grant_read_data(fn)
        # V3: search_questions zove Titan v2 za semantic deo hibridne pretrage.
        search_questions.add_to_role_policy(self._titan_invoke_policy())

        # Feedback (V2)
        submit_feedback = self._mk_fn(
            "SubmitFeedbackFn", "feedback", "submit", common_env, memory_mb=256
        )
        get_my_feedback = self._mk_fn(
            "GetMyFeedbackFn", "feedback", "get_my", common_env, memory_mb=256, timeout_s=5
        )
        table.grant_read_write_data(submit_feedback)
        table.grant_read_data(get_my_feedback)

        # AI processor (S3 trigger) + retry
        self.ai_processor = self._mk_fn(
            "AiProcessorFn",
            "ai",
            "processor",
            common_env,
            memory_mb=1024,
            timeout_s=60,
        )
        retry_ai = self._mk_fn(
            "RetryAiFn",
            "ai",
            "retry",
            common_env,
            memory_mb=512,
            timeout_s=15,
        )
        table.grant_read_write_data(self.ai_processor)
        materials_bucket.grant_read(self.ai_processor)
        # Claude Haiku 4.5 koristi global inference profile, koji zahteva pristup
        # i inference-profile ARN-u i underlying foundation-model ARN-u (u svim
        # regionima koje profile pokriva — zato wildcard region).
        self.ai_processor.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-*",
                    "arn:aws:bedrock:*:*:inference-profile/global.anthropic.claude-haiku-*",
                    f"arn:aws:bedrock:{cdk.Aws.REGION}:*:inference-profile/*anthropic.claude-haiku-*",
                ],
            )
        )
        # V3: ai_processor takođe generiše embeddings preko Titan v2.
        self.ai_processor.add_to_role_policy(self._titan_invoke_policy())
        # V3: ai_processor mora da pisuje extracted.txt u materials bucket.
        materials_bucket.grant_put(self.ai_processor)
        table.grant_read_write_data(retry_ai)
        materials_bucket.grant_read(retry_ai)
        retry_ai.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[self.ai_processor.function_arn],
            )
        )
        retry_ai.add_environment("AI_PROCESSOR_FN", self.ai_processor.function_name)

        # S3 PUT event → ai processor (filtrira Q&A trigger samo na originalni
        # upload; extracted.txt je takođe pod `materials/` ali ne sme da
        # re-okine processor — exclude preko suffix filter-a.)
        materials_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.ai_processor),
            s3.NotificationKeyFilter(prefix="materials/", suffix=".pdf"),
        )
        materials_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.ai_processor),
            s3.NotificationKeyFilter(prefix="materials/", suffix=".pptx"),
        )
        for img_suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            materials_bucket.add_event_notification(
                s3.EventType.OBJECT_CREATED,
                s3n.LambdaDestination(self.ai_processor),
                s3.NotificationKeyFilter(prefix="materials/", suffix=img_suffix),
            )

        # ---------- V3: AI tutor ----------
        ai_ask = self._mk_fn(
            "AiTutorAskFn",
            "ai",
            "ask",
            {
                **common_env,
                "TITAN_EMBED_MODEL_ID": "amazon.titan-embed-text-v2:0",
                "RATE_LIMIT_PER_DAY": "20",
                "AI_CHAT_TTL_DAYS": "90",
            },
            memory_mb=512,
            timeout_s=20,
        )
        table.grant_read_write_data(ai_ask)
        materials_bucket.grant_read(ai_ask)
        ai_ask.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-*",
                    "arn:aws:bedrock:*:*:inference-profile/global.anthropic.claude-haiku-*",
                    f"arn:aws:bedrock:{cdk.Aws.REGION}:*:inference-profile/*anthropic.claude-haiku-*",
                ],
            )
        )
        ai_ask.add_to_role_policy(self._titan_invoke_policy())
        self.ai_ask = ai_ask

        # ---------- V2: Rezime ----------
        rezime_env = {
            **common_env,
            "REPORTS_BUCKET": reports_bucket.bucket_name,
            "SCHEDULER_GROUP": "default",
        }
        self.rezime_generator = self._mk_fn(
            "RezimeGeneratorFn",
            "rezime",
            "generate",
            rezime_env,
            memory_mb=1024,
            timeout_s=60,
        )
        table.grant_read_write_data(self.rezime_generator)
        reports_bucket.grant_put(self.rezime_generator)
        reports_bucket.grant_read(self.rezime_generator)
        self.rezime_generator.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-*",
                    "arn:aws:bedrock:*:*:inference-profile/global.anthropic.claude-haiku-*",
                    f"arn:aws:bedrock:{cdk.Aws.REGION}:*:inference-profile/*anthropic.claude-haiku-*",
                ],
            )
        )

        # Scheduler may invoke rezime_generator.
        self.rezime_generator.grant_invoke(scheduler_role)

        # objaviTermin / deleteTermin need to manage schedules.
        scheduler_extra_env = {
            "SCHEDULER_GROUP": "default",
            "SCHEDULER_ROLE_ARN": scheduler_role.role_arn,
            "REZIME_LAMBDA_ARN": self.rezime_generator.function_arn,
        }
        for fn_with_schedule in [objavi_termin, delete_termin]:
            for k, v in scheduler_extra_env.items():
                fn_with_schedule.add_environment(k, v)
            fn_with_schedule.add_to_role_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "scheduler:CreateSchedule",
                        "scheduler:DeleteSchedule",
                        "scheduler:GetSchedule",
                        "scheduler:UpdateSchedule",
                    ],
                    resources=[
                        f"arn:aws:scheduler:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:schedule/default/rezime-*"
                    ],
                )
            )
            fn_with_schedule.add_to_role_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["iam:PassRole"],
                    resources=[scheduler_role.role_arn],
                )
            )

        # Rezime API Lambdas
        get_rezime = self._mk_fn(
            "GetRezimeFn",
            "rezime",
            "get",
            {**common_env, "REPORTS_BUCKET": reports_bucket.bucket_name},
            memory_mb=256,
        )
        regenerate_rezime = self._mk_fn(
            "RegenerateRezimeFn",
            "rezime",
            "regenerate",
            {**common_env, "REZIME_LAMBDA_ARN": self.rezime_generator.function_arn},
            memory_mb=256,
        )
        table.grant_read_data(get_rezime)
        reports_bucket.grant_read(get_rezime)
        table.grant_read_data(regenerate_rezime)
        regenerate_rezime.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[self.rezime_generator.function_arn],
            )
        )

        # ---------- Routes ----------
        self._wire_routes(
            get_me=get_me,
            create_termin=create_termin,
            list_termini=list_termini,
            get_termin=get_termin,
            update_termin=update_termin,
            delete_termin=delete_termin,
            objavi_termin=objavi_termin,
            moji_termini=moji_termini,
            get_upload_url=get_upload_url,
            list_materials=list_materials,
            delete_material=delete_material,
            rezervisi=rezervisi,
            otkazi=otkazi,
            moje_rezervacije=moje_rezervacije,
            list_questions=list_questions,
            create_question=create_question,
            update_question=update_question,
            delete_question=delete_question,
            approve_question=approve_question,
            search_questions=search_questions,
            list_tags=list_tags,
            list_predmeti=list_predmeti,
            retry_ai=retry_ai,
            submit_feedback=submit_feedback,
            get_my_feedback=get_my_feedback,
            get_rezime=get_rezime,
            regenerate_rezime=regenerate_rezime,
            ai_ask=ai_ask,
        )

        self.api_url = self.api.url
        cdk.CfnOutput(self, "ApiUrl", value=self.api.url)

    # ---------- helpers ----------
    def _mk_fn(
        self,
        construct_id: str,
        package: str,
        module: str,
        env: dict,
        *,
        memory_mb: int = 512,
        timeout_s: int = 10,
        extra_env: Optional[dict] = None,
    ) -> _lambda.Function:
        merged_env = {**env, **(extra_env or {})}
        return _lambda.Function(
            self,
            construct_id,
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler=f"{module}.handler",
            code=_lambda.Code.from_asset(str(BACKEND_DIR / "lambdas" / package)),
            memory_size=memory_mb,
            timeout=cdk.Duration.seconds(timeout_s),
            layers=[self.shared_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment=merged_env,
            tracing=_lambda.Tracing.ACTIVE,
        )

    def _auth(self) -> dict:
        return {
            "authorizer": self.authorizer,
            "authorization_type": apigw.AuthorizationType.COGNITO,
        }

    def _titan_invoke_policy(self) -> iam.PolicyStatement:
        """V3: IAM statement za Titan v2 embeddings invoke."""
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=[
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2*",
            ],
        )

    def _wire_routes(self, **fns) -> None:  # noqa: C901
        api = self.api
        auth = self._auth()

        # /health (open)
        health = api.root.add_resource("health")
        health.add_method("GET", apigw.MockIntegration(
            integration_responses=[apigw.IntegrationResponse(status_code="200")],
            request_templates={"application/json": '{"statusCode": 200}'},
        ), method_responses=[apigw.MethodResponse(status_code="200")])

        # /me
        me = api.root.add_resource("me")
        me.add_method("GET", apigw.LambdaIntegration(fns["get_me"]), **auth)
        me_rez = me.add_resource("rezervacije")
        me_rez.add_method("GET", apigw.LambdaIntegration(fns["moje_rezervacije"]), **auth)
        me_term = me.add_resource("termini")
        me_term.add_method("GET", apigw.LambdaIntegration(fns["moji_termini"]), **auth)

        # /predmeti
        predmeti = api.root.add_resource("predmeti")
        predmeti.add_method("GET", apigw.LambdaIntegration(fns["list_predmeti"]), **auth)

        # /search/{questions,tags}
        search = api.root.add_resource("search")
        search_q = search.add_resource("questions")
        search_q.add_method("GET", apigw.LambdaIntegration(fns["search_questions"]), **auth)
        search_t = search.add_resource("tags")
        search_t.add_method("GET", apigw.LambdaIntegration(fns["list_tags"]), **auth)

        # /termini
        termini = api.root.add_resource("termini")
        termini.add_method("GET", apigw.LambdaIntegration(fns["list_termini"]), **auth)
        termini.add_method("POST", apigw.LambdaIntegration(fns["create_termin"]), **auth)

        termin_id = termini.add_resource("{id}")
        termin_id.add_method("GET", apigw.LambdaIntegration(fns["get_termin"]), **auth)
        termin_id.add_method("PATCH", apigw.LambdaIntegration(fns["update_termin"]), **auth)
        termin_id.add_method("DELETE", apigw.LambdaIntegration(fns["delete_termin"]), **auth)

        # /termini/{id}/objavi
        objavi = termin_id.add_resource("objavi")
        objavi.add_method("POST", apigw.LambdaIntegration(fns["objavi_termin"]), **auth)

        # /termini/{id}/rezime (V2)
        rezime_res = termin_id.add_resource("rezime")
        rezime_res.add_method(
            "GET", apigw.LambdaIntegration(fns["get_rezime"]), **auth
        )
        regen_res = rezime_res.add_resource("regenerate")
        regen_res.add_method(
            "POST", apigw.LambdaIntegration(fns["regenerate_rezime"]), **auth
        )

        # /termini/{id}/materials/...
        materials = termin_id.add_resource("materials")
        materials.add_method("GET", apigw.LambdaIntegration(fns["list_materials"]), **auth)
        upload_url = materials.add_resource("upload-url")
        upload_url.add_method("POST", apigw.LambdaIntegration(fns["get_upload_url"]), **auth)
        material_id = materials.add_resource("{materialId}")
        material_id.add_method("DELETE", apigw.LambdaIntegration(fns["delete_material"]), **auth)

        # /termini/{id}/slots/{slotIndex}/...
        slots = termin_id.add_resource("slots")
        slot_idx = slots.add_resource("{slotIndex}")
        rez_res = slot_idx.add_resource("rezervisi")
        rez_res.add_method("POST", apigw.LambdaIntegration(fns["rezervisi"]), **auth)
        rezervacija_res = slot_idx.add_resource("rezervacija")
        rezervacija_res.add_method("DELETE", apigw.LambdaIntegration(fns["otkazi"]), **auth)

        # /termini/{id}/ai/process
        ai = termin_id.add_resource("ai")
        ai_proc = ai.add_resource("process")
        ai_proc.add_method("POST", apigw.LambdaIntegration(fns["retry_ai"]), **auth)

        # /termini/{id}/questions  (list + create)
        questions = termin_id.add_resource("questions")
        questions.add_method("GET", apigw.LambdaIntegration(fns["list_questions"]), **auth)
        questions.add_method("POST", apigw.LambdaIntegration(fns["create_question"]), **auth)

        # /questions/{id}  (patch + delete + approve)
        questions_root = api.root.add_resource("questions")
        question_id = questions_root.add_resource("{id}")
        question_id.add_method("PATCH", apigw.LambdaIntegration(fns["update_question"]), **auth)
        question_id.add_method("DELETE", apigw.LambdaIntegration(fns["delete_question"]), **auth)
        approve = question_id.add_resource("approve")
        approve.add_method("POST", apigw.LambdaIntegration(fns["approve_question"]), **auth)

        # /questions/{id}/feedback (V2 — student vote)
        feedback_res = question_id.add_resource("feedback")
        feedback_res.add_method(
            "POST", apigw.LambdaIntegration(fns["submit_feedback"]), **auth
        )
        feedback_me = feedback_res.add_resource("me")
        feedback_me.add_method(
            "GET", apigw.LambdaIntegration(fns["get_my_feedback"]), **auth
        )

        # /ai/ask (V3 — student AI tutor sa rate limit-om)
        ai_root = api.root.add_resource("ai")
        ai_ask_res = ai_root.add_resource("ask")
        ai_ask_res.add_method(
            "POST", apigw.LambdaIntegration(fns["ai_ask"]), **auth
        )
