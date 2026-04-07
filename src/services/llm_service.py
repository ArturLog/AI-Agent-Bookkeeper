import json
import google.generativeai as genai
from config import GEMINI_API_KEY
import base64
import datetime
from utils.parser import parse_polish_date


class LLMService:
    """
    Gemini LLM service for analyzing shift hours and shift reports.
    """
    
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-3-flash-preview')
    
    def analyze_shift_hours(self, content: bytes, prompt: str = None) -> dict:
        """
        Analyzes shift hours image using Gemini LLM with custom prompt.
        
        Args:
            content: Image bytes
            prompt: Custom prompt for shift hours analysis (optional, uses default if not provided)
        
        Returns:
            dict with structure:
            {
                'type': 'shift-hours',
                'name': 'Employee Name',
                'month': 'Month',
                'year': 'Year',
                'data': [
                    {'day': int, 'hours_raw': str, 'hours_decimal': float},
                    ...
                ]
            }
        """
        try:
            image_base64 = base64.standard_b64encode(content).decode('utf-8')
            
            prompt = self._get_default_shift_hours_prompt()
            
            response = self.model.generate_content([
                {
                    "mime_type": "image/jpeg",
                    "data": image_base64,
                },
                prompt
            ])
            
            response_text = response.text
            print(f"LLM Response for hours: {response_text[:200]}")
            
            result = self._parse_shift_hours_response(response_text)
            return result
            
        except Exception as e:
            print(f"Error analyzing shift hours with Gemini: {e}")
            return {
                'type': 'shift-hours',
                'name': 'UNKNOWN_EMPLOYEE',
                'month': 'Unknown',
                'year': 'Unknown',
                'data': []
            }
    
    def analyze_shift_report(self, content: bytes, prompt: str = None) -> dict:
        """
        Analyzes shift report image using Gemini LLM with custom prompt.
        
        Args:
            content: Image bytes
            prompt: Custom prompt for report analysis (optional, uses default if not provided)
        
        Returns:
            dict with structure:
            {
                'type': 'shift-report',
                'netto_8': float,
                'netto_23': float,
                'netto_sum': float,
                'tips': float,
                'date': datetime,
                'date_str': str
            }
        """
        try:
            image_base64 = base64.standard_b64encode(content).decode('utf-8')
            
            prompt = self._get_default_shift_report_prompt()
            
            response = self.model.generate_content([
                {
                    "mime_type": "image/jpeg",
                    "data": image_base64,
                },
                prompt
            ])
            
            response_text = response.text
            print(f"LLM Response for report: {response_text[:200]}")
            
            result = self._parse_shift_report_response(response_text)
            return result
            
        except Exception as e:
            print(f"Error analyzing shift report with Gemini: {e}")
            return {
                'type': 'shift-report',
                'netto_8': 0.0,
                'netto_23': 0.0,
                'netto_sum': 0.0,
                'tips': 0.0,
                'date': None,
                'date_str': 'Unknown'
            }
    
    def _get_default_shift_report_prompt(self) -> str:
        """
        Default prompt for shift report analysis.
        User should override this with their custom prompt.
        """
        return """You are extracting data from a Polish shift report / cash register shift summary.

    Your task:
    Read the image carefully and return ONLY valid JSON in exactly this structure:
    {
    "netto_8": number,
    "netto_23": number,
    "tips": number,
    "date": "YYYY-MM-DD HH:MM",
    "date_str": "human readable date"
    }

    Rules:
    1. The image may be rotated, skewed, partially cropped, low quality, or photographed at an angle. Mentally rotate and interpret it before extracting data.
    2. This is usually a Polish report. Common labels include:
    - "Stawka" = VAT rate
    - "Netto" = net amount
    - "Suma końcowa" = final sum
    - "sobota", "niedziela", etc. = weekday/date text
    3. Extract "netto_23" from the row where VAT rate is 23% and use the value from the "Netto" column.
    4. Extract "netto_8" from the row where VAT rate is 8% and use the value from the "Netto" column.
    5. Extract "tips" from the sales/category section, NOT from VAT summary.
    - Tips are the value from the row labeled "GG - USŁUGI".
    - OCR may show this as variants such as:
        "GG - USLUGI", "GG-USLUGI", "GG USŁUGI", "GG USLUGI"
    - If that row is present, use its amount as tips.
    6. The date is usually near the bottom of the report and may look like:
    "sobota, 28 marca 2026 01:44"
    Convert it to:
    - "date": "2026-03-28 01:44"
    - "date_str": the original human-readable date text as seen on the report
    7. Numbers use Polish formatting, e.g.:
    - "6 376,85 zł" -> 6376.85
    - "16 825,20 zł" -> 16825.20
    - "463,00 zł" -> 463.00
    8. Return numeric fields as JSON numbers, not strings.
    9. Ignore currency symbols and unrelated fields like VAT tax amounts, guest count, receipt count, or total sales unless needed to find the target values.
    10. If multiple similar values appear, prefer:
        - VAT rows for netto_8 and netto_23
        - "GG - USŁUGI" row for tips
        - bottom printed timestamp for date
    11. Return ONLY raw JSON. No markdown, no comments, no explanation.

    Example of expected output:
    {"netto_8": 6376.85, "netto_23": 16825.20, "tips": 463.0, "date": "2026-03-28 01:44", "date_str": "sobota, 28 marca 2026 01:44"}"""
        
