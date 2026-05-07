Destiny-v2: NEPSE Discord Bot Documentation
============================================

Overview:
---------
Destiny-v2 is a professional Discord bot designed for tracking the Nepal Stock Exchange (NEPSE).
It includes features like a modern Search UI, real-time alerts, and automated tracking.

List of All Commands:
---------------------
Type these in Discord starting with '/' to see the UI recommendations.

1. /price [symbol]
   - Description: Shows the Live Traded Price (LTP) and market details.
   - UI Feature: Autocomplete search (typing 'nbl' finds 'NABIL').

2. /set_alert [symbol] [max_price] [low_price]
   - Description: Pings you when a stock hits your High (Max) or Low target.
   - Persistence: Saved in 'data.json' so it survives bot restarts.

3. /track [symbol]
   - Description: Sends a price update in the channel every 30 seconds.
   - Note: Use this for stocks you want to monitor closely during trading hours.

4. /stop
   - Description: Clears all active alerts and 30-second tracking tasks.

How to Run Locally (Offline on your PC):
----------------------------------------
If you want to move the bot from Railway to your computer:

1. Install Python:
   Download Python 3.10+ from https://www.python.org/

2. Setup Folder:
   Copy your 'bot.py', 'requirements.txt', and 'data.json' to a folder.

3. Install Libraries:
   Open your Command Prompt (CMD) in that folder and run:
   pip install discord.py nepse-api thefuzz python-dotenv

4. Setup Token:
   Create a file named '.env' in the folder and add your token:
   DISCORD_TOKEN=your_actual_bot_token_here

5. Run:
   In CMD, type: python bot.py

Maintenance Tips:
-----------------
- The bot automatically fetches all 350+ NEPSE symbols on startup.
- Ensure your Railway 'Variables' tab has the DISCORD_TOKEN.
- If Slash Commands don't show up, kick and re-invite the bot with 'applications.commands' permission.

Created by: Anup Neupane & Gemini AI
Version: 2.0.0 (Hybrid Build)
