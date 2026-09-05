"""Fail-closed application configuration."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

LIVE_ACKNOWLEDGEMENT = "I_UNDERSTAND_LIVE_TRADING_RISK"
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")
_SUPPORTED_EXCHANGES = frozenset({"binance"})


class ConfigurationError(ValueError):
    """Raised when configuration could permit unsafe or ambiguous behaviour."""


class Environment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class TradingMode(StrEnum):
    """Order execution modes, ordered by increasing external risk."""

    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings with secrets excluded from representations."""

    environment: Environment = Environment.DEVELOPMENT
    trading_mode: TradingMode = TradingMode.PAPER
    exchange: str = "binance"
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
    api_key: str | None = field(default=None, repr=False)
    api_secret: str | None = field(default=None, repr=False)
    enable_live: bool = False
    live_acknowledgement: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.exchange or not self.exchange.isascii():
            raise ConfigurationError("Exchange must be a non-empty ASCII identifier.")
        if self.exchange not in _SUPPORTED_EXCHANGES:
            supported = ", ".join(sorted(_SUPPORTED_EXCHANGES))
            raise ConfigurationError(
                f"Unsupported exchange: {self.exchange!r}. Supported exchanges: {supported}."
            )
        if not self.symbols:
            raise ConfigurationError("At least one symbol is required.")
        if len(set(self.symbols)) != len(self.symbols):
            raise ConfigurationError("Symbols must be unique.")
        invalid = [symbol for symbol in self.symbols if not _SYMBOL_PATTERN.fullmatch(symbol)]
        if invalid:
            raise ConfigurationError(f"Invalid symbols: {', '.join(invalid)}")

        has_key = bool(self.api_key)
        has_secret = bool(self.api_secret)
        if has_key != has_secret:
            raise ConfigurationError("API key and secret must be configured together.")
        if self.trading_mode is TradingMode.TESTNET and not (has_key and has_secret):
            raise ConfigurationError("Testnet mode requires testnet API credentials.")
        if self.trading_mode is TradingMode.LIVE:
            self._validate_live_mode(has_key=has_key, has_secret=has_secret)
        elif self.enable_live or self.live_acknowledgement:
            raise ConfigurationError("Live safeguards may only be set in live mode.")

    def _validate_live_mode(self, *, has_key: bool, has_secret: bool) -> None:
        if not self.enable_live:
            raise ConfigurationError("Live mode requires AL_KRIPTO_ENABLE_LIVE=true.")
        if self.live_acknowledgement != LIVE_ACKNOWLEDGEMENT:
            raise ConfigurationError("Live mode requires the exact risk acknowledgement.")
        if not (has_key and has_secret):
            raise ConfigurationError("Live mode requires restricted API credentials.")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build validated settings from a supplied mapping or process environment."""

        values = os.environ if environ is None else environ
        try:
            environment = Environment(values.get("AL_KRIPTO_ENV", "development").lower())
            trading_mode = TradingMode(values.get("AL_KRIPTO_TRADING_MODE", "paper").lower())
        except ValueError as error:
            raise ConfigurationError(f"Unsupported environment or trading mode: {error}") from error

        return cls(
            environment=environment,
            trading_mode=trading_mode,
            exchange=values.get("AL_KRIPTO_EXCHANGE", "binance").strip().lower(),
            symbols=_parse_symbols(values.get("AL_KRIPTO_SYMBOLS", "BTCUSDT,ETHUSDT")),
            api_key=_optional(values.get("AL_KRIPTO_API_KEY")),
            api_secret=_optional(values.get("AL_KRIPTO_API_SECRET")),
            enable_live=_parse_bool(values.get("AL_KRIPTO_ENABLE_LIVE", "false")),
            live_acknowledgement=_optional(values.get("AL_KRIPTO_LIVE_ACK")),
        )

    def redacted(self) -> dict[str, object]:
        """Return non-sensitive settings suitable for diagnostics and logs."""

        return {
            "environment": self.environment.value,
            "trading_mode": self.trading_mode.value,
            "exchange": self.exchange,
            "symbols": list(self.symbols),
            "api_credentials_configured": bool(self.api_key and self.api_secret),
            "live_enabled": self.enable_live,
        }


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_symbols(value: str) -> tuple[str, ...]:
    return tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean value: {value!r}")


def load_settings() -> Settings:
    """Load and validate settings from the process environment."""

    return Settings.from_env()
