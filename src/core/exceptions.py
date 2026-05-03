class PolymarketError(Exception):
    """Base exception for Polymarket bot."""
    pass


class ConfigurationError(PolymarketError):
    """Configuration related errors."""
    pass


class APIError(PolymarketError):
    """API call failures."""
    pass


class TradingError(PolymarketError):
    """Trading execution errors."""
    pass


class ValidationError(PolymarketError):
    """Input validation errors."""
    pass


class AuthenticationError(PolymarketError):
    """Authentication failures."""
    pass
