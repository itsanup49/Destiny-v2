import discord
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# This function will fetch all 300+ symbols automatically
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
        return sorted(list(set(symbols))) # Removes duplicates and sorts A-Z
    except:
        return ["NABIL", "NICA", "HDL"] # Backup list if scraping fails

# Global list that gets filled on startup
ALL_SYMBOLS = fetch_all_symbols()

def get_nepal_time():
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    now = datetime.now(nepal_tz)
    # Market: Sun-Thu (0-3 in Python weekday is Mon-Thu, Sunday is 6)
    # Note: Sunday is 6, Mon-Thu is 0-3.
    is_open = False
    if now.weekday() == 6 or now.weekday() < 4: 
        if 11 <= now.hour < 15:
            is_open = True
            
    return now.strftime("%I:%M %p"), "🟢 OPEN" if is_open else "🔴 CLOSED"
