#!/usr/bin/env python3
"""
AWS CDK application entry point for the Stripe payments infrastructure.
"""
import aws_cdk as cdk

from stacks.payments_stack import PaymentsStack

app = cdk.App()

PaymentsStack(
    app,
    "PaymentsStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
    description="Stripe card-payment checkout infrastructure (KAN-19)",
)

app.synth()
