# Polymarket Wallet Mirror Bot

A Python-based trading bot that follows and replicates trades from specified wallets on Polymarket. The copy trading feature is exposed as **Wallet Mirror**. It also includes wallet scanning, historical bet summaries, and backtesting tools to identify and validate wallets before mirroring them.

## Requirements

- Python 3.8+
- Polygon Network wallet with USDC
- Polygon RPC endpoint

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/polymarket-copy-trade.git
cd polymarket-copy-trade
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up external environment variables:
```bash
cp .env.example .env
```
Edit `.env` with your Polygonscan and Telegram configuration.

4. Set up Polymarket session and target wallets:
```bash
python scripts/create_session.py
```
Then edit `config/targets/wallets.json` with the wallets you want to copytrade.

## Usage

### Main Functions

- Wallet Mirror from target wallet:
```bash
python src/main_copy_trade.py
```

- Backtest wallet trading history:
```bash
python src/main_backtest.py
```

- Search for smart wallets:
```bash
python src/main_search.py
```

- Telegram control panel:
```bash
python src/main_telegram.py
```

- Runtime setup checks:
```bash
python scripts/check_setup.py
python scripts/check_setup.py telegram rpc ws polygonscan groq
```

### Test Functions

The `src/test` directory contains individual test files for specific functionalities:

- `test_trade.py`: Test trade
- `test_monitor.py`: Test monitor

## Configuration

Configuration is split by responsibility:

- `.env`: external API keys and Telegram values only
- `config/session/default.json`: Polymarket credentials, private key, RPC/WebSocket URLs, and trading parameters
- `config/targets/wallets.json`: wallets used for copytrading and backtesting
- `data/output/`: generated CSV files
- `logs/`: runtime logs

Telegram buttons include config status, discovery, backtest launch, top-wallet PnL ranking, Groq AI analysis, and Wallet Mirror status. Use `/scan <wallet>` to read a wallet's public Polymarket history and summarize old bets. Use `/mirror <wallet>` to analyze a wallet and set it as the Wallet Mirror target. Groq is advisory only; Wallet Mirror execution still uses the configured trading limits.

Required optional `.env` values for Telegram/Groq:
```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

## Project Layout

- `config/`: runtime configuration files
- `data/`: generated or collected bot data
- `logs/`: runtime logs
- `scripts/`: operator scripts
- `src/services/`: business services such as monitoring, trading, and backtesting
- `src/tools/`: technical utilities such as approval and API key generation
- `src/utils/`: shared helpers

## API Calls and Performance

### API Calls per Bet

For each replicated trade, the bot performs approximately **3 to 4 external API calls**:

1.  **RPC Resolution (1 call)**: Resolves the full transaction details from the pending transaction hash (if not already provided by the WebSocket provider).
2.  **Balance Check (1 call)**: Hits the Polymarket/Polygon RPC to verify sufficient USDC balance before placing the order.
3.  **Order Posting (1 call)**: Sends the signed market order to the Polymarket CLOB API.
4.  **Telegram Notification (1 call)**: Sends a status update and trade details to your Telegram chat.

### Performance

-   **Detection Latency**: Uses WebSockets to monitor the Polygon mempool, allowing for near-instant detection of target trades (typically **<100ms**).
-   **Execution Speed**: Once a trade is detected and validated, the bot can place a corresponding order in **<500ms**, depending on network and API latency.
-   **Resource Usage**: The bot is optimized to run with minimal memory (**<500MB**) and can be managed via PM2 for high availability.

## Disclaimer

This bot is for educational purposes only. Use at your own risk. Trading cryptocurrency carries significant risks.

## TODO

- Effectively searching for smart wallet and build pools
- Periodically backtesting
