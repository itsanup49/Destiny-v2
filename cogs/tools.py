import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend — required for servers
import matplotlib.pyplot as plt
import io
from .utils import ALL_SYMBOLS, get_nepal_time

BASE_URL = "https://nepseapi.surajrimal.dev"

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def stock_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [
            app_commands.Choice(name=s, value=s)
            for s in ALL_SYMBOLS if current.upper() in s.upper()
        ]
        return choices[:25]

    # ── /ipo ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="ipo", description="Check active & upcoming IPOs / Right Shares")
    async def ipo(self, interaction: discord.Interaction):
        await interaction.response.defer()

        headers = {"User-Agent": "Mozilla/5.0 (compatible; DestinyBot/2.0)"}
        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            try:
                async with session.get("https://www.sharesansar.com/ipo") as resp:
                    if resp.status != 200:
                        await interaction.followup.send("❌ Could not reach ShareSansar. Try again later.")
                        return

                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    embed = discord.Embed(
                        title="📋 Active & Upcoming IPOs / Right Shares",
                        color=0x3498db,
                        timestamp=get_nepal_time()
                    )

                    table = soup.find("table")
                    found = 0

                    if table:
                        rows = table.find_all("tr")[1:]  # skip header
                        for row in rows[:8]:
                            cols = [td.get_text(strip=True) for td in row.find_all("td")]
                            if len(cols) >= 3 and cols[0]:
                                name      = cols[0]
                                open_date = cols[1] if len(cols) > 1 else "N/A"
                                close_date= cols[2] if len(cols) > 2 else "N/A"
                                units     = cols[3] if len(cols) > 3 else "N/A"
                                embed.add_field(
                                    name=name,
                                    value=f"Open: `{open_date}` | Close: `{close_date}` | Units: `{units}`",
                                    inline=False
                                )
                                found += 1

                    if found == 0:
                        embed.description = "✅ No active IPOs right now. Check back later!"

                    embed.set_footer(text="Source: ShareSansar")
                    await interaction.followup.send(embed=embed)

            except aiohttp.ClientConnectorError:
                await interaction.followup.send("❌ Connection failed. Check if the bot's host has internet access.")
            except Exception as e:
                await interaction.followup.send(f"❌ IPO fetch error: `{e}`")

    # ── /chart ────────────────────────────────────────────────────────────────
    @app_commands.command(name="chart", description="View today's price trend chart for a stock")
    @app_commands.autocomplete(symbol=stock_autocomplete)
    async def chart(self, interaction: discord.Interaction, symbol: str):
        await interaction.response.defer()
        sym = symbol.upper()

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # Pull today's floorsheet for intraday price trend
                async with session.get(f"{BASE_URL}/FloorsheetOf?symbol={sym}&page=1&size=200") as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"❌ No data found for **{sym}**. Market may be closed.")
                        return

                    raw = await resp.json()

                    # Handle both list and dict responses
                    trades = raw if isinstance(raw, list) else raw.get("floorsheets", [])

                    if not trades:
                        await interaction.followup.send(f"❌ No trades found for **{sym}** today.")
                        return

                    # Extract prices — try multiple possible key names
                    prices = []
                    for t in trades:
                        rate = (
                            t.get("rate") or
                            t.get("tradeRate") or
                            t.get("contractRate") or
                            t.get("Rate")
                        )
                        if rate:
                            try:
                                prices.append(float(str(rate).replace(",", "")))
                            except ValueError:
                                pass

                    if not prices:
                        await interaction.followup.send(f"❌ Could not read price data for **{sym}**.")
                        return

                    prices.reverse()  # oldest → newest
                    high = max(prices)
                    low  = min(prices)
                    ltp  = prices[-1]
                    open_price = prices[0]
                    is_up = ltp >= open_price

                    # ── Build the chart ──
                    fig, ax = plt.subplots(figsize=(10, 4))
                    fig.patch.set_facecolor("#0f0f23")
                    ax.set_facecolor("#1a1a2e")

                    line_color = "#2ecc71" if is_up else "#e74c3c"
                    fill_color = "#27ae60" if is_up else "#c0392b"

                    x = range(len(prices))
                    ax.plot(x, prices, color=line_color, linewidth=2.0, zorder=3)
                    ax.fill_between(x, prices, min(prices) - 1, alpha=0.25, color=fill_color)

                    # Horizontal reference lines
                    ax.axhline(y=open_price, color="#f39c12", linewidth=1, linestyle="--", alpha=0.6, label=f"Open: {open_price:.2f}")
                    ax.axhline(y=ltp, color=line_color, linewidth=1, linestyle=":", alpha=0.8, label=f"LTP: {ltp:.2f}")

                    ax.set_title(f"{sym}  |  Today's Price Trend", color="white", fontsize=13, pad=12, fontweight="bold")
                    ax.set_xlabel("Trade Sequence", color="#aaaaaa", fontsize=9)
                    ax.set_ylabel("Price (Rs.)", color="#aaaaaa", fontsize=9)
                    ax.tick_params(colors="#aaaaaa", labelsize=8)
                    for spine in ["top", "right"]:
                        ax.spines[spine].set_visible(False)
                    for spine in ["bottom", "left"]:
                        ax.spines[spine].set_color("#2a2a4a")
                    ax.grid(True, alpha=0.1, color="white")
                    ax.legend(facecolor="#1a1a2e", edgecolor="#2a2a4a", labelcolor="white", fontsize=8)

                    plt.tight_layout()

                    buf = io.BytesIO()
                    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
                    buf.seek(0)
                    plt.close(fig)

                    # ── Send ──
                    file  = discord.File(buf, filename=f"{sym}_chart.png")
                    trend = "🟢 UP" if is_up else "🔴 DOWN"
                    change_pct = ((ltp - open_price) / open_price * 100) if open_price else 0

                    embed = discord.Embed(
                        title=f"📈 {sym} — Intraday Chart",
                        color=0x2ecc71 if is_up else 0xe74c3c,
                        timestamp=get_nepal_time()
                    )
                    embed.set_image(url=f"attachment://{sym}_chart.png")
                    embed.add_field(name="LTP",   value=f"**Rs. {ltp:,.2f}**", inline=True)
                    embed.add_field(name="High",  value=f"Rs. {high:,.2f}",    inline=True)
                    embed.add_field(name="Low",   value=f"Rs. {low:,.2f}",     inline=True)
                    embed.add_field(name="Open",  value=f"Rs. {open_price:,.2f}", inline=True)
                    embed.add_field(name="Trend", value=trend,                 inline=True)
                    embed.add_field(name="Day %", value=f"{change_pct:+.2f}%", inline=True)
                    embed.set_footer(text=f"Based on {len(prices)} floor sheet trades today")

                    await interaction.followup.send(embed=embed, file=file)

            except aiohttp.ClientConnectorError:
                await interaction.followup.send("❌ Connection failed. Check bot's internet access.")
            except Exception as e:
                await interaction.followup.send(f"❌ Chart error: `{e}`")

async def setup(bot):
    await bot.add_cog(Tools(bot))
