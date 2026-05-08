import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def fetch_all_symbols():
    try:
        url = "https://www.sharesansar.com/today-price"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table')
        symbols = []
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) > 1:
                    sym = cols[1].text.strip()
                    if sym: symbols.append(sym)
        return sorted(list(set(symbols)))
    except:
        return ["NABIL", "NICA", "HDL"]

ALL_SYMBOLS = fetch_all_symbols()

def get_nepal_time():
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    now = datetime.now(nepal_tz)
    is_open = (now.weekday() == 6 or now.weekday() < 4) and (11 <= now.hour < 15)
    return now.strftime("%I:%M %p"), "🟢 OPEN" if is_open else "🔴 CLOSED"
