from services.telegram.copy_modules import (
    TelegramCopyMirrorMixin,
    TelegramCopySmartMixin,
    TelegramCopySimulationMixin,
)


class TelegramCopyMixin(
    TelegramCopyMirrorMixin,
    TelegramCopySmartMixin,
    TelegramCopySimulationMixin,
):
    """Combined mixin for all copy trading functionality."""
    pass
