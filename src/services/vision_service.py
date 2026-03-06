from google.cloud import vision
from config import SHIFT_HOURS, SHIFT_REPORT, UNCATEGORIZED
from utils.parser import parse_hours_value

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

    def analyze_shift_hours(self, content: bytes) -> dict:
        """
        Extracts personal data and shift details from a Shift Hours image.
        """
        image = vision.Image(content=content)
        response = self._client.document_text_detection(image=image)
        full_text = response.full_text_annotation.text
        lines = full_text.split('\n')

        def find_after(label: str, text_lines: list) -> str:
            """
            Finds value next to or below a specified label.
            """
            for i, line in enumerate(text_lines):
                if label.lower() in line.lower():
                    # Check for colon or existing split
                    parts = line.split(':') if ':' in line else line.lower().split(label.lower())
                    val = parts[-1].strip()
                    # If same line is empty, try next line
                    if not val and i + 1 < len(text_lines):
                        val = text_lines[i + 1].strip()
                    return val
            return "Unknown"

        name = find_after("Imię i Nazwisko", lines)
        month = find_after("Miesiąc", lines)
        year = find_after("Rok", lines)

        # Extract rows using geometrical data
        words_with_pos = self._extract_words_with_pos(response)
        rows = self._group_words_into_rows(words_with_pos)
        shift_data = self._parse_rows(rows)

        return {
            'name': name,
            'month': month,
            'year': year,
            'data': shift_data
        }

    def _extract_words_with_pos(self, response) -> list:
        """
        Collects words and their average coordinates.
        """
        words_with_pos = []
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        text = "".join([s.text for s in word.symbols])
                        vertices = word.bounding_box.vertices
                        center_y = sum(v.y for v in vertices) / 4
                        center_x = sum(v.x for v in vertices) / 4
                        words_with_pos.append({'text': text, 'x': center_x, 'y': center_y})
        return words_with_pos

    def _group_words_into_rows(self, words: list, threshold: int = 15) -> list:
        """
        Groups words sharing similar Y-coordinates into rows.
        """
        if not words:
            return []
        
        words.sort(key=lambda w: w['y'])
        rows = []
        current_row = [words[0]]

        for i in range(1, len(words)):
            if abs(words[i]['y'] - current_row[-1]['y']) < threshold:
                current_row.append(words[i])
            else:
                current_row.sort(key=lambda w: w['x'])
                rows.append(current_row)
                current_row = [words[i]]
        
        current_row.sort(key=lambda w: w['x'])
        rows.append(current_row)
        return rows

    def _parse_rows(self, rows: list) -> list:
        """
        Identifies and parses valid data rows in the shifts table.
        """
        data = []
        for row in rows:
            if not row: continue
            first_word = row[0]['text']
            # Valid row starts with a day number (1-31)
            if first_word.isdigit() and 1 <= int(first_word) <= 31:
                if len(row) >= 4:
                    day = int(first_word)
                    hours_raw = row[3]['text'] 
                    # Handle multi-word hour strings (e.g., "11 15")
                    if len(row) > 4 and abs(row[4]['x'] - row[3]['x']) < 50:
                        hours_raw += " " + row[4]['text']
                    
                    hours_decimal = parse_hours_value(hours_raw)
                    if hours_decimal > 0:
                        data.append({
                            'day': day,
                            'hours_raw': hours_raw,
                            'hours_decimal': hours_decimal
                        })
        data.sort(key=lambda x: x['day'], reverse=False)
        return data
