from __future__ import annotations

import unittest

from al_kripto.config import (
    LIVE_ACKNOWLEDGEMENT,
    ConfigurationError,
    Environment,
    Settings,
    TradingMode,
)


class SettingsTests(unittest.TestCase):
    def test_defaults_are_paper_only(self) -> None:
        settings = Settings.from_env({})

        self.assertEqual(settings.environment, Environment.DEVELOPMENT)
        self.assertEqual(settings.trading_mode, TradingMode.PAPER)
        self.assertFalse(settings.enable_live)
        self.assertEqual(settings.symbols, ("BTCUSDT", "ETHUSDT"))

    def test_symbols_are_normalized(self) -> None:
        settings = Settings.from_env({"AL_KRIPTO_SYMBOLS": " btcusdt, ethusdt "})

        self.assertEqual(settings.symbols, ("BTCUSDT", "ETHUSDT"))

    def test_invalid_and_duplicate_symbols_are_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"AL_KRIPTO_SYMBOLS": "BTC/USDT"})
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"AL_KRIPTO_SYMBOLS": "BTCUSDT,BTCUSDT"})

    def test_exchange_and_symbol_list_cannot_be_empty(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(exchange="")
        with self.assertRaises(ConfigurationError):
            Settings(symbols=())

    def test_partial_credentials_are_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"AL_KRIPTO_API_KEY": "key-only"})

    def test_testnet_requires_credentials(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"AL_KRIPTO_TRADING_MODE": "testnet"})

    def test_live_mode_requires_all_safeguards(self) -> None:
        base = {
            "AL_KRIPTO_TRADING_MODE": "live",
            "AL_KRIPTO_API_KEY": "key",
            "AL_KRIPTO_API_SECRET": "secret",
        }
        with self.assertRaises(ConfigurationError):
            Settings.from_env(base)
        with self.assertRaises(ConfigurationError):
            Settings.from_env({**base, "AL_KRIPTO_ENABLE_LIVE": "true"})

    def test_live_mode_accepts_explicit_acknowledgement(self) -> None:
        settings = Settings.from_env(
            {
                "AL_KRIPTO_TRADING_MODE": "live",
                "AL_KRIPTO_ENABLE_LIVE": "true",
                "AL_KRIPTO_LIVE_ACK": LIVE_ACKNOWLEDGEMENT,
                "AL_KRIPTO_API_KEY": "key",
                "AL_KRIPTO_API_SECRET": "secret",
            }
        )

        self.assertEqual(settings.trading_mode, TradingMode.LIVE)
        self.assertTrue(settings.enable_live)

    def test_live_mode_requires_credentials_after_safeguards(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(
                trading_mode=TradingMode.LIVE,
                enable_live=True,
                live_acknowledgement=LIVE_ACKNOWLEDGEMENT,
            )

    def test_live_flags_are_rejected_outside_live_mode(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"AL_KRIPTO_ENABLE_LIVE": "true"})

    def test_secrets_are_not_exposed(self) -> None:
        settings = Settings(api_key="top-secret-key", api_secret="top-secret-value")
        rendered = repr(settings) + str(settings.redacted())

        self.assertNotIn("top-secret-key", rendered)
        self.assertNotIn("top-secret-value", rendered)
        self.assertTrue(settings.redacted()["api_credentials_configured"])

    def test_invalid_boolean_is_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"AL_KRIPTO_ENABLE_LIVE": "sometimes"})

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings.from_env({"AL_KRIPTO_TRADING_MODE": "automatic"})


if __name__ == "__main__":
    unittest.main()
