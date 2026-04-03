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
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
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
    
    def _get_default_shift_hours_prompt(self) -> str:
        """
        Default prompt for shift hours analysis.
        User should override this with their custom prompt.
        """
        return """Analyze this shift hours sheet and extract the following information in JSON format only, no explanations:
{
    "name": "Employee full name",
    "month": "Month name or number",
    "year": "Year as number",
    "data": [
        {"day": 1, "hours_raw": "raw hours text", "hours_decimal": 8.5},
        ...
    ]
}
Focus on extracting:
- Employee name
- Month and year
- Daily hours worked for each day (1-31)
Return ONLY valid JSON, no markdown or explanations."""
    
    def _get_default_shift_report_prompt(self) -> str:
        """
        Default prompt for shift report analysis.
        User should override this with their custom prompt.
        """
        return """Analyze this shift report and extract financial data in JSON format only, no explanations:
{
    "netto_8": amount with 8% VAT,
    "netto_23": amount with 23% VAT,
    "tips": tips/gratuity amount,
    "date": "YYYY-MM-DD HH:MM format",
    "date_str": "human readable date"
}
Return ONLY valid JSON, no markdown or explanations."""
    
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
