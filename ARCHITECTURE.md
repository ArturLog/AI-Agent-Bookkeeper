# AI-Agent-Bookkeeper Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI-Agent-Bookkeeper Pipeline                     │
│           Automated Monthly Bookkeeping Workflow                     │
└─────────────────────────────────────────────────────────────────────┘

                              TRIGGER
                        (Cloud Scheduler)
                              │
                              ▼
                    ┌──────────────────┐
                    │  Cloud Function  │
                    │  monthly-ingestion│
                    └──────────────────┘
                              │
                ┌─────────────┴──────────────┐
                ▼                            ▼
        ┌────────────────┐        ┌────────────────┐
        │ Google Drive   │        │ Secret Manager │
        │ (Images)       │        │ (API Keys)     │
        └─────┬──────────┘        └────────────────┘
              │
              ▼
    ┌─────────────────────────────┐
    │   DriveService              │
    │   - list_images()           │
    │   - download_file()         │
    └────────────┬────────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │   Image Conversion          │
    │   - HEIC → JPEG             │
    │   - convert_heic_to_jpeg()  │
    └────────────┬────────────────┘
                 │
    ┌────────────┴──────────────┐
    │                           │
    ▼                           ▼
┌──────────────────┐    ┌──────────────────┐
│ VisionService    │    │ StorageService   │
│ (Categorize)     │    │ (Archive)        │
│ - CATEGORIZE     │    │ - Upload to GCS  │
│ shift-hours      │    │   (monthyear/    │
│ shift-report     │    │    category/file)│
│ uncategorized    │    │                  │
└────────┬─────────┘    └──────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
[Hours]   [Reports]
    │         │
    └────┬────┘
         │
         ▼
    ┌──────────────────────────┐
    │   LLMService (GEMINI)    │
    │   - analyze_shift_hours()│
    │   - analyze_shift_report()
    │   - Custom Prompts       │
    │   - JSON Parsing         │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │  Extract & Format        │
    │  - Employee Names        │
    │  - Daily Hours           │
    │  - Financial Metrics     │
    │  - Dates/Times           │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │  SheetsService           │
    │  - Aggregate Data        │
    │  - Create Monthly Sheet  │
    │  - Format & Styling      │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │  Google Sheets           │
    │  (Aggregated Results)    │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │  EmailService            │
    │  - Send Notifications    │
    │  - Success/Error Reports │
    │  - Attach Sheet Link     │
    └──────────────────────────┘
```

## Component Details

### 1. DriveService
**Purpose:** Retrieve image files from Google Drive

**Methods:**
- `list_images(folder_id)` - Lists all image files in a folder
- `download_file(file_id)` - Downloads image content

**Mime Types Supported:**
- Standard: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- HEIC format: `.heic` (automatically converted to JPEG)

**Note:** Only categorization is performed here; no analysis.

### 2. Image Conversion (HEIC Support)
**Purpose:** Convert HEIC images to JPEG for compatibility

**Function:** `convert_heic_to_jpeg()` in `utils/parser.py`

**Process:**
1. Detect if image is HEIC format
2. Convert to RGB (if needed for JPEG)
3. Save as high-quality JPEG (95% quality)
4. Return converted bytes

**Fallback:** If conversion fails, original content is used

### 3. VisionService (Categorization)
**Purpose:** Classify images into categories using Vision API

**Methods:**
- `categorize_image(content)` - Returns category string

**Categories:**
- `"shift-hours"` - Employee time sheets with daily hours
- `"shift-report"` - Daily financial reports with sales/tips
- `"uncategorized"` - Doesn't match known patterns

**Technology:** Google Cloud Vision API (OCR + Text Detection)

**Status:** ✅ Already works well, continues to be used

### 4. StorageService (Archive)
**Purpose:** Archive processed images to Google Cloud Storage

**Methods:**
- `upload_image(content, file_name, category, month_year, mime_type)` - Stores file
- `find_file_in_month(file_name, month_year)` - Checks for duplicates

**Storage Structure:**
```
gs://project-data/
├── april2026/
│   ├── shift-hours/
│   │   ├── employee1_hours.jpg
│   │   └── employee2_hours.jpg
│   └── shift-report/
│       ├── daily_report_1.jpg
│       └── daily_report_2.jpg
└── may2026/
    ├── ...
