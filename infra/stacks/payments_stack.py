"""
AWS CDK stack for the Stripe payments infrastructure.

Provisions:
  - DynamoDB: payments table (with GSI on intent_id) + idempotency_keys table
  - SNS topic: payment events
  - Lambda: receipt writer (SNS → S3)
  - S3: receipts bucket
  - CloudWatch: audit log group (/payments/audit)
  - Secrets Manager: Stripe webhook signing secret placeholder
  - IAM: least-privilege roles for each resource
"""
import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
)
from constructs import Construct


class PaymentsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── DynamoDB: Payments table ──────────────────────────────────────
        self.payments_table = dynamodb.Table(
            self,
            "PaymentsTable",
            table_name="payments",
            partition_key=dynamodb.Attribute(
                name="payment_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
        )
        # GSI on intent_id — used by webhook handler to look up by Stripe ID
        self.payments_table.add_global_secondary_index(
            index_name="intent_id-index",
            partition_key=dynamodb.Attribute(
                name="intent_id",
                type=dynamodb.AttributeType.STRING,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # ── DynamoDB: Idempotency table ───────────────────────────────────
        self.idempotency_table = dynamodb.Table(
            self,
            "IdempotencyTable",
            table_name="payment_idempotency_keys",
            partition_key=dynamodb.Attribute(
                name="idempotency_key",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl",  # auto-expire keys after 24h
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
        )

        # ── S3: Receipts bucket ───────────────────────────────────────────
        self.receipts_bucket = s3.Bucket(
            self,
            "ReceiptsBucket",
            bucket_name=f"payments-receipts-{self.account}-{self.region}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="archive-old-receipts",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        )
                    ],
                )
            ],
        )

        # ── SNS: Payment events topic ─────────────────────────────────────
        self.payment_events_topic = sns.Topic(
            self,
            "PaymentEventsTopic",
            topic_name="payment-events",
            display_name="Payment Domain Events",
        )

        # ── CloudWatch: Audit log group ───────────────────────────────────
        self.audit_log_group = logs.LogGroup(
            self,
            "PaymentsAuditLogGroup",
            log_group_name="/payments/audit",
            retention=logs.RetentionDays.ONE_YEAR,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ── Secrets Manager: Stripe credentials ──────────────────────────
        self.stripe_secret = secretsmanager.Secret(
            self,
            "StripeCredentials",
            secret_name="stripe/credentials",
            description="Stripe API keys for payment processing",
            secret_object_value={
                "STRIPE_SECRET_KEY": cdk.SecretValue.unsafe_plain_text(
                    "REPLACE_WITH_ACTUAL_KEY"
                ),
                "STRIPE_WEBHOOK_SECRET": cdk.SecretValue.unsafe_plain_text(
                    "REPLACE_WITH_ACTUAL_WEBHOOK_SECRET"
                ),
            },
        )

        # ── Lambda: Receipt handler ───────────────────────────────────────
        self.receipt_lambda = lambda_.Function(
            self,
            "ReceiptHandlerLambda",
            function_name="payment-receipt-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="receipt_handler.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "RECEIPTS_BUCKET": self.receipts_bucket.bucket_name,
                "CLOUDWATCH_LOG_GROUP": "/payments/audit",
            },
            log_retention=logs.RetentionDays.ONE_MONTH,
        )

        # Grant Lambda permissions
        self.receipts_bucket.grant_write(self.receipt_lambda)
        self.audit_log_group.grant_write(self.receipt_lambda)

        # Subscribe Lambda to SNS topic
        self.payment_events_topic.add_subscription(
            sns_subs.LambdaSubscription(self.receipt_lambda)
        )

        # ── IAM: API Backend role ─────────────────────────────────────────
        self.api_role = iam.Role(
            self,
            "PaymentsApiRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="IAM role for the payments FastAPI backend",
        )
        # DynamoDB access
        self.payments_table.grant_read_write_data(self.api_role)
        self.idempotency_table.grant_read_write_data(self.api_role)
        # SNS publish
        self.payment_events_topic.grant_publish(self.api_role)
        # CloudWatch logs
        self.audit_log_group.grant_write(self.api_role)
        # Secrets Manager read
        self.stripe_secret.grant_read(self.api_role)

        # ── CloudWatch Alarms ─────────────────────────────────────────────
        # Alarm: Lambda errors
        lambda_error_alarm = cloudwatch.Alarm(
            self,
            "ReceiptLambdaErrorAlarm",
            metric=self.receipt_lambda.metric_errors(
                period=Duration.minutes(5),
            ),
            threshold=5,
            evaluation_periods=1,
            alarm_description="Receipt Lambda error rate too high",
        )

        # ── Outputs ───────────────────────────────────────────────────────
        cdk.CfnOutput(self, "PaymentsTableName", value=self.payments_table.table_name)
        cdk.CfnOutput(self, "IdempotencyTableName", value=self.idempotency_table.table_name)
        cdk.CfnOutput(self, "ReceiptsBucketName", value=self.receipts_bucket.bucket_name)
        cdk.CfnOutput(self, "PaymentEventsTopicArn", value=self.payment_events_topic.topic_arn)
        cdk.CfnOutput(self, "AuditLogGroupName", value=self.audit_log_group.log_group_name)
        cdk.CfnOutput(self, "StripeSecretArn", value=self.stripe_secret.secret_arn)
