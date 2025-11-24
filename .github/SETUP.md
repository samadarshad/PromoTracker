# GitHub Actions Setup Guide

This guide will help you configure GitHub Actions for automated testing in your PromoTracker repository.

## Quick Start (5 minutes)

### Step 1: Configure GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following two secrets:

#### Required Secrets

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `AWS_ACCESS_KEY_ID` | AWS access key | AWS Console → IAM → Users → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Same as above |


### Step 2: Create AWS IAM User for GitHub Actions

Create a dedicated IAM user with these permissions:

```bash
# Create IAM user
aws iam create-user --user-name github-actions-promo-tracker

# Attach policies (adjust as needed for your security requirements)
aws iam attach-user-policy \
  --user-name github-actions-promo-tracker \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Create access key
aws iam create-access-key --user-name github-actions-promo-tracker
```

**Important**: Save the access key ID and secret - you'll use these as GitHub secrets.

#### Minimum IAM Permissions (Recommended)

Instead of PowerUserAccess, create a custom policy with only required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "lambda:*",
        "dynamodb:*",
        "s3:*",
        "ssm:*",
        "iam:GetRole",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:PassRole",
        "logs:*",
        "states:*",
        "events:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step 3: Verify Workflow Files

Ensure these files exist in your repository:

```bash
.github/
├── workflows/
│   ├── test-pr.yml           # Main testing workflow
│   ├── cleanup-test-stack.yml # Cleanup workflow
│   └── README.md              # Workflows documentation
└── SETUP.md                   # This file
```

### Step 4: Test the Setup

1. Create a new branch:
   ```bash
   git checkout -b test/github-actions-setup
   ```

2. Make a small change (e.g., update README):
   ```bash
   echo "# Testing GitHub Actions" >> README.md
   git add README.md
   git commit -m "Test: GitHub Actions setup"
   git push origin test/github-actions-setup
   ```

3. Create a pull request on GitHub

4. Check the **Actions** tab to see workflows running

5. Once tests pass, close or merge the PR to trigger cleanup

## Workflow Details

### Pull Request Testing Workflow

**File**: `.github/workflows/test-pr.yml`

**Triggers**: PR opened, synchronized, or reopened to `main` or `develop`

**Steps**:
1. ✅ Run unit tests (fast)
2. 🚀 Deploy TestStack to AWS
3. 🔗 Run integration tests
4. 🎯 Run end-to-end tests
5. 💾 Keep stack running during PR review

**Duration**: 5-10 minutes

### Cleanup Workflow

**File**: `.github/workflows/cleanup-test-stack.yml`

**Triggers**: PR closed or merged, or manual dispatch

**Steps**:
1. 🗑️ Empty S3 bucket
2. 🔥 Destroy TestStack
3. 🔑 Remove Parameter Store keys
4. ✅ Verify cleanup complete

**Duration**: 2-3 minutes

## Monitoring

### View Test Results

1. Go to **Actions** tab
2. Click on a workflow run
3. Expand jobs to see detailed logs

### Check AWS Resources

```bash
# List active test stacks
aws cloudformation describe-stacks --region eu-west-2 \
  --query 'Stacks[?StackName==`TestStack`]' \
  --output table

# Check Parameter Store
aws ssm describe-parameters --region eu-west-2 \
  --filters "Key=Name,Values=/PromoTracker/Test/" \
  --output table
```

## Troubleshooting

### Issue: Workflow fails with "AWS credentials not configured"

**Solution**: Verify GitHub secrets are set correctly

```bash
# Check if secrets exist (you won't see values)
# Go to: Settings → Secrets and variables → Actions
```

### Issue: "CDK bootstrap required"

**Solution**: Bootstrap CDK in your AWS account

```bash
cdk bootstrap aws://YOUR_ACCOUNT_ID/eu-west-2
```

### Issue: Test stack already exists

**Solution**: Run manual cleanup

1. Go to **Actions** tab
2. Select **Cleanup Test Stack**
3. Click **Run workflow**

Or cleanup manually:
```bash
./scripts/cleanup_test_stack.sh
```

### Issue: S3 bucket deletion fails

**Cause**: Bucket not empty

**Solution**: Empty bucket first

```bash
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name TestStack --region eu-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`TestHtmlBucketName`].OutputValue' \
  --output text)

aws s3 rm "s3://$BUCKET_NAME" --recursive --region eu-west-2
```

## Cost Management

### Expected Costs

- **Unit tests**: Free (GitHub runners)
- **Per PR test run**: $0.50 - $2.00
- **Auto-cleanup**: Prevents ongoing charges

### Cost Optimization Tips

1. **Use draft PRs** for work-in-progress (tests don't run)
2. **Combine commits** to reduce test runs
3. **Manual cleanup** if needed via workflow dispatch
4. **Monitor costs** in AWS Cost Explorer

### Set Up Billing Alerts

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name GitHubActions-TestStack-Cost \
  --alarm-description "Alert when test costs exceed $10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Use least privilege** IAM permissions
3. **Rotate AWS keys** regularly
4. **Enable AWS CloudTrail** for audit logging
5. **Review workflow logs** for sensitive data

## Advanced Configuration

### Enable Branch Protection

Require tests to pass before merging:

1. Go to **Settings** → **Branches**
2. Add rule for `main` branch
3. Check **Require status checks to pass**
4. Select:
   - ✅ Unit Tests
   - ✅ Integration Tests
   - ✅ End-to-End Tests

### Manual Cleanup Trigger

You can manually trigger cleanup anytime:

1. **Actions** tab → **Cleanup Test Stack**
2. **Run workflow** → Select branch
3. **Run workflow** button

### Custom Test Configuration

Edit workflow files to customize:

- **Test timeout**: Adjust in `test-pr.yml`
- **Branches**: Change trigger branches
- **Concurrency**: Modify concurrency settings
- **Notifications**: Add Slack/email notifications

## Verification Checklist

- [ ] GitHub secrets configured (4 secrets)
- [ ] AWS IAM user created with permissions
- [ ] CDK bootstrapped in AWS account
- [ ] Workflow files present in repository
- [ ] Test PR created successfully
- [ ] All tests passing in Actions tab
- [ ] Cleanup workflow runs on PR close
- [ ] Test stack removed from AWS

## Getting Help

- **Workflow issues**: Check [.github/workflows/README.md](workflows/README.md)
- **Test issues**: Check [tests/README.md](../tests/README.md)
- **AWS issues**: Review AWS CloudWatch Logs
- **General help**: See [TESTING_SUMMARY.md](../TESTING_SUMMARY.md)

## Next Steps

After setup is complete:

1. ✅ All PRs will automatically run tests
2. ✅ Test stacks auto-cleanup on PR close
3. ✅ Monitor costs in AWS console
4. 📊 Consider adding test coverage reporting
5. 🔔 Set up failure notifications (optional)

---

**Setup complete!** Your repository now has automated testing with GitHub Actions. 🎉