```

**Purpose:** Prevent re-processing, maintain audit trail

### 5. LLMService (NEW - Gemini Analysis)
**Purpose:** Analyze images using Gemini LLM with custom prompts

**Methods:**
- `analyze_shift_hours(content, prompt=None)` - Extract hours data
- `analyze_shift_report(content, prompt=None)` - Extract financial data
- `set_custom_prompts(shift_hours_prompt, shift_report_prompt)` - Load custom prompts

**Model:** `gemini-2.0-flash` (fast, efficient, low-latency)

**Input:** Image bytes (JPEG format)

**Output:** Parsed JSON with structured data

**Custom Prompts:**
- User-provided prompts specific to document format
- Must return valid JSON
- Supports Polish language (for local business)
- See [PROMPTS_TEMPLATES.md](../PROMPTS_TEMPLATES.md)

#### Shift Hours Analysis Output
```json
{
    "type": "shift-hours",
    "name": "Employee Name",
    "month": "April",
    "year": 2026,
    "data": [
        {"day": 1, "hours_raw": "8h 30m", "hours_decimal": 8.5},
        {"day": 2, "hours_raw": "9 00", "hours_decimal": 9.0}
    ]
}
```

#### Shift Report Analysis Output
```json
{
    "type": "shift-report",
    "netto_8": 1450.75,
    "netto_23": 825.50,
    "netto_sum": 2276.25,
    "tips": 125.00,
    "date": "2026-04-03 21:30",
    "date_str": "3 kwietnia 2026 21:30"
}
```

### 6. SheetsService (Aggregation)
**Purpose:** Combine all extracted data into a monthly report

**Methods:**
- `update_monthly_sheet(sheet_name, reports, hours_data)` - Creates/updates sheet

**Sheet Structure:**
```
Day | Tips    | Netto 23% | Netto 8% | Total Netto | Employee1 | Employee2 | ...
----|---------|-----------|----------|-------------|-----------|-----------|----
1   | 125.00  | 825.50    | 1450.75  | 2276.25     | 8.5       | 9.0       |
2   | 0.00    | 0.00      | 0.00     | 0.00        | 8.0       | 8.5       |
...
```

**Features:**
- Auto-creates new rows for data entry
- Groups data by employee columns
- Calculates daily totals
- Formats header (bold, grey background)
- Deduplicates report entries

### 7. EmailService (Notifications)
**Purpose:** Send status updates and error alerts

**Methods:**
- `send_email(subject, message_body)` - Sends HTML email

**Triggers:**
- ✅ Process Started
- ✅ Process Completed (with results summary)
- ❌ Process Failed (with error details)

**Recipients:** Configured in environment variables

## Data Flow

### Success Path
```
Images (Drive)
   ↓ Download
Content (Bytes)
   ↓ Convert (HEIC→JPEG)
JPEG Content
   ├→ Categorize (Vision API) → Category
   ├→ Archive (GCS)
   └→ Analyze (Gemini LLM) → JSON Results
   ↓
Aggregate (Sheets)
   ↓
Store (Google Sheets)
   ↓
Notify (Email)
```

### Handling Duplicates
```
File Exists in GCS?
   YES → Skip re-download/categorize, but re-analyze
   NO  → Full pipeline (download, categorize, store, analyze)
