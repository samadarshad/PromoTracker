from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    aws_logs as logs,
    aws_apigateway as apigateway,
    CfnOutput,
    Tags,
)
from constructs import Construct

class TestStack(Stack):
    """
    Test stack for serverless application testing.
    Optimized for temporary deployments with aggressive cleanup policies.
    """

    def __init__(self, scope: Construct, construct_id: str, env_suffix: str = "test", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Tag all resources for easy identification
        Tags.of(self).add("Environment", env_suffix)
        Tags.of(self).add("Purpose", "Testing")
        Tags.of(self).add("ManagedBy", "CDK")

        # ======================
        # DynamoDB Tables (Test Configuration)
        # ======================

        # Websites Table - Test version
        self.websites_table = dynamodb.Table(
            self, "TestWebsitesTable",
            partition_key=dynamodb.Attribute(
                name="website_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=False,  # Disabled for test
            removal_policy=RemovalPolicy.DESTROY,  # Auto-delete on stack destroy
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

        # Promotions Table - Test version
        self.promotions_table = dynamodb.Table(
            self, "TestPromotionsTable",
            partition_key=dynamodb.Attribute(
                name="promotion_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=False,
            removal_policy=RemovalPolicy.DESTROY,
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

        # Predictions Table - Test version
        self.predictions_table = dynamodb.Table(
            self, "TestPredictionsTable",
            partition_key=dynamodb.Attribute(
                name="website_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="prediction_timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=False,
            removal_policy=RemovalPolicy.DESTROY,
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

        # Scraping Metrics Table (with TTL) - Test version
        self.metrics_table = dynamodb.Table(
            self, "TestScrapingMetricsTable",
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
        # S3 Buckets (Test Configuration)
        # ======================

        # HTML Storage Bucket - Test version with aggressive lifecycle
        self.html_bucket = s3.Bucket(
            self, "TestHtmlBucket",
            versioned=False,  # Disabled for test
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(1),  # Auto-delete after 1 day
                    abort_incomplete_multipart_upload_after=Duration.days(1)
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,  # Auto-delete on stack destroy
        )

        # ======================
        # Lambda Layers
        # ======================

        # Shared code layer (custom utilities)
        self.shared_code_layer = lambda_.LayerVersion(
            self, "TestSharedCodeLayer",
            code=lambda_.Code.from_asset("../layers/shared_code"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared internal code (logging, DB, S3 helpers) - Test"
        )

        # Dependencies layer (third-party packages: boto3, requests, etc.)
        self.dependencies_layer = lambda_.LayerVersion(
            self, "TestDependenciesLayer",
            code=lambda_.Code.from_asset("../layers/dependencies"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Third-party dependencies (boto3, requests, pydantic, etc.) - Test"
        )

        # Detector-specific layer for LLM dependencies
        self.detector_layer = lambda_.LayerVersion(
            self, "TestDetectorLayer",
            code=lambda_.Code.from_asset("../lambdas/detector_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Detector-specific dependencies (openai, beautifulsoup4, lxml) - Test"
        )

        # ======================
        # Mock API Infrastructure
        # ======================

        # Mock Firecrawl API Lambda
        self.mock_firecrawl_fn = lambda_.Function(
            self, "TestMockFirecrawlFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/mock_firecrawl"),
            timeout=Duration.seconds(10),
            memory_size=128,
            log_retention=logs.RetentionDays.ONE_DAY,
            description="Mock Firecrawl API for testing"
        )

        # Mock OpenAI API Lambda
        self.mock_openai_fn = lambda_.Function(
            self, "TestMockOpenAIFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/mock_openai"),
            timeout=Duration.seconds(10),
            memory_size=128,
            log_retention=logs.RetentionDays.ONE_DAY,
            description="Mock OpenAI API for testing"
        )

        # API Gateway for mock APIs
        self.mock_api = apigateway.RestApi(
            self, "TestMockAPIGateway",
            rest_api_name="PromoTracker-Test-Mock-API",
            description="Mock API endpoints for testing (Firecrawl and OpenAI)",
            deploy=True,
            deploy_options=apigateway.StageOptions(
                stage_name="v1",
                throttling_rate_limit=100,
                throttling_burst_limit=200
            )
        )

        # Firecrawl mock endpoint: POST /v2/scrape
        firecrawl_v2 = self.mock_api.root.add_resource("v2")
        firecrawl_scrape = firecrawl_v2.add_resource("scrape")
        firecrawl_scrape.add_method(
            "POST",
            apigateway.LambdaIntegration(self.mock_firecrawl_fn)
        )

        # OpenAI mock endpoint: POST /v1/chat/completions
        openai_v1 = self.mock_api.root.add_resource("v1")
        openai_chat = openai_v1.add_resource("chat")
        openai_completions = openai_chat.add_resource("completions")
        openai_completions.add_method(
            "POST",
            apigateway.LambdaIntegration(self.mock_openai_fn)
        )

        # Build mock API URLs
        mock_firecrawl_url = f"{self.mock_api.url}v2/scrape"
        mock_openai_url = f"{self.mock_api.url}v1"

        # Common environment variables for all Lambdas
        common_env = {
            "WEBSITES_TABLE": self.websites_table.table_name,
            "PROMOTIONS_TABLE": self.promotions_table.table_name,
            "PREDICTIONS_TABLE": self.predictions_table.table_name,
            "METRICS_TABLE": self.metrics_table.table_name,
            "HTML_BUCKET": self.html_bucket.bucket_name,
            "ENVIRONMENT": env_suffix,  # Indicate test environment
            # Mock API URLs for testing
            "FIRECRAWL_API_URL": mock_firecrawl_url,
            "OPENAI_API_BASE_URL": mock_openai_url,
        }

        # Get Websites Lambda - Test version
        self.get_websites_fn = lambda_.Function(
            self, "TestGetWebsitesFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/get_websites"),
            layers=[self.dependencies_layer, self.shared_code_layer],
            environment=common_env,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_DAY,  # Shorter retention for test
        )

        # Scraper Lambda - Test version
        self.scraper_fn = lambda_.Function(
            self, "TestScraperFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/scraper"),
            layers=[self.dependencies_layer, self.shared_code_layer],
            environment=common_env,
            timeout=Duration.seconds(300),
            memory_size=512,
            log_retention=logs.RetentionDays.ONE_DAY,
        )

        # Detector Lambda - Test version
        self.detector_fn = lambda_.Function(
            self, "TestDetectorFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/detector"),
            layers=[self.dependencies_layer, self.shared_code_layer, self.detector_layer],
            environment=common_env,
            timeout=Duration.seconds(300),
            memory_size=1024,
            log_retention=logs.RetentionDays.ONE_DAY,
        )

        # Predictor Lambda - Test version
        self.predictor_fn = lambda_.Function(
            self, "TestPredictorFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambdas/predictor"),
            layers=[self.dependencies_layer, self.shared_code_layer],
            environment=common_env,
            timeout=Duration.seconds(300),
            memory_size=1024,
            log_retention=logs.RetentionDays.ONE_DAY,
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

        # Grant Parameter Store access to scraper Lambda (for test Firecrawl API key)
        self.scraper_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:eu-west-2:{self.account}:parameter/PromoTracker/Test/FirecrawlApiKey",
                    f"arn:aws:ssm:eu-west-2:{self.account}:parameter/PromoTracker/FirecrawlApiKey"  # Fallback to prod
                ]
            )
        )

        # Grant Parameter Store access to detector Lambda (for test OpenAI API key)
        self.detector_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:eu-west-2:{self.account}:parameter/PromoTracker/Test/OpenAIApiKey",
                    f"arn:aws:ssm:eu-west-2:{self.account}:parameter/PromoTracker/OpenAIApiKey"  # Fallback to prod
                ]
            )
        )

        # ======================
        # Step Functions State Machine
        # ======================

        # Define tasks
        get_websites_task = tasks.LambdaInvoke(
            self, "TestGetWebsites",
            lambda_function=self.get_websites_fn,
            output_path="$.Payload",
        )

        scraper_task = tasks.LambdaInvoke(
            self, "TestScrapeWebsite",
            lambda_function=self.scraper_fn,
            result_path="$.scraper_output",
        ).add_catch(
            sfn.Pass(self, "TestScraperFailed"),
            errors=["States.ALL"],
            result_path="$.error"
        )

        detector_task = tasks.LambdaInvoke(
            self, "TestDetectPromotion",
            lambda_function=self.detector_fn,
            result_path="$.detector_output",
        ).add_catch(
            sfn.Pass(self, "TestDetectorFailed"),
            errors=["States.ALL"],
            result_path="$.error"
        )

        predictor_task = tasks.LambdaInvoke(
            self, "TestPredictNextSale",
            lambda_function=self.predictor_fn,
            result_path="$.predictor_output",
        ).add_catch(
            sfn.Pass(self, "TestPredictorFailed"),
            errors=["States.ALL"],
            result_path="$.error"
        )

        # Check if scraper succeeded before continuing
        check_scraper_success = sfn.Choice(self, "TestCheckScraperSuccess")

        scraper_succeeded = sfn.Condition.number_equals("$.scraper_output.Payload.statusCode", 200)

        # Success path: continue to detector
        success_path = detector_task.next(predictor_task)

        # Failure path: skip to end
        failure_path = sfn.Pass(self, "TestSkipProcessing")

        # Chain tasks with conditional logic
        process_website = scraper_task.next(
            check_scraper_success
                .when(scraper_succeeded, success_path)
                .otherwise(failure_path)
        )

        # Map over all websites
        process_all_websites = sfn.Map(
            self, "TestProcessAllWebsites",
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
            self, "TestPromoTrackerStateMachine",
            definition=workflow,
            timeout=Duration.minutes(30),
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self, "TestStateMachineLogGroup",
                    retention=logs.RetentionDays.ONE_DAY,
                    removal_policy=RemovalPolicy.DESTROY
                ),
                level=sfn.LogLevel.ALL
            )
        )

        # ======================
        # Outputs
        # ======================

        CfnOutput(self, "TestWebsitesTableName",
            value=self.websites_table.table_name,
            description="Test DynamoDB Websites table name"
        )

        CfnOutput(self, "TestPromotionsTableName",
            value=self.promotions_table.table_name,
            description="Test DynamoDB Promotions table name"
        )

        CfnOutput(self, "TestPredictionsTableName",
            value=self.predictions_table.table_name,
            description="Test DynamoDB Predictions table name"
        )

        CfnOutput(self, "TestMetricsTableName",
            value=self.metrics_table.table_name,
            description="Test DynamoDB Metrics table name"
        )

        CfnOutput(self, "TestHtmlBucketName",
            value=self.html_bucket.bucket_name,
            description="Test S3 bucket for HTML storage"
        )

        CfnOutput(self, "TestStateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="Test Step Functions state machine ARN"
        )

        # Output Lambda function ARNs for direct invocation in tests
        CfnOutput(self, "TestGetWebsitesFunctionArn",
            value=self.get_websites_fn.function_arn,
            description="Test GetWebsites Lambda function ARN"
        )

        CfnOutput(self, "TestScraperFunctionArn",
            value=self.scraper_fn.function_arn,
            description="Test Scraper Lambda function ARN"
        )

        CfnOutput(self, "TestDetectorFunctionArn",
            value=self.detector_fn.function_arn,
            description="Test Detector Lambda function ARN"
        )

        CfnOutput(self, "TestPredictorFunctionArn",
            value=self.predictor_fn.function_arn,
            description="Test Predictor Lambda function ARN"
        )

        # Output Lambda function names for easy invocation
        CfnOutput(self, "TestGetWebsitesFunctionName",
            value=self.get_websites_fn.function_name,
            description="Test GetWebsites Lambda function name"
        )

        CfnOutput(self, "TestScraperFunctionName",
            value=self.scraper_fn.function_name,
            description="Test Scraper Lambda function name"
        )

        CfnOutput(self, "TestDetectorFunctionName",
            value=self.detector_fn.function_name,
            description="Test Detector Lambda function name"
        )

        CfnOutput(self, "TestPredictorFunctionName",
            value=self.predictor_fn.function_name,
            description="Test Predictor Lambda function name"
        )

        # Output Mock API URLs
        CfnOutput(self, "TestMockAPIURL",
            value=self.mock_api.url,
            description="Test Mock API Gateway base URL"
        )

        CfnOutput(self, "TestMockFirecrawlURL",
            value=mock_firecrawl_url,
            description="Test Mock Firecrawl API endpoint URL"
        )

        CfnOutput(self, "TestMockOpenAIURL",
            value=mock_openai_url,
            description="Test Mock OpenAI API base URL"
        )
