from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ======================
        # DynamoDB Tables
        # ======================

        # Websites Table
        self.websites_table = dynamodb.Table(
            self, "WebsitesTable",
            partition_key=dynamodb.Attribute(
                name="website_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Add GSI for enabled websites
        self.websites_table.add_global_secondary_index(
            index_name="EnabledWebsitesIndex",
            partition_key=dynamodb.Attribute(
                name="enabled",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Promotions Table
        self.promotions_table = dynamodb.Table(
            self, "PromotionsTable",
            partition_key=dynamodb.Attribute(
                name="promotion_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Add GSI for querying promotions by website
        self.promotions_table.add_global_secondary_index(
            index_name="WebsitePromotionsIndex",
            partition_key=dynamodb.Attribute(
                name="website_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Predictions Table
        self.predictions_table = dynamodb.Table(
            self, "PredictionsTable",
            partition_key=dynamodb.Attribute(
                name="website_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="prediction_timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Add GSI for latest predictions
        self.predictions_table.add_global_secondary_index(
            index_name="LatestPredictionsIndex",
            partition_key=dynamodb.Attribute(
                name="is_latest",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Scraping Metrics Table (with TTL)
        self.metrics_table = dynamodb.Table(
            self, "ScrapingMetricsTable",
            partition_key=dynamodb.Attribute(
                name="metric_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ======================
        # S3 Buckets
        # ======================

        # HTML Storage Bucket
        self.html_bucket = s3.Bucket(
            self, "HtmlBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ],
                    expiration=Duration.days(365)
                )
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ======================
        # Lambda Functions
        # ======================

        # Shared Lambda layer for common dependencies
        self.shared_layer = lambda_.LayerVersion(
            self, "SharedLayer",
            code=lambda_.Code.from_asset("../lambdas/shared_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared utilities and dependencies"
        )

        # Detector-specific layer for LLM dependencies
        self.detector_layer = lambda_.LayerVersion(
            self, "DetectorLayer",
            code=lambda_.Code.from_asset("../lambdas/detector_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Detector-specific dependencies (openai, beautifulsoup4, lxml)"
        )

        # Common environment variables for all Lambdas
        common_env = {
            "WEBSITES_TABLE": self.websites_table.table_name,
            "PROMOTIONS_TABLE": self.promotions_table.table_name,
            "PREDICTIONS_TABLE": self.predictions_table.table_name,
            "METRICS_TABLE": self.metrics_table.table_name,
            "HTML_BUCKET": self.html_bucket.bucket_name,
        }

        # Get Websites Lambda
        self.get_websites_fn = lambda_.Function(
            self, "GetWebsitesFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/get_websites"),
            layers=[self.shared_layer],
            environment=common_env,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Scraper Lambda
        self.scraper_fn = lambda_.Function(
            self, "ScraperFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/scraper"),
            layers=[self.shared_layer],
            environment=common_env,
            timeout=Duration.seconds(300),
            memory_size=512,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Detector Lambda
        self.detector_fn = lambda_.Function(
            self, "DetectorFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/detector"),
            layers=[self.shared_layer, self.detector_layer],
            environment=common_env,
            timeout=Duration.seconds(300),
            memory_size=1024,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Predictor Lambda
        self.predictor_fn = lambda_.Function(
            self, "PredictorFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/predictor"),
            layers=[self.shared_layer],
            environment=common_env,
            timeout=Duration.seconds(300),
            memory_size=1024,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Grant permissions to Lambda functions
        self.websites_table.grant_read_data(self.get_websites_fn)
        self.websites_table.grant_read_data(self.scraper_fn)

        self.promotions_table.grant_read_write_data(self.scraper_fn)
        self.promotions_table.grant_read_write_data(self.detector_fn)
        self.promotions_table.grant_read_data(self.predictor_fn)

        self.predictions_table.grant_read_write_data(self.predictor_fn)

        self.metrics_table.grant_read_write_data(self.scraper_fn)
        self.metrics_table.grant_read_write_data(self.detector_fn)

        self.html_bucket.grant_read_write(self.scraper_fn)
        self.html_bucket.grant_read(self.detector_fn)

        # Grant Parameter Store access to scraper Lambda (for Firecrawl API key)
        self.scraper_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:eu-west-2:{self.account}:parameter/PromoTracker/FirecrawlApiKey"
                ]
            )
        )

        # Grant Parameter Store access to detector Lambda (for OpenAI API key)
        self.detector_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:eu-west-2:{self.account}:parameter/PromoTracker/OpenAIApiKey"
                ]
            )
        )

        # ======================
        # Step Functions State Machine
        # ======================

        # Define tasks
        get_websites_task = tasks.LambdaInvoke(
            self, "GetWebsites",
            lambda_function=self.get_websites_fn,
            output_path="$.Payload",
        )

        scraper_task = tasks.LambdaInvoke(
            self, "ScrapeWebsite",
            lambda_function=self.scraper_fn,
            result_path="$.scraper_output",
        ).add_catch(
            sfn.Pass(self, "ScraperFailed"),
            errors=["States.ALL"],
            result_path="$.error"
        )

        detector_task = tasks.LambdaInvoke(
            self, "DetectPromotion",
            lambda_function=self.detector_fn,
            result_path="$.detector_output",
        ).add_catch(
            sfn.Pass(self, "DetectorFailed"),
            errors=["States.ALL"],
            result_path="$.error"
        )

        predictor_task = tasks.LambdaInvoke(
            self, "PredictNextSale",
            lambda_function=self.predictor_fn,
            result_path="$.predictor_output",
        ).add_catch(
            sfn.Pass(self, "PredictorFailed"),
            errors=["States.ALL"],
            result_path="$.error"
        )

        # Check if scraper succeeded before continuing
        check_scraper_success = sfn.Choice(self, "CheckScraperSuccess")

        scraper_succeeded = sfn.Condition.number_equals("$.scraper_output.Payload.statusCode", 200)

        # Success path: continue to detector
        success_path = detector_task.next(predictor_task)

        # Failure path: skip to end
        failure_path = sfn.Pass(self, "SkipProcessing")

        # Chain tasks with conditional logic
        process_website = scraper_task.next(
            check_scraper_success
                .when(scraper_succeeded, success_path)
                .otherwise(failure_path)
        )

        # Map over all websites
        process_all_websites = sfn.Map(
            self, "ProcessAllWebsites",
            max_concurrency=10,
            items_path="$.websites",
            parameters={
                "website.$": "$$.Map.Item.Value"
            }
        ).iterator(process_website)

        # Define the workflow
        workflow = get_websites_task.next(process_all_websites)

        # Create state machine
        self.state_machine = sfn.StateMachine(
            self, "PromoTrackerStateMachine",
            definition=workflow,
            timeout=Duration.minutes(30),
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self, "StateMachineLogGroup",
                    retention=logs.RetentionDays.ONE_WEEK
                ),
                level=sfn.LogLevel.ALL
            )
        )

        # ======================
        # EventBridge Scheduler
        # ======================

        # Daily trigger at 09:00 UTC
        daily_rule = events.Rule(
            self, "DailyScrapingRule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="9",
                month="*",
                week_day="*",
                year="*"
            ),
            description="Trigger promo tracking pipeline daily at 09:00 UTC"
        )

        daily_rule.add_target(
            targets.SfnStateMachine(
                self.state_machine,
                input=events.RuleTargetInput.from_object({
                    "triggered_by": "eventbridge",
                    "schedule": "daily"
                })
            )
        )

        # ======================
        # Outputs
        # ======================

        CfnOutput(self, "WebsitesTableName",
            value=self.websites_table.table_name,
            description="DynamoDB Websites table name"
        )

        CfnOutput(self, "PromotionsTableName",
            value=self.promotions_table.table_name,
            description="DynamoDB Promotions table name"
        )

        CfnOutput(self, "PredictionsTableName",
            value=self.predictions_table.table_name,
            description="DynamoDB Predictions table name"
        )

        CfnOutput(self, "MetricsTableName",
            value=self.metrics_table.table_name,
            description="DynamoDB Metrics table name"
        )

        CfnOutput(self, "HtmlBucketName",
            value=self.html_bucket.bucket_name,
            description="S3 bucket for HTML storage"
        )

        CfnOutput(self, "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="Step Functions state machine ARN"
        )
