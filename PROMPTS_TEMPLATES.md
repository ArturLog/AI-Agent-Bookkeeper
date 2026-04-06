# LLM Prompts for Gemini Analysis

This document guides how to customize prompts for Gemini LLM analysis of shift hours and shift reports.

## Overview

The application now uses **Gemini LLM** (instead of Vision API) for detailed analysis of:
- **Shift Hours**: Employee time sheets with daily hours worked
- **Shift Reports**: Daily financial reports with sales and tips

The Vision API is still used for **categorization** (determining if an image is shift-hours or shift-report).

## How Prompts Work

1. The LLMService initializes with **default prompts**
2. You can override them with custom prompts by:
   - Modifying prompt templates programmatically
   - Or providing them via environment variables or configuration files

## Expected Output Format

Gemini must return **valid JSON** (required) for parsing.

### Shift Hours Response Format

```json
{
    "name": "John Doe",
    "month": "April",
    "year": 2026,
    "data": [
        {"day": 1, "hours_raw": "8h 30m", "hours_decimal": 8.5},
        {"day": 2, "hours_raw": "9 00", "hours_decimal": 9.0},
        {"day": 3, "hours_raw": "8.75", "hours_decimal": 8.75}
    ]
}
```

**Fields:**
- `name`: Employee full name (string)
- `month`: Month name or number (string/int)
- `year`: 4-digit year (int)
- `data`: Array of daily records
  - `day`: Day of month (1-31, int)
  - `hours_raw`: Original text from document (string)
  - `hours_decimal`: Converted to decimal hours (float, format: H.HH for 15-minute precision)

### Shift Report Response Format

```json
{
    "netto_8": 1450.75,
    "netto_23": 825.50,
    "tips": 125.00,
    "date": "2026-04-03 21:30",
    "date_str": "3 kwietnia 2026 21:30"
}
```

**Fields:**
- `netto_8`: Net amount at 8% VAT (float)
- `netto_23`: Net amount at 23% VAT (float)
- `tips`: Tips/gratuity amount (float)
- `date`: ISO format datetime YYYY-MM-DD HH:MM (string)
- `date_str`: Human-readable date string (string, typically in Polish)

## Example Custom Prompts

### Example 1: Shift Hours Prompt (Polish Context)

```
Analizujesz kartę czasu pracy pracownika. Ekstrahuj dane w formacie JSON:

{
    "name": "Pełne imię i nazwisko pracownika",
    "month": "Miesiąc (nazwa lub nr)",
    "year": "Rok (4 cyfry)",
    "data": [
        {"day": liczba_dnia, "hours_raw": "tekst_godzin", "hours_decimal": godziny_dziesiętne},
        ...
    ]
}

Zasady konwersji godzin:
- "8h 30m" → 8.5
- "9 00" (9 godzin 0 minut) → 9.0
- "8h45m" → 8.75
- Zaokrąglaj do 0.25 (15 minut)

Zwróć TYLKO JSON, bez wyjaśnień.
```

### Example 2: Shift Report Prompt (Polish Context)

```
Analizujesz raport dzienny z kas. Ekstrahuj finansowe dane w formacie JSON:

{
    "netto_8": kwota_netto_8%,
    "netto_23": kwota_netto_23%,
    "tips": napiwki,
    "date": "YYYY-MM-DD HH:MM",
    "date_str": "data_czytelnie_po_polsku"
}

Szukaj:
- Netto 8% - Usually for services/napiwki
- Netto 23% - Usually for products/food
- GG USŁUGI - Tips field
- Data oraz godzina z dokumentu

Zwróć TYLKO JSON, bez wyjaśnień.
```

## How to Implement Custom Prompts

### Option 1: Direct Code Modification (Not Recommended for Production)

Edit [src/services/llm_service.py](src/services/llm_service.py):

```python
def _get_default_shift_hours_prompt(self) -> str:
    return """Your custom prompt here..."""

def _get_default_shift_report_prompt(self) -> str:
    return """Your custom prompt here..."""
```

### Option 2: Environment Variables (Recommended)

1. Create a file: `src/prompts.py`
2. Add your prompts as constants
3. Load them in `llm_service.py`

```python
from config import SHIFT_HOURS_PROMPT, SHIFT_REPORT_PROMPT

# In LLMService.__init__():
self._shift_hours_prompt = SHIFT_HOURS_PROMPT
self._shift_report_prompt = SHIFT_REPORT_PROMPT
```

### Option 3: Dynamic Configuration (For Main Functions)

```python
from services import LLMService

llm = LLMService()
llm.set_custom_prompts(
    shift_hours_prompt="Your custom hours prompt...",
    shift_report_prompt="Your custom report prompt..."
)
```

## Testing Your Prompts

1. **Local Testing**: Modify [src/services/llm_service.py](src/services/llm_service.py) directly
2. **Test with sample image**: Create a `.env` file with `GEMINI_API_KEY` set
3. **Run locally**: `python src/main.py`
4. **Check output**: Verify JSON parsing works correctly

## Important Notes

1. **JSON Must Be Valid**: Gemini must return parseable JSON
2. **Field Names Matter**: Use exact field names shown above
3. **Data Types**: Ensure types match (e.g., `hours_decimal` as float, `day` as int)
4. **Polish Date Format**: For Polish reports, use format like "3 kwietnia 2026 21:30"
5. **Gemini Model**: Currently using `gemini-2.0-flash` - update in [src/services/llm_service.py](src/services/llm_service.py) if needed

## Troubleshooting

### "Invalid JSON" Error
- Gemini may be returning text outside JSON (markdown backticks, explanations)
- Solution: Adjust prompt to emphasize "ONLY JSON, NO EXPLANATIONS"
- The parser tries to extract JSON from markdown blocks automatically

### Wrong Data Type Extraction
- Double-check field names match expected structure
- Verify prompt examples in the prompt match expected format
- Test with `print(json.dumps(response))` to see raw output

### Missing Fields
- Ensure all required fields appear in JSON response structure
- Update prompt to explicitly list all fields needed
- Add validation in `_parse_shift_hours_response()` / `_parse_shift_report_response()`

## Next Steps

1. Provide your custom prompts to this file / share with the team
2. Test locally with your sample images
3. Deploy to GCP with `terraform apply` (set `gemini_api_key` variable)
4. Monitor cloud function logs in GCP console
