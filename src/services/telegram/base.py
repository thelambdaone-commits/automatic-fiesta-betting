import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
SCRIPTS_DIR = ROOT_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from check_setup import format_results, run_checks
from core.config import Config
from services.groq_advisor import GroqAdvisor
from services.wallet_ranker import THEME_ALL_DISPLAY_LIMIT, THEME_DETAIL_DISPLAY_LIMIT, THEME_RANK_LIMIT, WalletRanker

logger = logging.getLogger(__name__)
