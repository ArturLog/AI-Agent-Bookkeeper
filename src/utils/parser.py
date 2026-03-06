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
            return int(nums[0]) + round_minutes(int(nums[1]))
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
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0
