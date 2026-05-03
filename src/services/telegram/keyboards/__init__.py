# Keyboards module
from .main import MainKeyboardMixin
from .copy_betting import CopyBettingKeyboardMixin
from .wallets import WalletsKeyboardMixin
from .discover import DiscoverKeyboardMixin
from .settings import SettingsKeyboardMixin

__all__ = [
    'MainKeyboardMixin',
    'CopyBettingKeyboardMixin',
    'WalletsKeyboardMixin',
    'DiscoverKeyboardMixin',
    'SettingsKeyboardMixin',
]