```

### Error Handling
- Graceful degradation: Missing data marked as "UNKNOWN"
- Validation: Check for required fields
- Retry: Automatic on temporary failures
- Notification: Email alert with error details
- Logging: Cloud Function logs in GCP

## Environment Variables

### Local Development (.env)
```
GOOGLE_DRIVE_FOLDER_ID=...     # Google Drive folder with images
DATA_BUCKET=...                # GCS bucket for storage
SMTP_SERVER=...                # Email server (e.g., smtp.gmail.com)
SMTP_PORT=...                  # Email port (usually 587)
SENDER_EMAIL=...               # Email sender address
RECEIVER_EMAIL=...             # Email recipient address
EMAIL_PASSWORD=...             # Email sender password
SPREADSHEET_ID=...             # Google Sheets ID
GEMINI_API_KEY=...             # Gemini LLM API key
```

### Cloud Deployment (Terraform/Secret Manager)
```
EMAIL_PASSWORD  → Secret Manager (email_password)
GEMINI_API_KEY  → Secret Manager (gemini-api-key)
Other vars      → Environment Variables (Cloud Function config)
```

## Key Differences: Vision API vs. Gemini LLM

| Aspect | Vision API | Gemini LLM |
|--------|-----------|-----------|
| **Purpose** | Categorization (works well) | Detailed analysis |
| **Input** | Image bytes | Image bytes + Custom prompt |
| **Output** | Text/categories | Structured JSON |
| **Accuracy** | Good for text detection | Better for specific extraction |
| **Cost** | Lower | Moderate |
| **Customization** | Limited | Full control via prompts |
| **Learning** | Rule-based | LLM-based understanding |
| **Polish Support** | Good (OCR) | Excellent (LLM) |

## Security Considerations

1. **API Keys:** Stored in Secret Manager, not in code/config
2. **Service Account:** Minimal permissions (least privilege)
3. **Data Storage:** GCS with uniform bucket-level access
4. **Email Credentials:** Stored as app-specific passwords
5. **Logging:** Cloud Function logs contain sensitive data (monitored)

## Scalability

### Current Configuration
- **Max Instances:** 1 (sequential processing)
- **Memory:** 256MB (sufficient for ~30 images)
- **Timeout:** 60 seconds per run
- **Frequency:** Monthly (1st of month at 9 AM)

### if Scaling Needed
- Increase `max_instance_count` in Terraform
- Increase `timeout_seconds` for larger batches
- Implement queuing/batching mechanism
- Monitor Gemini API quota

## Technologies Used

### Google Cloud Services
- **Cloud Functions** - Serverless execution
- **Cloud Scheduler** - Monthly trigger
- **Cloud Storage** - Image archival
- **Secret Manager** - API key storage
- **Cloud Vision API** - Image categorization
- **Generative AI API** - Gemini LLM

### Google Workspace APIs
- **Drive API** - File retrieval
- **Sheets API** - Data aggregation

### Python Libraries
- `google-cloud-*` - GCP clients
- `google-generativeai` - Gemini API
- `google-auth` - Authentication
- `Pillow` + `pillow-heif` - Image processing
- `python-dateutil` - Date parsing

## Monitoring & Maintenance

### Daily/Weekly
- Check Cloud Function logs for errors
- Monitor email notifications
- Verify data in Google Sheets

### Monthly
- After automated run:
  - Review aggregated results
  - Verify all employees are included
  - Check financial totals accuracy
  - Archive completed sheet

### Quarterly
- Review Gemini prompt effectiveness
- Analyze API costs
- Update dependencies
- Performance tuning if needed

## Future Enhancements

Potential improvements:
1. **PDF Report Generation** - Auto-create downloadable PDFs
2. **Telegram Integration** - Direct image upload via Telegram
3. **Multiple Sheets** - Separate employee vs. financial sheets
4. **Validation Rules** - Sanity checks on extracted data
5. **Retry Logic** - Automatic re-analysis for failures
6. **Custom Alerts** - Anomaly detection (missing employees, etc.)
7. **Analytics Dashboard** - Monthly summary and trends
8. **Multi-language Support** - Support other languages/formats

## Troubleshooting

### Common Issues

**"GEMINI_API_KEY not found"**
- Check .env file exists and has the key
- Verify Secret Manager has the secret (production)

**"Invalid JSON from Gemini"**
- Review custom prompts for clarity
- Ensure prompt emphasizes "ONLY JSON"
- Check sample images to test

**"No images found"**
- Verify Google Drive folder ID is correct
- Check folder contains .jpg/.png/.heic files
- Ensure service account has Drive read permissions

**"Sheet update failed"**
- Verify SPREADSHEET_ID is correct
- Check sheet permissions for service account
- Ensure sheet exists and is accessible

## Documentation References

- [SETUP_CHECKLIST.md](../SETUP_CHECKLIST.md) - Step-by-step implementation
- [GEMINI_SETUP.md](../GEMINI_SETUP.md) - Gemini integration details
- [PROMPTS_TEMPLATES.md](../PROMPTS_TEMPLATES.md) - Custom prompt guide
- [README.md](../README.md) - Quick start guide

---

**Last Updated:** April 3, 2026  
**Version:** 2.0 (Gemini LLM Integration)  
**Status:** Production Ready
