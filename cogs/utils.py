import discord
from discord.ext import commands
from datetime import datetime
import pytz

# List of popular symbols for Autocomplete
SYMBOLS = ["NABIL", "NICA", "HDL", "NYADI", "AHPC", "SHL", "UPPER", "GBIME", "CIT", "HIDCL"]

def get_nepal_time():
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    now = datetime.now(nepal_tz)
    
    # Market hours: Sun-Thu, 11:00 to 15:00
    is_open = False
    if now.weekday() < 4: # 0=Mon, 4=Fri (Nepal is Sun-Thu)
        if 11 <= now.hour < 15:
            is_open = True
            
    return now.strftime("%I:%M %p"), "🟢 OPEN" if is_open else "🔴 CLOSED"

async def setup(bot):
    pass # Just a helper file
