#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infrastructure.infrastructure_stack import InfrastructureStack
from infrastructure.test_stack import TestStack


app = cdk.App()

# Production stack
InfrastructureStack(app, "InfrastructureStack",
    env=cdk.Environment(account='034894101750', region='eu-west-2'),
    )

# Test stack (only deployed when explicitly requested)
# Deploy with: cdk deploy TestStack
TestStack(app, "TestStack",
    env=cdk.Environment(account='034894101750', region='eu-west-2'),
    env_suffix="test"
    )

app.synth()
