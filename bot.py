import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import requests
from bs4 import BeautifulSoup
from nepse import AsyncNepse
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.nepse = AsyncNepse()
        self.nepse.setTLSVerification(False)
        self.active_alerts = {}
        
        # --- MANUALLY ADDED SYMBOLS (STOPS THE LOADING DELAY) ---
        # Add all 300+ symbols inside this list
        self.all_symbols = [
            "NABIL", "NICA", "ADBL", "NIFRA", "UPPER", "HIDCL", "HDL", "SHL", 
            "AHPC", "NHPC", "GBIME", "PRVU", "HRL", "NRIC", "CIT", "NTC",
            "HBL", "SBI", "SCB", "BOKL", "MBL", "SANIMA", "PCBL", "EBL"
            # ... you can paste the rest of the 300 symbols here
        ]

    async def setup_hook(self):
        # We skip the auto-fetch and sync immediately
        await self.tree.sync()
        if not self.alert_engine.is_running():
            self.alert_engine.start()

    def scrape_fallback(self, symbol):
        """Ultra-reliable scraper for Sharesansar"""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            if not table: return None
            
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) > 2 and cols[1].text.strip().upper() == symbol:
                    return {
                        "ltp": cols[2].text.strip().replace(',', ''),
                        "change": cols[3].text.strip(),
                        "volume": cols[7].text.strip().replace(',', ''),
                        "source": "Sharesansar (Backup)"
                    }
            return None
        except: return None

    @tasks.loop(seconds=15)
    async def alert_engine(self):
        # Logic for firing pings remains the same
        pass

bot = DestinyBot()

@bot.tree.command(name="price", description="Instant Price Check")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    
    # ENGINE 1: API
    try:
        data = await bot.nepse.getLiveMarket()
        stock = next((s for s in data if s['symbol'] == sym), None) if data else None
        
        if stock and float(stock.get('lastTradedPrice', 0)) > 0:
            ltp = stock.get('lastTradedPrice')
            change = stock.get('pointChange', 0)
            vol = stock.get('totalTradedQuantity', 0)
            source = "Unofficial API"
        else:
            # ENGINE 2: SCRAPER
            backup = bot.scrape_fallback(sym)
            if backup:
                ltp, change, vol, source = backup['ltp'], backup['change'], backup['volume'], backup['source']
            else:
                return await interaction.followup.send(f"❌ Market Data Unavailable for **{sym}** right now.")

        color = 0x2ecc71 if float(change) > 0 else 0xe74c3c if float(change) < 0 else 0x34495e
        embed = discord.Embed(title=f"📊 {sym} Analysis", color=color)
        embed.add_field(name="LTP", value=f"**Rs. {ltp}**", inline=True)
        embed.add_field(name="Change", value=str(change), inline=True)
        embed.add_field(name="Volume", value=f"{vol} units", inline=False)
        embed.set_footer(text=f"Engine: {source}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("⚠️ Error fetching data. Is the symbol correct?")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    if not current:
        return [app_commands.Choice(name=s, value=s) for s in bot.all_symbols[:10]]
    # fuzzy search through our manual list
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