def _get_default_shift_hours_prompt(self) -> str:
    """
    Default prompt for shift hours analysis.
    User should override this with their custom prompt.
    """
    return """You are extracting data from a handwritten Polish employee shift-hours sheet.

Your task:
Read the image carefully and return ONLY valid JSON in exactly this structure:
{
  "name": "Employee full name",
  "month": "Month name or number",
  "year": 2026,
  "data": [
    {"day": 1, "hours_raw": "raw hours text", "hours_decimal": 0.0}
  ]
}

Rules:
1. The image may be rotated, skewed, photographed at an angle, low quality, partially cropped, or handwritten. Mentally rotate and interpret it before extracting data.
2. This is usually a Polish monthly work-time sheet. Common labels include:
   - "Rok" = year
   - "Miesiąc" = month
   - "Imię i Nazwisko" = employee full name
   - "Rozpoczęcie pracy" = work start time
   - "Zakończenie pracy" = work end time
   - "Ilość godzin" = worked hours
   - "Razem" = total
3. Extract:
   - "name" from the "Imię i Nazwisko" field
   - "month" from the "Miesiąc" field
   - "year" from the "Rok" field as a number
4. For daily work data, read the row for each calendar day shown on the sheet.
5. Use ONLY the "Ilość godzin" column as the source for daily hours.
   - Do NOT calculate hours from start/end times unless "Ilość godzin" is missing and the value is still clearly inferable.
   - Prefer the written hours value exactly as recorded in the hours column.
6. For each day:
   - "day" = day number
   - "hours_raw" = raw text from the "Ilość godzin" cell for that day
   - "hours_decimal" = normalized decimal number of hours
7. Normalize Polish handwritten hour formats:
   - "8" -> 8.0
   - "8,5" -> 8.5
   - "8.5" -> 8.5
   - "8h 30m" or equivalent -> 8.5
8. Special interpretation rule for this kind of sheet:
   - In handwritten "Ilość godzin" cells, values that look like fractions with a slash are often actually hour-minute notation written with a slash instead of a separator.
   - Examples:
     - "11/25" means 11h 25m
     - "7/10" means 7h 10m
   - Convert such values to decimal hours:
     - 7h 27m -> 7.45
     - 11h 25m -> 11.42
     - 7h 10m -> 7.17
   - Keep "hours_raw" as seen on the page, but put the normalized decimal in "hours_decimal"
9. If a row has no work hours, a dash, is blank, or clearly indicates no shift:
   - include that day with:
     - "hours_raw": ""
     - "hours_decimal": 0.0
10. Include all days visible on the sheet, typically 1 through 31, in order.
11. Ignore notes from the "Notatka" column unless they help disambiguate whether a shift exists.
12. Ignore signatures, totals, handwritten comments outside the daily rows, and bottom summaries unless needed to interpret a specific day.
13. If a field is unclear, choose the most likely reading based on sheet structure and handwriting consistency across nearby rows.
14. Return ONLY raw JSON. No markdown, no comments, no explanation.

Example output:
{
  "name": "BOŻENA LAMBOJ",
  "month": "MARZEC",
  "year": 2026,
  "data": [
    {"day": 1, "hours_raw": "", "hours_decimal": 0.0},
    {"day": 2, "hours_raw": "3", "hours_decimal": 3.0},
    {"day": 3, "hours_raw": "11/27", "hours_decimal": 11.45}
  ]
}"""
    
    def _parse_shift_hours_response(self, response_text: str) -> dict:
        """
        Parses LLM response for shift hours.
        """
        try:
            json_str = self._extract_json(response_text)
            data = json.loads(json_str)
            
            return {
                'type': 'shift-hours',
                'name': data.get('name', 'UNKNOWN_EMPLOYEE'),
                'month': data.get('month', 'Unknown'),
                'year': data.get('year', 'Unknown'),
                'data': data.get('data', [])
            }
        except Exception as e:
            print(f"Error parsing shift hours response: {e}")
            return {
                'type': 'shift-hours',
                'name': 'UNKNOWN_EMPLOYEE',
                'month': 'Unknown',
                'year': 'Unknown',
                'data': []
            }
    
    def _parse_shift_report_response(self, response_text: str) -> dict:
        """
        Parses LLM response for shift report.
        """
        
        try:
            json_str = self._extract_json(response_text)
            data = json.loads(json_str)
            
            date_str = data.get('date_str', 'Unknown')
            report_date = None
            if date_str and date_str != 'Unknown':
                report_date = parse_polish_date(date_str)
            
            return {
                'type': 'shift-report',
                'netto_8': float(data.get('netto_8', 0.0)),
                'netto_23': float(data.get('netto_23', 0.0)),
                'netto_sum': round(float(data.get('netto_8', 0.0)) + float(data.get('netto_23', 0.0)), 2),
                'tips': float(data.get('tips', 0.0)),
                'date': report_date,
                'date_str': date_str
            }
        except Exception as e:
            print(f"Error parsing shift report response: {e}")
            return {
                'type': 'shift-report',
                'netto_8': 0.0,
                'netto_23': 0.0,
                'netto_sum': 0.0,
                'tips': 0.0,
                'date': None,
                'date_str': 'Unknown'
            }
    
    def _extract_json(self, text: str) -> str:
        """
        Extracts JSON from text, handling markdown code blocks.
        """
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end > start:
                return text[start:end].strip()
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            if end > start:
                return text[start:end].strip()
        
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                return text[start:end+1]
        except:
            pass
        
        return text
    
    def set_custom_prompts(self, shift_hours_prompt: str = None, shift_report_prompt: str = None):
        """
        Allows setting custom prompts for analysis.
        Can be called after initialization to override defaults.
        """
        if shift_hours_prompt:
            self._shift_hours_prompt = shift_hours_prompt
        if shift_report_prompt:
            self._shift_report_prompt = shift_report_prompt
    
    def _get_default_shift_hours_prompt(self) -> str:
        """Returns custom or default shift hours prompt."""
        if hasattr(self, '_shift_hours_prompt'):
            return self._shift_hours_prompt
        return self.__get_default_shift_hours_prompt_template()
    
    def _get_default_shift_report_prompt(self) -> str:
        """Returns custom or default shift report prompt."""
        if hasattr(self, '_shift_report_prompt'):
            return self._shift_report_prompt
        return self.__get_default_shift_report_prompt_template()
    
    def __get_default_shift_hours_prompt_template(self) -> str:
        """Default template for shift hours."""
        return """Analyze this shift hours sheet and extract the following information in JSON format only:
{
    "name": "Employee full name",
    "month": "Month name or number",
    "year": "Year as 4-digit number",
    "data": [
        {"day": 1, "hours_raw": "raw text", "hours_decimal": 8.5},
        {"day": 2, "hours_raw": "raw text", "hours_decimal": 8.0}
    ]
}
Return ONLY valid JSON."""
    
    def __get_default_shift_report_prompt_template(self) -> str:
        """Default template for shift report."""
        return """Analyze this shift report and extract financial data in JSON format:
{
    "netto_8": 1000.50,
    "netto_23": 500.25,
    "tips": 100.00,
    "date": "2026-04-03 21:30",
    "date_str": "3 kwietnia 2026 21:30"
}
Return ONLY valid JSON."""
