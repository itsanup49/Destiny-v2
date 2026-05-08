import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from .utils import ALL_SYMBOLS, get_nepal_time

BASE_URL = "https://nepseapi.surajrimal.dev"

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ]
        return choices[:25]

    @app_commands.command(name="stock", description="Get live NEPSE stock data")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def stock(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        sym = symbol.upper()

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{BASE_URL}/LiveMarket") as response:
                    if response.status != 200:
                        await interaction.followup.send(f"❌ API returned status {response.status}. Market may be closed.")
                        return

                    market_data = await response.json()

                    # Find the stock in the live market list
                    stock_info = None
                    for item in market_data:
                        if item.get("symbol", "").upper() == sym:
                            stock_info = item
                            break

                    if not stock_info:
                        await interaction.followup.send(f"❌ Symbol **{sym}** not found. Market may be closed or symbol is invalid.")
                        return

                    ltp = stock_info.get("ltp") or stock_info.get("lastTradedPrice") or "N/A"
                    change = stock_info.get("pointChange") or stock_info.get("change") or 0
                    percent = stock_info.get("percentageChange") or stock_info.get("percentChange") or 0
                    volume = stock_info.get("totalTradeQuantity") or stock_info.get("volume") or "N/A"
                    high = stock_info.get("highPrice") or "N/A"
                    low = stock_info.get("lowPrice") or "N/A"
                    prev_close = stock_info.get("previousClose") or "N/A"

                    try:
                        change_float = float(str(change).replace(",", ""))
                        color = 0x2ecc71 if change_float >= 0 else 0xe74c3c
                        arrow = "🟢" if change_float >= 0 else "🔴"
                    except:
                        color = 0x3498db
                        arrow = "⚪"

                    embed = discord.Embed(
                        title=f"{arrow} {sym} — Live Data",
                        color=color,
                        timestamp=get_nepal_time()
                    )
                    embed.add_field(name="LTP (Rs.)", value=f"**{ltp}**", inline=True)
                    embed.add_field(name="Change", value=f"`{change} ({percent}%)`", inline=True)
                    embed.add_field(name="Volume", value=f"{volume}", inline=True)
                    embed.add_field(name="High", value=f"{high}", inline=True)
                    embed.add_field(name="Low", value=f"{low}", inline=True)
                    embed.add_field(name="Prev. Close", value=f"{prev_close}", inline=True)
                    embed.set_footer(text="Source: NepseAPI • Nepal Stock Exchange")

                    await interaction.followup.send(embed=embed)

            except aiohttp.ClientConnectorError:
                await interaction.followup.send("❌ Could not connect to the data server. Check your internet/hosting.")
            except Exception as e:
                await interaction.followup.send(f"❌ Unexpected error: `{e}`")

    @app_commands.command(name="market", description="Get NEPSE market summary")
    async def market_summary(self, interaction: discord.Interaction):
        await interaction.response.defer()

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{BASE_URL}/Summary") as response:
                    if response.status != 200:
                        await interaction.followup.send("❌ Could not fetch market summary.")
                        return

                    data = await response.json()

                    embed = discord.Embed(title="📊 NEPSE Market Summary", color=0x2ecc71, timestamp=get_nepal_time())
                    for key, value in data.items():
                        embed.add_field(name=key, value=f"`{value}`", inline=True)
                    embed.set_footer(text="Source: NepseAPI")

                    await interaction.followup.send(embed=embed)

            except Exception as e:
                await interaction.followup.send(f"❌ Error: `{e}`")

    @app_commands.command(name="gainers", description="Top gaining stocks today")
    async def top_gainers(self, interaction: discord.Interaction):
        await interaction.response.defer()

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{BASE_URL}/TopGainers") as response:
                    if response.status != 200:
                        await interaction.followup.send("❌ Could not fetch gainers.")
                        return

                    data = await response.json()
                    top5 = data[:5] if len(data) >= 5 else data

                    embed = discord.Embed(title="🚀 Top Gainers Today", color=0x2ecc71, timestamp=get_nepal_time())
                    for stock in top5:
                        sym = stock.get("symbol", "N/A")
                        ltp = stock.get("ltp") or stock.get("lastTradedPrice", "N/A")
                        pct = stock.get("percentageChange") or stock.get("percentChange", "N/A")
                        embed.add_field(name=sym, value=f"LTP: **{ltp}** | `+{pct}%`", inline=False)
                    embed.set_footer(text="Source: NepseAPI")

                    await interaction.followup.send(embed=embed)

            except Exception as e:
                await interaction.followup.send(f"❌ Error: `{e}`")

    @app_commands.command(name="losers", description="Top losing stocks today")
    async def top_losers(self, interaction: discord.Interaction):
        await interaction.response.defer()

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{BASE_URL}/TopLosers") as response:
                    if response.status != 200:
                        await interaction.followup.send("❌ Could not fetch losers.")
                        return

                    data = await response.json()
                    top5 = data[:5] if len(data) >= 5 else data

                    embed = discord.Embed(title="📉 Top Losers Today", color=0xe74c3c, timestamp=get_nepal_time())
                    for stock in top5:
                        sym = stock.get("symbol", "N/A")
                        ltp = stock.get("ltp") or stock.get("lastTradedPrice", "N/A")
                        pct = stock.get("percentageChange") or stock.get("percentChange", "N/A")
                        embed.add_field(name=sym, value=f"LTP: **{ltp}** | `{pct}%`", inline=False)
                    embed.set_footer(text="Source: NepseAPI")

                    await interaction.followup.send(embed=embed)

            except Exception as e:
                await interaction.followup.send(f"❌ Error: `{e}`")

async def setup(bot):
    await bot.add_cog(Market(bot))
