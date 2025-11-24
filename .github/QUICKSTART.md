# GitHub Actions Quick Start

## 🚀 5-Minute Setup

### 1. Add GitHub Secrets (2 minutes)

Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these 2 secrets:

```
AWS_ACCESS_KEY_ID          = <your-aws-key-id>
AWS_SECRET_ACCESS_KEY      = <your-aws-secret>
```

**Note**: Firecrawl and OpenAI keys NOT needed - mock server is used!

### 2. Create Test PR (1 minute)

```bash
git checkout -b test/github-actions
echo "# Testing CI/CD" >> README.md
git add README.md
git commit -m "Test: GitHub Actions"
git push origin test/github-actions
```

Then create PR on GitHub.

### 3. Watch Tests Run (2 minutes)

1. Go to **Actions** tab
2. See tests running
3. Wait for ✅ or ❌

### 4. Cleanup (automatic)

Close or merge PR → Cleanup runs automatically!

## ✅ That's It!

Every PR now gets:
- ✅ Automated testing
- ✅ Real AWS validation
- ✅ Automatic cleanup

## 📚 More Details

- Setup guide: [SETUP.md](SETUP.md)
- Workflows: [workflows/README.md](workflows/README.md)
- CI/CD summary: [../CICD_SUMMARY.md](../CICD_SUMMARY.md)

## 🔧 Manual Cleanup

If needed:
1. **Actions** tab
2. **Cleanup Test Stack** workflow
3. **Run workflow**

## 💰 Cost

~$0.50 - $2.00 per PR (auto-cleanup prevents ongoing charges)

## 🆘 Troubleshooting

| Issue | Fix |
|-------|-----|
| "AWS credentials" error | Check GitHub secrets |
| Stack already exists | Run manual cleanup |
| Tests fail | Check Actions logs |

---

**Questions?** See [SETUP.md](SETUP.md) for detailed help.
