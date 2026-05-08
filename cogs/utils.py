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
        symbols = [row.find_all('td')[1].text.strip() for row in table.find_all('tr')[1:] if len(row.find_all('td')) > 1]
        return sorted(list(set(symbols)))
    except:
        return ["NABIL", "NICA", "HDL"]

ALL_SYMBOLS = fetch_all_symbols()

def get_nepal_time():
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    now = datetime.now(nepal_tz)
    is_open = (now.weekday() == 6 or now.weekday() < 4) and (11 <= now.hour < 15)
    return now.strftime("%I:%M %p"), "🟢 OPEN" if is_open else "🔴 CLOSED"
