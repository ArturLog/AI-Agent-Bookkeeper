# Gemini LLM Integration - Setup Checklist

Follow this checklist to implement and switch to Gemini LLM for image analysis.

## Phase 1: Get API Key ✅ (Before running code)

- [ ] Go to [Google AI Studio](https://aistudio.google.com/app/apikeys)
- [ ] Create a new API key (or copy existing one)
- [ ] Save the API key securely
- [ ] Ensure the key has access to Generative AI API
- [ ] **Do not commit this key to Git**

## Phase 2: Local Development Setup

### 2.1 Update Environment Variables
- [ ] Copy `src/example.env` to `src/.env` (if not already done)
- [ ] Add your Gemini API key to `.env`:
  ```
  GEMINI_API_KEY=your-key-here
  ```
- [ ] Verify other required variables are set

### 2.2 Install Dependencies
- [ ] Navigate to `src/` directory
- [ ] Install requirements: `pip install -r requirements.txt`
  - Should include `google-generativeai==0.8.0`
  - Should include `Pillow==11.3.0` and `pillow-heif==0.20.2` (from previous HEIC support)

### 2.3 Test Locally
- [ ] With virtual environment activated in `src/` directory
- [ ] Run: `python main.py`
- [ ] Verify:
  - ✅ Files are picked up correctly
  - ✅ Vision API categorization works
  - ✅ Gemini LLM analysis executes without errors
  - ✅ JSON responses are parsed correctly

### 2.4 Prepare Custom Prompts
- [ ] Read [PROMPTS_TEMPLATES.md](../PROMPTS_TEMPLATES.md)
- [ ] Prepare custom prompts for:
  - [ ] Shift hours analysis
  - [ ] Shift report analysis
- [ ] Test prompts locally (optional but recommended)
- [ ] Keep prompts in a safe location for deployment

## Phase 3: Code Structure Verification

Verify all code changes are in place:

### New Files
- [ ] `src/services/llm_service.py` exists
  - [ ] Contains `LLMService` class
  - [ ] Has `analyze_shift_hours()` method
  - [ ] Has `analyze_shift_report()` method
  - [ ] Has `set_custom_prompts()` method

### Modified Files
- [ ] `src/config.py`
  - [ ] Contains `GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")`
  - [ ] `validate_config()` checks for `GEMINI_API_KEY`

- [ ] `src/main.py`
  - [ ] Imports `LLMService` from services
  - [ ] `PipelineProcessor` initializes `self.llm = LLMService()`
  - [ ] Analysis uses `self.llm.analyze_shift_hours()` (not `self.vision`)
  - [ ] Analysis uses `self.llm.analyze_shift_report()` (not `self.vision`)

- [ ] `src/services/__init__.py`
  - [ ] Exports `LLMService`

- [ ] `src/requirements.txt`
  - [ ] Contains `google-generativeai==0.8.0`

- [ ] `src/example.env`
  - [ ] Contains `GEMINI_API_KEY=` field

### Documentation
- [ ] `GEMINI_SETUP.md` exists (setup guide)
- [ ] `PROMPTS_TEMPLATES.md` exists (prompt guide)

## Phase 4: Infrastructure Setup (GCP Deployment)

### 4.1 Prepare Terraform Variables
- [ ] Copy `infrastructure/example.tfvars` to `infrastructure/terraform.tfvars`
- [ ] Fill in all required values:
  - [ ] `project_id`
  - [ ] `region`
  - [ ] `agent_email`
  - [ ] `agent_email_password`
  - [ ] `agent_smtp_server`
  - [ ] `agent_smtp_port`
  - [ ] `email_receiver`
  - [ ] `google_drive_folder_id`
  - [ ] `spreadsheet_id`
  - [ ] `gemini_api_key` ← NEW

### 4.2 Verify Terraform Configuration
- [ ] `infrastructure/variables.tf`
  - [ ] Contains `gemini_api_key` variable with `sensitive = true`

- [ ] `infrastructure/main.tf`
  - [ ] `aiplatform.googleapis.com` is in the enabled services list
  - [ ] `google_secret_manager_secret "gemini_api_key"` resource exists
  - [ ] `google_secret_manager_secret_version "gemini_api_key_version"` exists
  - [ ] `google_secret_manager_secret_iam_member "gemini_secret_access"` exists
  - [ ] Cloud Function has secret environment variable for `GEMINI_API_KEY`

### 4.3 Deploy to GCP
- [ ] Navigate to `infrastructure/` directory
- [ ] Run: `terraform init` (if first time)
- [ ] Run: `terraform plan` and verify changes look correct
- [ ] Run: `terraform apply` and confirm deployment
- [ ] Wait for cloud function to deploy (~5 minutes)

### 4.4 Verify GCP Deployment
- [ ] Check Cloud Console:
  - [ ] Cloud Function "monthly-ingestion" is deployed
  - [ ] Cloud Scheduler job is created
  - [ ] Secret Manager has `gemini-api-key` secret
  - [ ] Service Account has `secretmanager.secretAccessor` role
  - [ ] AI Platform API is enabled

## Phase 5: Testing

### 5.1 Local Testing with Real Data
- [ ] Prepare test images (shift hours and report samples)
- [ ] Place in local test folder
- [ ] Create `test_local.py`:
  ```python
  import os
  from src.main import PipelineProcessor
  
  os.chdir('src')
  processor = PipelineProcessor()
  results = processor.run()
  print(results)
  ```
- [ ] Run test and verify output

### 5.2 Monitor First Cloud Execution
After deployment:
- [ ] In GCP Console, check Cloud Function logs
- [ ] Verify no errors in initialization
- [ ] Check for "Starting ingestion..." message
- [ ] Verify Gemini API is being called successfully
- [ ] Check parsed JSON results

### 5.3 Troubleshooting
If encountering errors:
- [ ] Check Cloud Function logs in GCP Console
- [ ] Review [GEMINI_SETUP.md](../GEMINI_SETUP.md) troubleshooting section
- [ ] Verify API key is valid and hasn't expired
- [ ] Ensure custom prompts are returning valid JSON
- [ ] Check quota usage in Google AI Studio

## Phase 6: Production Optimization (Optional)

- [ ] Increase Cloud Function timeout if processing large batches
- [ ] Monitor API costs and adjust as needed
- [ ] Set up alerts for errors
- [ ] Regular review of prompts and results quality
- [ ] Consider batching or rate limiting if needed

## Rollback Plan (If Needed)

If Gemini doesn't work as expected:

### Quick Rollback
- [ ] Modify `src/main.py` to use `self.vision` instead of `self.llm`
- [ ] Keep Vision API for both categorization and analysis (temporary)
- [ ] Redeploy to GCP

### Debug Mode
- [ ] Keep Gemini but add error handling to fall back to Vision
- [ ] Set `DEBUG=true` in environment to log intermediate results
- [ ] Gradually refine prompts while maintaining stability

## Timeline

| Phase | Estimated Time |
|-------|-----------------|
| Phase 1: Get API Key | 5-10 min |
| Phase 2: Local Setup | 15-30 min |
| Phase 3: Code Verification | 10 min |
| Phase 4: Infrastructure | 30-45 min |
| Phase 5: Testing | 20-30 min |
| Phase 6: Optimization | 30 min (optional) |
| **Total** | **2-3 hours** |

## Success Criteria

✅ Setup is complete when:

1. Local execution: `python src/main.py` works without errors
2. Gemini API: Images are processed with LLM analysis
3. JSON Parsing: Results are correctly extracted and formatted
4. GCP Deployment: Cloud Function runs successfully on schedule
5. Custom Prompts: Analysis results match your expectations
6. Integration: Data flows correctly into Google Sheets

## Next Steps After Completion

- [ ] Share custom prompts with team (if applicable)
- [ ] Set up monitoring and alerting
- [ ] Document any customizations made
- [ ] Plan for monthly maintenance/review
- [ ] Archive previous Vision API if no longer needed

## Support References

- [GEMINI_SETUP.md](../GEMINI_SETUP.md) - Detailed setup guide
- [PROMPTS_TEMPLATES.md](../PROMPTS_TEMPLATES.md) - Prompt customization
- [LLM Service Code](src/services/llm_service.py) - Implementation details
- [Google AI Studio](https://aistudio.google.com) - API key management
- [Google Cloud Console](https://console.cloud.google.com) - GCP monitoring

---

**Last Updated:** April 3, 2026  
**Version:** 1.0  
**Status:** Ready for Implementation
