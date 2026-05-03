# Common constants
from enum import Enum


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Mode(str, Enum):
    SIMULATION = "simulation"
    LIVE = "live"
    TEST = "test"


class TimeUnit(str, Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"


# Default values
DEFAULT_SIMULATION_MODE = True
DEFAULT_LIVE_TRADING = False
DEFAULT_MAX_ORDER_SIZE = 1000.0
DEFAULT_SLIPPAGE_TOLERANCE = 0.01
DEFAULT_REQUEST_TIMEOUT = 20
DEFAULT_MONITOR_INTERVAL = 5  # seconds
DEFAULT_BACKOFF_INITIAL = 1  # second
DEFAULT_BACKOFF_MAX = 60  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0

# Paths
DATA_DIR = "data"
CONFIG_DIR = "config"
LOG_DIR = "logs"
