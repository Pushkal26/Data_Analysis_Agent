import re
from datetime import datetime, timedelta
import calendar

def parse_date_from_filename(filename: str):
    """
    Infers start and end dates from filenames like:
    - sales_nov_2024.csv
    - revenue_q1_2025.csv
    - data_2023.csv
    """
    filename = filename.lower()
    
    # Pattern for Quarter: q1_2025, q1-2025, 2025_q1
    quarter_match = re.search(r'q([1-4])[_\-](\d{4})', filename)
    if not quarter_match:
        # Try reversed 2025_q1
        quarter_match = re.search(r'(\d{4})[_\-]q([1-4])', filename)
        if quarter_match:
            year, quarter = int(quarter_match.group(1)), int(quarter_match.group(2))
        else:
            year, quarter = None, None
    else:
        quarter, year = int(quarter_match.group(1)), int(quarter_match.group(2))

    if year and quarter:
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        
        start_date = datetime(year, start_month, 1)
        last_day = calendar.monthrange(year, end_month)[1]
        end_date = datetime(year, end_month, last_day)
        return start_date, end_date, f"Q{quarter} {year}"

    # Pattern for Month: nov_2024, 2024_nov, november-2024
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    year_match = re.search(r'(\d{4})', filename)
    if year_match:
        year = int(year_match.group(1))
        # Find month
        found_month = None
        for m_str, m_int in months.items():
            if m_str in filename:
                found_month = m_int
                break
        
        if found_month:
            start_date = datetime(year, found_month, 1)
            last_day = calendar.monthrange(year, found_month)[1]
            end_date = datetime(year, found_month, last_day)
            return start_date, end_date, f"{calendar.month_name[found_month]} {year}"
            
        # If year found but no month/quarter, assume full year? 
        # Risky, better to return None or assume full year if explicit "year" or similar.
        # For now, if only year matches and it looks like a year file.
        if "year" in filename or re.search(r'^\d{4}\.csv', filename) or re.search(r'sales_\d{4}\.csv', filename):
             start_date = datetime(year, 1, 1)
             end_date = datetime(year, 12, 31)
             return start_date, end_date, f"FY {year}"

    return None, None, None

