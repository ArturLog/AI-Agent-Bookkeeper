import re
import datetime
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
    def analyze_shift_hours(self, content: bytes) -> dict:
        """
        Extracts personal data and shift details from a Shift Hours image.
        """
        image = vision.Image(content=content)
        response = self._client.document_text_detection(image=image)
        
        words_with_pos = self._extract_words_with_pos(response)
        rows = self._group_words_into_rows(words_with_pos)

        def get_value_for_label(label, rows):
            for i, row in enumerate(rows[:10]):
                row_text = " ".join([w['text'] for w in row])
                if label.lower() in row_text.lower():
                    parts = row_text.lower().split(label.lower())
                    val = parts[-1].strip(": ").strip()
                    if val and len(val) > 2: return val.upper()

                    if i + 1 < len(rows):
                        next_row_text = " ".join([w['text'] for w in rows[i+1]])
                        if len(next_row_text) > 2: return next_row_text.upper()
            return "Unknown"

        name_raw = get_value_for_label("Imię i Nazwisko", rows)
        month = get_value_for_label("Miesiąc", rows)
        year = get_value_for_label("Rok", rows)

        name = name_raw
        if name != "Unknown":
            labels_to_strip = ["IMIĘ I NAZWISKO", "MIESIĄC", "ROK", "NORMA", "STANOWISKO", str(month).upper() if month else ""]
            for l in labels_to_strip:
                if l and l in name:
                    name = name.replace(l, "").strip()
            
            # Remove parentheses content like (LUTY 2026)
            name = re.sub(r'\(.*?\)', '', name).strip()
            
            name_parts = name.split()
            if len(name_parts) >= 2:
                real_name_parts = [p for p in name_parts if not any(c.isdigit() for c in p)]
                if len(real_name_parts) >= 2:
                    name = " ".join(real_name_parts[:2])
                elif real_name_parts:
                    name = real_name_parts[0]

        shift_data = self._parse_hours_rows(rows)

        return {
            'type': SHIFT_HOURS,
            'name': name if name and name != "Unknown" else "UNKNOWN_EMPLOYEE",
            'month': month,
            'year': year,
            'data': shift_data
        }

    def analyze_shift_report(self, content: bytes) -> dict:
        """
        Extracts Netto sum, tips (GG - USŁUGI), and date from a Shift Report image.
        """
        image = vision.Image(content=content)
        response = self._client.document_text_detection(image=image)
        full_text = response.full_text_annotation.text
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]

        words_with_pos = self._extract_words_with_pos(response)
        rows = self._group_words_into_rows(words_with_pos)

        netto_8 = 0.0
        netto_23 = 0.0
        tips = 0.0
        report_date = None

        def find_netto_matching_vat(vals, rate):
            potentials = []
            for i in range(len(vals)):
                for j in range(len(vals)):
                    if i == j: continue
                    v_netto = vals[i]
                    v_vat = vals[j]
                    if v_netto <= v_vat: continue
                    
                    # Netto * rate ~= VAT (5% tolerance)
                    expected_vat = v_netto * rate
                    if abs(v_vat - expected_vat) < (v_vat * 0.10 + 2): # 10% tolerance is safer for OCR
                        potentials.append(v_netto)
            return max(potentials) if potentials else 0.0

        for row in rows:
            row_text = " ".join([w['text'] for w in row])
            row_text_lower = row_text.lower()
            
            vals = find_all_prices(row_text)

            if re.search(r'8\s*%', row_text_lower):
                netto = find_netto_matching_vat(vals, 0.08)
                if netto > 0: netto_8 = netto
                elif vals: 
                    filtered = [v for v in vals if v != 8]
                    if filtered: netto_8 = max(filtered)
            
            elif re.search(r'23\s*%', row_text_lower):
                netto = find_netto_matching_vat(vals, 0.23)
                if netto > 0: netto_23 = netto
                elif vals:
                    filtered = [v for v in vals if v != 23]
                    if filtered: netto_23 = max(filtered)
            
            # 2. Tips (GG - USŁUGI)
            elif "gg" in row_text_lower and ("usługi" in row_text_lower or "uslugi" in row_text_lower):
                if vals:
                    filtered = [v for v in vals if v < 2000]
                    if filtered: tips = max(filtered)

        polish_months = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia']
        for line in reversed(lines):
            line_lower = line.lower()
            if any(m in line_lower for m in polish_months):
                report_date = parse_polish_date(line)
                if report_date:
                    # Logic: If report was done between 00:00 and 16:59, 
                    # it belongs to the previous business day.
                    if report_date.hour < 17:
                        report_date = report_date - datetime.timedelta(days=1)
                    break

        return {
            'type': SHIFT_REPORT,
            'netto_8': netto_8,
            'netto_23': netto_23,
            'netto_sum': round(netto_8 + netto_23, 2),
            'tips': tips,
            'date': report_date,
            'date_str': report_date.strftime("%Y-%m-%d %H:%M") if report_date else "Unknown"
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
                        width = max(v.x for v in vertices) - min(v.x for v in vertices)
                        words_with_pos.append({'text': text, 'x': center_x, 'y': center_y, 'w': width})
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

    def _parse_hours_rows(self, rows: list) -> list:
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
