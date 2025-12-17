# Nightly Evaluation Setup Guide

## Overview

The nightly evaluation workflow automatically runs golden prompt tests through the collaboration system and generates evaluation reports every night at 2 AM UTC.

## Files Created

1. **`.github/workflows/nightly-eval.yml`** - GitHub Actions workflow
2. **`scripts/run_golden_tests.py`** - Test runner script

## Setup Steps

### 1. Configure GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

- `OPENAI_API_KEY` - Your OpenAI API key
- `GEMINI_API_KEY` - Your Google Gemini API key  
- `PERPLEXITY_API_KEY` - Your Perplexity API key
- `KIMI_API_KEY` - Your Kimi API key

**Note:** These are optional - if not set, the workflow will still run but collaboration tests may fail if API keys are required.

### 2. Verify Golden Tests File

Ensure `backend/tests/examples/golden_tests_example.json` exists and contains your test cases.

### 3. Test Locally (Optional)

Test the script locally before pushing:

```bash
# Start your backend
cd backend
uvicorn main:app --reload

# In another terminal, run the test script
export API_URL=http://localhost:8000
export ORG_ID=org_demo
python scripts/run_golden_tests.py > test_results.json

# Test evaluation API
curl -X POST http://localhost:8000/api/eval/evaluate \
  -H "Content-Type: application/json" \
  -H "x-org-id: org_demo" \
  -d @test_results.json
```

## How It Works

1. **Schedule**: Runs automatically at 2 AM UTC daily (configurable)
2. **Manual Trigger**: Can be triggered manually from GitHub Actions tab
3. **Test Execution**: 
   - Starts backend with test database
   - Runs each golden test through collaboration API
   - Collects transcripts with outputs
4. **Evaluation**: 
   - Calls evaluation API with test results
   - Generates Markdown report
   - Checks for regressions
5. **Artifacts**: Uploads report as downloadable artifact
6. **PR Comments**: If triggered on PR, comments with results

## Customization

### Change Schedule

Edit `.github/workflows/nightly-eval.yml`:

```yaml
schedule:
  - cron: '0 2 * * *'  # 2 AM UTC daily
  # Examples:
  # - cron: '0 0 * * *'  # Midnight UTC
  # - cron: '0 14 * * 1'  # 2 PM UTC every Monday
```

### Adjust Regression Thresholds

Edit the "Check for regressions" step:

```yaml
# Fail if average score drops below threshold
if (( $(echo "$AVG_SCORE < 80" | bc -l) )); then
  # Change 80 to your desired threshold
```

### Use Different Golden Tests File

Set environment variable in workflow:

```yaml
- name: Run golden tests
  env:
    GOLDEN_TESTS_FILE: backend/tests/production_golden_tests.json
```

## Viewing Results

1. Go to **Actions** tab in GitHub
2. Click on **"Nightly Golden Prompt Evaluation"**
3. Click on the latest run
4. Download artifact **"nightly-eval-report-{number}"**
5. Open `nightly_report.md` for the full report

## Troubleshooting

### Workflow Fails to Start Backend

- Check that all required environment variables are set
- Verify database/Qdrant/Redis services start correctly
- Check logs in `/tmp/api.log`

### Tests Timeout

- Increase timeout in `run_golden_tests.py`:
  ```python
  timeout=300  # Increase to 600 for longer tests
  max_wait = 600  # Increase max wait time
  ```

### Missing API Keys

- Add secrets in GitHub repository settings
- Or use mock/test keys for development

### Evaluation API Returns Errors

- Ensure backend is running and healthy
- Check that `/api/eval/evaluate` endpoint is accessible
- Verify test results JSON format matches expected schema

## Next Steps

1. **Add More Golden Tests**: Expand `golden_tests_example.json` with more test cases
2. **Store Historical Data**: Consider storing evaluation results in database
3. **Set Up Alerts**: Configure notifications when regressions are detected
4. **Dashboard**: Build a dashboard to visualize trends over time

## Manual Trigger

To manually trigger the workflow:

1. Go to **Actions** tab
2. Click **"Nightly Golden Prompt Evaluation"**
3. Click **"Run workflow"** button
4. Select branch and click **"Run workflow"**


