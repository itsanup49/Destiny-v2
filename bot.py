import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import requests
from bs4 import BeautifulSoup
from thefuzz import process
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DestinyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        # Expanded list for search
        self.all_symbols = ["NABIL", "NICA", "ADBL", "HIDCL", "NIFRA", "HDL", "SHL", "AHPC", "UPPER", "NHPC", "GBIME", "NMB"]
        self.active_alerts = {} 

    def get_nepse_data(self, symbol):
        """Scrapes Sharesansar - reliable even when APIs are down."""
        try:
            # We use the 'company' page for deeper data if live is closed
            url = f"https://www.sharesansar.com/company/{symbol}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find LTP from the specific price display
            price_box = soup.find('span', {'class': 'p_ltp'})
            change_box = soup.find('span', {'class': 'p_price_change'})
            
            if price_box:
                return {
                    "ltp": price_box.text.strip().replace(',', ''),
                    "change": change_box.text.strip() if change_box else "0",
                    "status": "Success"
                }
            return None
        except:
            return None

    async def setup_hook(self):
        await self.tree.sync()
        self.alert_engine.start()

    async def fire_pings(self, user_id, channel_id, message, count):
        channel = self.get_channel(channel_id)
        if not channel: return
        for _ in range(count):
            await channel.send(f"🚨 <@{user_id}> {message}")
            await asyncio.sleep(3)

    @tasks.loop(seconds=20)
    async def alert_engine(self):
        if not self.active_alerts: return
        for user_id, config in list(self.active_alerts.items()):
            data = self.get_nepse_data(config['symbol'])
            if data:
                current_p = float(data['ltp'])
                if current_p <= config['low']:
                    msg = f"PRICE DROPPED! {config['symbol']} is at Rs. {current_p}"
                    del self.active_alerts[user_id]
                    await self.fire_pings(user_id, config['channel'], msg, 5)
                elif current_p >= config['high']:
                    msg = f"BREAKOUT! {config['symbol']} is at Rs. {current_p}"
                    del self.active_alerts[user_id]
                    await self.fire_pings(user_id, config['channel'], msg, 7)

bot = DestinyBot()

@bot.tree.command(name="price", description="Check LTP and Market Pressure")
async def price_cmd(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    sym = symbol.strip().upper()
    data = bot.get_nepse_data(sym)
    
    if data:
        ltp = data['ltp']
        change = data['change']
        color = 0x2ecc71 if "+" in change else 0xe74c3c if "-" in change else 0x34495e
        
        embed = discord.Embed(title=f"📊 {sym} Analysis", color=color)
        embed.add_field(name="Current Price", value=f"**Rs. {ltp}**", inline=True)
        embed.add_field(name="Change", value=f"{change}", inline=True)
        embed.set_footer(text="Data Source: Sharesansar Real-time")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Could not find **{sym}**. Ensure the symbol is correct.")

@bot.tree.command(name="set_alert", description="Burst pings: 5x for Low, 7x for High")
async def set_alert(interaction: discord.Interaction, symbol: str, low: float, high: float):
    sym = symbol.strip().upper()
    bot.active_alerts[interaction.user.id] = {"symbol": sym, "low": low, "high": high, "channel": interaction.channel_id}
    await interaction.response.send_message(f"🎯 Alert Armed for **{sym}**!")

@price_cmd.autocomplete('symbol')
async def stock_auto(interaction: discord.Interaction, current: str):
    matches = process.extract(current, bot.all_symbols, limit=10)
    return [app_commands.Choice(name=m[0], value=m[0]) for m in matches if m[1] > 30]

bot.run(TOKEN)

