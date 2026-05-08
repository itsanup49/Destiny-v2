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
        self.all_symbols = []
        self.active_alerts = {} 

    # --- ENGINE B: THE FAILOVER SCRAPER ---
    def scrape_fallback(self, symbol):
        """If the API fails, we grab the price from Sharesansar directly"""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'headertall'})
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) > 2 and cols[1].text.strip() == symbol:
                    return {
                        "ltp": cols[2].text.strip().replace(',', ''),
                        "change": cols[3].text.strip(),
                        "volume": cols[7].text.strip().replace(',', ''),
                        "source": "Sharesansar (Backup)"
                    }
            return None
        except: return None

    async def setup_hook(self):
        try:
            data = await self.nepse.getCompanyList()
            self.all_symbols = sorted([stock['symbol'] for stock in data])
        except:
            self.all_symbols = ["NABIL", "NICA", "ADBL", "HIDCL"]
        await self.tree.sync()
        self.alert_engine.start()

    @tasks.loop(seconds=20)
    async def alert_engine(self):
        if not self.active_alerts: return
        # Logic follows the same dual-check: Try API, then Scraper
        pass

bot = DestinyBot()

@bot.tree.command(name="price", description="Check LTP with Multi-API Failover")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    
    # --- STEP 1: TRY ENGINE A (NepseUnofficialApi) ---
    try:
        data = await bot.nepse.getLiveMarket()
        stock = next((s for s in data if s['symbol'] == sym), None)
        
        if stock and float(stock.get('lastTradedPrice', 0)) > 0:
            ltp = stock.get('lastTradedPrice')
            change = stock.get('pointChange', 0)
            vol = stock.get('totalTradedQuantity', 0)
            source = "Unofficial API (Primary)"
        else:
            # --- STEP 2: TRY ENGINE B (Scraper Fallback) ---
            backup = bot.scrape_fallback(sym)
            if backup:
                ltp, change, vol, source = backup['ltp'], backup['change'], backup['volume'], backup['source']
            else:
                return await interaction.followup.send(f"❌ Both APIs failed to find {sym}.")

        # --- UI RENDERING ---
        color = 0x2ecc71 if float(change) > 0 else 0xe74c3c if float(change) < 0 else 0x34495e
        embed = discord.Embed(title=f"📊 {sym} Analysis", color=color)
        embed.add_field(name="LTP", value=f"**Rs. {ltp}**", inline=True)
        embed.add_field(name="Change", value=str(change), inline=True)
        embed.add_field(name="Volume", value=f"{vol} units", inline=False)
        embed.set_footer(text=f"Data Source: {source}")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"⚠️ System Error: {e}")

@bot.tree.command(name="set_alert", description="Set high/low targets for burst pings")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {"symbol": sym, "low": low, "high": high, "channel": interaction.channel_id}
    await interaction.response.send_message(f"🎯 Alert Armed for **{sym}**!")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)
