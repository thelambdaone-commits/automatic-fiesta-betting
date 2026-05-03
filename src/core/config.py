import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
SESSION_FILE = CONFIG_DIR / "session" / "default.json"
TARGETS_FILE = CONFIG_DIR / "targets" / "wallets.json"
BACKTEST_OUTPUT_DIR = DATA_DIR / "output" / "backtest"


def _load_json(path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _get(data, key, env_key=None, default=None):
    return data.get(key, os.getenv(env_key or key.upper(), default))


def _get_float(data, key, env_key=None, default=0.0):
    return float(_get(data, key, env_key, default))


def _get_int(data, key, env_key=None, default=0):
    return int(_get(data, key, env_key, default))


SESSION_CONFIG = _load_json(SESSION_FILE)
TARGETS_CONFIG = _load_json(TARGETS_FILE)


class Config:
    BASE_DIR = BASE_DIR
    CONFIG_DIR = CONFIG_DIR
    DATA_DIR = DATA_DIR
    LOG_DIR = LOG_DIR
    SESSION_FILE = SESSION_FILE
    TARGETS_FILE = TARGETS_FILE
    BACKTEST_OUTPUT_DIR = BACKTEST_OUTPUT_DIR

    # Polymarket API
    API_KEY = _get(SESSION_CONFIG, "polymarket_api_key", "POLYMARKET_API_KEY")
    SECRET = _get(SESSION_CONFIG, "polymarket_api_secret", "POLYMARKET_SECRET")
    PASSPHRASE = _get(SESSION_CONFIG, "polymarket_api_passphrase", "POLYMARKET_PASSPHRASE")
    HOST = _get(SESSION_CONFIG, "host", "POLYMARKET_HOST", "https://clob.polymarket.com")
    DATA_API_HOST = _get(SESSION_CONFIG, "data_api_host", "POLYMARKET_DATA_API_HOST", "https://data-api.polymarket.com")
    GAMMA_API_HOST = _get(SESSION_CONFIG, "gamma_api_host", "POLYMARKET_GAMMA_API_HOST", "https://gamma-api.polymarket.com")
    CHAIN_ID = _get_int(SESSION_CONFIG, "chain_id", "POLYMARKET_CHAIN_ID", 137)
    PRIVATE_KEY = _get(SESSION_CONFIG, "private_key", "POLYMARKET_PRIVATE_KEY")
    
    # Network
    RPC_URL = _get(SESSION_CONFIG, "rpc_url", "RPC_URL", "https://polygon-rpc.com")
    WS_URL = _get(SESSION_CONFIG, "alchemy_ws_url", "WS_URL", "wss://polygon-rpc.com")
    REQUEST_TIMEOUT = _get_float(SESSION_CONFIG, "request_timeout", "REQUEST_TIMEOUT", 10)
    
    # Polygonscan
    POLYGONSCAN_API_KEY = os.getenv("POLYGONSCAN_API_KEY")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Groq AI
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Trading parameters
    MIN_ORDER_SIZE = _get_float(SESSION_CONFIG, "min_order_size", "MIN_ORDER_SIZE", 10)
    MAX_ORDER_SIZE = _get_float(SESSION_CONFIG, "max_order_size", "MAX_ORDER_SIZE", 1000)
    SLIPPAGE_TOLERANCE = _get_float(SESSION_CONFIG, "slippage_tolerance", "SLIPPAGE_TOLERANCE", 0.02)
    MAX_RISK_PER_TRADE = _get_float(SESSION_CONFIG, "max_risk_per_trade", "MAX_RISK_PER_TRADE", 0.05)
    FOLLOW_DELAY = _get_float(SESSION_CONFIG, "follow_delay", "FOLLOW_DELAY", 1)
    
    # Test mode
    TEST_WALLET = _get(TARGETS_CONFIG, "test_wallet", "TEST_WALLET")
    TEST_MIN_ORDER = _get_float(SESSION_CONFIG, "test_min_order", "TEST_MIN_ORDER", 10)
    TEST_MAX_ORDER = _get_float(SESSION_CONFIG, "test_max_order", "TEST_MAX_ORDER", 1000)
    TEST_SLIPPAGE = _get_float(SESSION_CONFIG, "test_slippage", "TEST_SLIPPAGE", 0.01)
    TEST_DELAY = _get_float(SESSION_CONFIG, "test_delay", "TEST_DELAY", 1)
    
    # Production mode
    TARGET_WALLETS = TARGETS_CONFIG.get("wallet_mirror_wallets") or TARGETS_CONFIG.get("copytrade_wallets", [])
    TARGET_WALLET = TARGET_WALLETS[0] if TARGET_WALLETS else os.getenv("TARGET_WALLET")
    PROD_MIN_ORDER = _get_float(SESSION_CONFIG, "prod_min_order", "PROD_MIN_ORDER", 100)
    PROD_MAX_ORDER = _get_float(SESSION_CONFIG, "prod_max_order", "PROD_MAX_ORDER", 10000)
    PROD_SLIPPAGE = _get_float(SESSION_CONFIG, "prod_slippage", "PROD_SLIPPAGE", 0.005)
    PROD_DELAY = _get_float(SESSION_CONFIG, "prod_delay", "PROD_DELAY", 2)

    # Execution mode
    SIMULATION_MODE = str(os.getenv("SIMULATION_MODE", os.getenv("DRY_RUN", "false"))).lower() in {"1", "true", "yes", "on"}
    LIVE_TRADING = str(os.getenv("LIVE_TRADING", "true")).lower() in {"1", "true", "yes", "on"}
    CONFIRM_LIVE_TRADING = str(os.getenv("CONFIRM_LIVE_TRADING", "false")).lower() in {"1", "true", "yes", "on"}
    
    # Search
    SEARCH_HOURS = _get_int(SESSION_CONFIG, "search_hours", "SEARCH_HOURS", 5)
    
    # Proxy
    HTTP_PROXY = os.getenv("HTTP_PROXY")
    HTTPS_PROXY = os.getenv("HTTPS_PROXY")
    
    # Polymarket contracts
    POLYMARKET_CONTRACTS = {
        "CTF_EXCHANGE": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E".lower(),
        "NEG_RISK_CTF_EXCHANGE": "0xC5d563A36AE78145C45a50134d48A1215220f80a".lower(),
        "NEG_RISK_ADAPTER": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296".lower(),
        "FEE_MODULE": "0x56C79347e95530c01A2FC76E732f9566dA16E113".lower(),
        "NEG_RISK_FEE_MODULE": "0x78769D50Be1763ed1CA0D5E878D93f05aabff29e".lower(),
        "RELAY_HUB": "0xD216153c06E857cD7f72665E0aF1d7D82172F494".lower(),
        "CONDITIONAL_TOKENS": "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045".lower()
    }
    
    # Event signatures
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef".lower()
    TRANSFER_SINGLE_TOPIC = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62".lower()
    MATCH_ORDERS_SIGNATURE = _get(SESSION_CONFIG, "match_orders_signature", "MATCH_ORDERS_SIGNATURE", "d2539b37")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = [cls.PRIVATE_KEY, cls.API_KEY, cls.SECRET, cls.PASSPHRASE]
        if not all(required):
            raise ValueError("Missing required environment variables")
        return True

    @classmethod
    def from_session(cls, session_data):
        """Load configuration from encrypted session"""
        from session_manager import SessionData
        if not isinstance(session_data, SessionData):
            raise ValueError("session_data must be a SessionData instance")
        cls.API_KEY = session_data.polymarket_api_key
        cls.SECRET = session_data.polymarket_api_secret
        cls.PASSPHRASE = session_data.polymarket_api_passphrase
        cls.PRIVATE_KEY = session_data.private_key
        cls.HOST = session_data.host
        cls.CHAIN_ID = session_data.chain_id
        cls.WS_URL = session_data.alchemy_ws_url
        cls.RPC_URL = session_data.rpc_url
        cls.MIN_ORDER_SIZE = session_data.min_order_size
        cls.MAX_ORDER_SIZE = session_data.max_order_size
        cls.SLIPPAGE_TOLERANCE = session_data.slippage_tolerance
        cls.FOLLOW_DELAY = session_data.follow_delay
        cls.MATCH_ORDERS_SIGNATURE = session_data.match_orders_signature
        if session_data.tracked_wallets:
            cls.TARGET_WALLET = session_data.tracked_wallets[0] if session_data.tracked_wallets else None
        return True
    
    @staticmethod
    def _base_dir():
        """Get base directory for imports"""
        import os
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Proxy dict for requests
def get_proxies():
    proxies = {
        'http': Config.HTTP_PROXY,
        'https': Config.HTTPS_PROXY
    }
    return {key: value for key, value in proxies.items() if value}
