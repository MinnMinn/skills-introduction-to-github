"""
Tests for the PaymentsStack CDK construct.

Uses aws_cdk.assertions to verify the synthesised CloudFormation template
contains the expected resources with the correct configurations.
"""
import json

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from stacks.payments_stack import PaymentsStack


@pytest.fixture(scope="module")
def template():
    """Synthesise the stack and return the CDK template for assertions."""
    app = cdk.App()
    stack = PaymentsStack(app, "TestPaymentsStack")
    return assertions.Template.from_stack(stack)


class TestDynamoDB:
    def test_payments_table_exists(self, template):
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {"TableName": "payments"},
        )

    def test_idempotency_table_exists(self, template):
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {"TableName": "payment_idempotency_keys"},
        )

    def test_idempotency_table_has_ttl(self, template):
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "TableName": "payment_idempotency_keys",
                "TimeToLiveSpecification": {
                    "AttributeName": "ttl",
                    "Enabled": True,
                },
            },
        )

    def test_payments_table_has_point_in_time_recovery(self, template):
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "TableName": "payments",
                "PointInTimeRecoverySpecification": {
                    "PointInTimeRecoveryEnabled": True,
                },
            },
        )

    def test_payments_table_has_gsi(self, template):
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "TableName": "payments",
                "GlobalSecondaryIndexes": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "IndexName": "intent_id-index",
                    })
                ]),
            },
        )


class TestSNS:
    def test_payment_events_topic_exists(self, template):
        template.has_resource_properties(
            "AWS::SNS::Topic",
            {"TopicName": "payment-events"},
        )


class TestLambda:
    def test_receipt_lambda_exists(self, template):
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"FunctionName": "payment-receipt-handler"},
        )

    def test_lambda_subscribed_to_sns(self, template):
        template.resource_count_is("AWS::SNS::Subscription", 1)


class TestS3:
    def test_receipts_bucket_blocks_public_access(self, template):
        template.has_resource_properties(
            "AWS::S3::Bucket",
            {
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True,
                }
            },
        )


class TestSecretsManager:
    def test_stripe_secret_exists(self, template):
        template.has_resource_properties(
            "AWS::SecretsManager::Secret",
            {"Name": "stripe/credentials"},
        )


class TestCloudWatch:
    def test_audit_log_group_exists(self, template):
        template.has_resource_properties(
            "AWS::Logs::LogGroup",
            {"LogGroupName": "/payments/audit"},
        )
