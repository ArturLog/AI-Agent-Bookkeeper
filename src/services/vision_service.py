from google.cloud import vision
from config import SHIFT_HOURS, SHIFT_REPORT, UNCATEGORIZED
from utils.parser import parse_hours_value, parse_currency_value, parse_polish_date, find_all_prices

class VisionService:
    def __init__(self):
        self._client = vision.ImageAnnotatorClient()

    def categorize_image(self, content: bytes) -> str:
        """
        Categorizes the image based on detected text keywords.
        """
        image = vision.Image(content=content)
        response = self._client.document_text_detection(image=image)
        text = response.full_text_annotation.text.lower()
        
        hours_keywords = ["rok", "miesiac", "norma", "imie", "nazwisko", "stanowisko", 
                          "dzien", "m-ca", "rozpoczecie", "pracy", "zakonczenie", 
                          "ilosc", "godzin", "notatka", "podpis"]
        
        report_keywords = ["stawka", "vat", "netto", "suma", "koncowa", "gg", "bar", 
                           "uslugi", "przekaski", "dodatki", "nasza", "wodka", 
                           "woda", "23", "23%", "8", "8%", "rach"]

        if any(keyword in text for keyword in hours_keywords):
            return SHIFT_HOURS
        elif any(keyword in text for keyword in report_keywords):
            return SHIFT_REPORT
        
        print(f"DEBUG: Uncategorized text found: {text[:200]}...") 
        return UNCATEGORIZED