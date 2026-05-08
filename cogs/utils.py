import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def fetch_all_symbols():
    """Scrapes all 300+ stock symbols from Sharesansar."""
    try:
        url = "https://www.sharesansar.com/today-price"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table')
        symbols = []
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) > 1:
                    sym = cols[1].text.strip()
                    if sym: symbols.append(sym)
        
        unique_symbols = sorted(list(set(symbols)))
        print(f"Successfully fetched {len(unique_symbols)} symbols.")
        return unique_symbols
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        # Fallback list if scraping fails
        return ["NABIL", "NICA", "HDL", "AHPC", "NYADI", "GBIME"]

# This runs once when the bot starts
ALL_SYMBOLS = fetch_all_symbols()

def get_nepal_time():
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    now = datetime.now(nepal_tz)
    # Market Open: Sun-Thu, 11 AM - 3 PM
    is_open = (now.weekday() == 6 or now.weekday() < 4) and (11 <= now.hour < 15)
    return now.strftime("%I:%M %p"), "🟢 OPEN" if is_open else "🔴 CLOSED"
