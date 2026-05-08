import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def fetch_all_symbols():
    try:
        url = "https://www.sharesansar.com/today-price"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table')
        symbols = []
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) > 1:
                    sym = cols[1].text.strip()
                    if sym: symbols.append(sym)
        
        if len(symbols) > 10:
            return sorted(list(set(symbols)))
    except:
        pass
    
    # BACKUP LIST (If scraping fails, these will always show up)
    return [
        "NABIL", "NICA", "HDL", "NYADI", "AHPC", "SHL", "UPPER", "GBIME", "CIT", "HIDCL",
        "NTC", "NBL", "ADBL", "SANIMA", "PCBL", "PRVU", "HRL", "NRIC", "API", "AKPL",
        "UPW", "LEC", "MEN", "NIFRA", "MLBSL", "NICL", "NLIC", "SICL", "EBL", "MNHL"
    ]

ALL_SYMBOLS = fetch_all_symbols()

def get_nepal_time():
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    now = datetime.now(nepal_tz)
    # Nepal Market: Sunday (6) to Thursday (3)
    is_open = (now.weekday() == 6 or now.weekday() < 4) and (11 <= now.hour < 15)
    return now.strftime("%I:%M %p"), "🟢 OPEN" if is_open else "🔴 CLOSED"
