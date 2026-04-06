# Gemini LLM Integration Setup Guide

This document explains the migration from Vision API to Gemini LLM for image analysis.

## What Changed

### Before (Vision API)
- Used Google Cloud Vision API for **both** categorization and detailed analysis
- Limited accuracy for complex documents with handwriting

### After (Gemini LLM)
- **Vision API**: Still used for categorization (works well) ✅
- **Gemini LLM**: Now used for detailed analysis (better for complex documents)
  - Shift Hours extraction
  - Shift Report extraction

## Architecture

```
Google Drive (Images)
    ↓
DriveService (download)
    ↓
HEIC → JPEG conversion
    ↓
VisionService (categorize) → "shift-hours" or "shift-report"
    ↓
LLMService (analyze with custom prompts) ← Gemini
    ↓
SheetsService (aggregate)
    ↓
EmailService (notify)
```

## Prerequisites

1. **Gemini API Key**
   - Get from Google AI Studio: https://aistudio.google.com/app/apikeys
   - Ensure Generative AI API is enabled in GCP project
   - Has quota for image analysis

2. **GCP Project Setup**
   - `aiplatform.googleapis.com` API enabled (handled by Terraform)
   - Gemini API key stored in Secret Manager (handled by Terraform)

## Installation & Configuration

### Local Development

1. **Copy environment template**
   ```bash
   cp src/example.env src/.env
   ```

2. **Add Gemini API Key to `.env`**
   ```bash
   GEMINI_API_KEY=your-api-key-here
   ```

3. **Install dependencies**
   ```bash
   cd src
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Test locally**
   ```bash
   python main.py
   ```

## Infrastructure Deployment

### Terraform Configuration

New variables in `infrastructure/terraform.tfvars`:

```hcl
gemini_api_key = "your-gemini-api-key-here"
```

### Deploy Steps

1. **Update terraform.tfvars**
   ```hcl
   project_id          = "your-project"
   region              = "us-central1"
   agent_email         = "your-email@gmail.com"
   agent_email_password = "your-app-password"
   agent_smtp_server   = "smtp.gmail.com"
   agent_smtp_port     = "587"
   email_receiver      = "recipient@example.com"
   google_drive_folder_id = "folder-id"
   spreadsheet_id      = "sheet-id"
   gemini_api_key      = "your-gemini-key"  # NEW
   ```

2. **Apply Terraform**
   ```bash
   cd infrastructure
   terraform init
   terraform plan
   terraform apply
   ```

3. **Verify deployment**
   - Check Cloud Function deployed successfully
   - Verify Secret Manager stores `gemini-api-key`
   - Check Cloud Scheduler trigger is active

## Customizing Prompts

See [PROMPTS_TEMPLATES.md](PROMPTS_TEMPLATES.md) for detailed guide on:
- Expected JSON format from Gemini
- How to write custom prompts
- Examples for shift hours and reports
- Local testing your prompts

## Code Structure

### New Files
- `src/services/llm_service.py` - Gemini integration

### Modified Files
- `src/main.py` - Uses LLMService for analysis instead of VisionService
- `src/config.py` - Added GEMINI_API_KEY configuration
- `src/requirements.txt` - Added `google-generativeai==0.8.0`
- `src/services/__init__.py` - Exports LLMService
- `src/example.env` - Added GEMINI_API_KEY field
- `infrastructure/variables.tf` - Added gemini_api_key variable
- `infrastructure/main.tf` - Enabled aiplatform API, added secret for key

### Unchanged (Still Works)
- `src/services/vision_service.py` - Categorization logic unchanged
- `src/services/drive_service.py` - File retrieval unchanged
- `src/services/sheets_service.py` - Data aggregation unchanged
- `src/services/email_service.py` - Notifications unchanged
- `src/utils/parser.py` - Parsing utilities unchanged

## LLMService API

### Basic Usage

```python
from services import LLMService

llm = LLMService()

# Analyze shift hours
result = llm.analyze_shift_hours(image_bytes)
# Returns: {"type": "shift-hours", "name": "...", "month": "...", "year": "...", "data": [...]}

# Analyze shift report
result = llm.analyze_shift_report(image_bytes)
# Returns: {"type": "shift-report", "netto_8": 0.0, "netto_23": 0.0, "tips": 0.0, ...}
```

### Custom Prompts

```python
custom_hours_prompt = """Write your custom prompt here..."""
custom_report_prompt = """Write your custom prompt here..."""

llm.set_custom_prompts(
    shift_hours_prompt=custom_hours_prompt,
    shift_report_prompt=custom_report_prompt
)
```

## Troubleshooting

### "GEMINI_API_KEY not found" Error

**Local Development**
- Ensure `.env` file exists in `src/` directory
- Verify `GEMINI_API_KEY=...` is set
- Restart Python process

**Cloud Deployment**
- Check Cloud Function environment variables in GCP Console
- Verify Secret Manager has `gemini-api-key` secret
- Check service account has `secretmanager.secretAccessor` role

### "Invalid JSON" from Gemini

- Gemini may be adding explanations around JSON
- Parser tries to extract JSON automatically
- If parsing fails, check logs in Cloud Function
- Adjust prompt to emphasize "ONLY JSON"

### API Rate Limits

- Gemini has rate limits per API key
- Monitor usage in Google AI Studio dashboard
- Consider batching or spreading requests
- Request higher limits if needed

### HEIC Support Issues

- Ensure `Pillow==11.3.0` and `pillow-heif==0.20.2` are installed
- HEIC files are automatically converted to JPEG before Gemini
- Check conversion in logs: "Converting HEIC to JPEG"

## Performance Considerations

1. **Memory**: Cloud Function configured with 256MB (sufficient)
2. **Timeout**: 60 seconds (may need increase for large batches of images)
3. **Model**: Using `gemini-2.0-flash` (fast and efficient)
4. **Batch Size**: Process one image at a time (manageable)

## Security Best Practices

1. **API Key Management**
   - Never commit API keys to version control
   - Always use Secret Manager in production
   - Rotate keys regularly

2. **Permissions**
   - Service account has minimal required permissions
   - Restricted to specific GCS buckets
   - Can only access its own secrets

3. **Monitoring**
   - Check Cloud Function logs regularly
   - Set up alerts for errors
   - Monitor API usage

## Next Steps

1. ✅ Get Gemini API Key
2. ✅ Update `.env` with key (local) or terraform (prod)
3. ⬜ Create custom prompts (see [PROMPTS_TEMPLATES.md](PROMPTS_TEMPLATES.md))
4. ⬜ Test locally with sample images
5. ⬜ Deploy to GCP
6. ⬜ Monitor first run with real data

## Rollback Plan

If Gemini doesn't work as expected:

1. **Switch back to Vision API** (temporary)
   - Revert `main.py` to use `self.vision` instead of `self.llm`
   - Keep Vision API enabled in Terraform
   - Cost trade-off: Vision is less accurate but more stable

2. **Stay on Gemini, retry**
   - Refine custom prompts
   - Check Gemini model version
   - Review error logs

## References

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Prompts Best Practices](PROMPTS_TEMPLATES.md)
- [Vision API Categorization](src/services/vision_service.py)
- [LLM Service Implementation](src/services/llm_service.py)
