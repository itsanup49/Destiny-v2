# 🚀 Destiny NEPSE V2
**Destiny NEPSE V2** is a high-performance, modular Discord bot designed to provide real-time intelligence for the Nepal Stock Exchange (NEPSE). Built with a professional Cog-based architecture, it offers live tracking, technical charting, and automated price alerts to give traders a competitive edge.
---
## ✨ Core Features
* **Live Market Analytics:** Real-time scraping of stock prices (LTP) and daily point changes.
* **Interactive UI:** Modern Discord interface using Buttons and Rich Embeds for a "pro" trading experience.
* **Automated Price Alerts:** Background engine that monitors stocks and DMs you when your target price is hit.
* **Technical Charting:** On-the-fly generation of price trend visualizations using Matplotlib.
* **Investment Tracking:** One-click checks for open IPOs, Right Shares, and Mutual Funds.
* **Broker Intelligence:** Real-time tracking of the top 3 buying brokers for any given day.
---
## 🛠️ Command Reference
### 📊 Market Commands

| Command | Description |
| :--- | :--- |
| `/stock <symbol>` | Get live LTP, price change, and market pressure for any symbol. Includes interactive buttons. |
| `/chart <symbol>` | Generates a visual trend analysis chart for the specified stock. |
| `/ipo` | Lists all currently active and upcoming IPOs and Right Shares. |
| `/broker` | Displays the top 3 buying brokers and their total transaction volume for the day. |

### 🚨 Alert Commands

| Command | Description |
| :--- | :--- |
| `/setalert <symbol> <price> <direction>` | Set a custom price alert. Direction can be `above` or `below`. The bot will DM you once the target is met. |

### ⚙️ System Commands

| Command | Description |
| :--- | :--- |
| `!sync` | (Admin Only) Forces the bot to refresh its slash command list with Discord's servers. |

---
## 📁 Project Structure
The bot uses a **Modular Cog Architecture**, ensuring it is scalable and easy to host on platforms like Railway or a VPS:
```text
destiny-bot/
├── main.py           # Entry point and Cog loader
├── requirements.txt  # Project dependencies
├── .env              # Sensitive credentials (TOKEN)
└── cogs/             # Feature modules (Must be lowercase)
    ├── market.py     # Live trading and UI buttons
    ├── tools.py      # Charts and IPO scrapers
    └── alerts.py     # Background price monitoring engine
