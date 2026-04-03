import re
import datetime

def round_minutes(mins: int) -> float:
    """
    Rounding to closest 15m steps: .00, .25, .50, .75
    0-7 -> 0
    8-22 -> 0.25
    23-37 -> 0.50
    38-52 -> 0.75
    53-59 -> 1.00
    """
    return round((mins / 60) * 4) / 4.0

def parse_hours_value(text: str) -> float:
    """
    Parses various handwritten formats into a decimal hour value.
    Example inputs: '11 30', '11 19', '3h', '11.5', '1130'
    """
    if not text or text in ["-", "—", ""]:
        return 0.0
        
    cleaned = text.strip().lower().replace(',', '.')
    
    # Case: Decimal already (e.g. 11.5)
    if '.' in cleaned:
        try:
            return float(cleaned)
        except ValueError:
            pass
        
    # Case: "11h 30m" or just "3h"
    if 'h' in cleaned:
        nums = "".join([c if c.isdigit() or c == ' ' else ' ' for c in cleaned]).split()
        if len(nums) >= 2:
            try:
                return int(nums[0]) + round_minutes(int(nums[1]))
            except ValueError:
                pass
        elif len(nums) == 1:
            try:
                return float(nums[0])
            except ValueError:
                return 0.0
            
    # Case: "11 30" (space separated)
    parts = cleaned.split()
    if len(parts) >= 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            return h + round_minutes(m)
        except ValueError:
            pass
        
    # Case: "1130" (tightly packed)
    digits = "".join(filter(str.isdigit, cleaned))
    if len(digits) >= 3:
        try:
            # Assume last 2 are minutes if total length >= 3
            h = int(digits[:-2])
            m = int(digits[-2:])
            if m < 60:
                return h + round_minutes(m)
        except ValueError:
            pass
            
    # Fallback to pure digit parsing if possible
    try:
        val = float(digits) if digits else 0.0
        # Sanity check: cap at 24 hours per day
        if val > 24:
            # Maybe it's HHMM format but MM >= 60? 
            # If 11271 -> likely junk. If 1150 -> 11.75
            if val > 2400: return 0.0
            h = int(val // 100)
            m = int(val % 100)
            if h <= 24 and m < 60:
                return h + round_minutes(m)
            return 0.0 # Junk
        return val
    except ValueError:
        return 0.0

def parse_currency_value(text: str) -> float:
    """
    Parses currency strings like '8 754,47 zł' or '6 365,04' into 8754.47.
    """
    if not text:
        return 0.0
    
    # Cleaning: comma to dot, remove everything but digits and dots
    cleaned = text.replace(',', '.')
    cleaned = re.sub(r'[^\d.]', '', cleaned)
    
    if not cleaned: return 0.0
    
    # If multiple dots, only the last one is the decimal separator
    if cleaned.count('.') > 1:
        parts = cleaned.split('.')
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
        
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def find_all_prices(text: str) -> list:
    """
    Finds all potential prices in a string, merging thousands separators correctly.
    Example: '23 % 1003,96 4 365,04 zł' -> [23.0, 1003.96, 4365.04]
    """
    if not text: return []
    
    # Improved regex:
    # 1. Matches digits with optional thousand separators (exactly 3 digits after space/dot)
    # 2. Matches optional decimal part (dot/comma + digits)
    # Pattern: Digit(s) then optionally groups of (space/dot + 3 digits), then optionally (dot/comma + 2-3 digits)
    pattern = r'\d{1,3}(?:[\s.]+\d{3})+(?:[.,]\d{1,3})?|\d+(?:[.,]\d{1,3})?'
    
    matches = re.findall(pattern, text)
    
    vals = []
    for m in matches:
        # Filter out tiny things like just '8' if they look like standalone tax rates 
        # but keep them if they are part of a larger context.
        # Actually, let's just parse and let the math check handle it.
        val = parse_currency_value(m)
        if val > 0:
            vals.append(val)
    return vals

def parse_polish_date(text: str) -> datetime.datetime:
    """
    Parses Polish date strings like 'poniedziałek, 16 lutego 2026 00:15'.
    """
    if not text:
        return None
    
    # Mapping Polish month (genitive and nominative) to numbers
    months = {
        'styczeń': 1, 'stycznia': 1,
        'luty': 2, 'lutego': 2,
        'marzec': 3, 'marca': 3,
        'kwiecień': 4, 'kwietnia': 4,
        'maj': 5, 'maja': 5,
        'czerwiec': 6, 'czerwca': 6,
        'lipiec': 7, 'lipca': 7,
        'sierpień': 8, 'sierpnia': 8,
        'wrzesień': 9, 'września': 9,
        'październik': 10, 'października': 10,
        'listopad': 11, 'listopada': 11,
        'grudzień': 12, 'grudnia': 12
    }
    
    cleaned = text.lower().replace(',', ' ').strip()
    # Remove day names
    days = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela', 'poniedzialek', 'sroda', 'piatek']
    for day in days:
        cleaned = cleaned.replace(day, '')
    
    parts = cleaned.split()
    if len(parts) >= 4:
        try:
            day = int(parts[0])
            month_str = parts[1]
            year = int(parts[2])
            time_str = parts[3]
            hour, minute = map(int, time_str.split(':'))
            
            month = months.get(month_str, 1) # Default to Jan if unknown
            return datetime.datetime(year, month, day, hour, minute)
        except (ValueError, IndexError):
            pass
            
    return None
