from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

import al_kripto


class PackageTests(unittest.TestCase):
    def test_version_is_exposed(self) -> None:
        self.assertEqual(al_kripto.__version__, "0.1.0")

    def test_module_entrypoint_is_safe_by_default(self) -> None:
        environment = dict(os.environ)
        for key in tuple(environment):
            if key.startswith("AL_KRIPTO_"):
                environment.pop(key)

        completed = subprocess.run(
            [sys.executable, "-m", "al_kripto"],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        output = json.loads(completed.stdout)

        self.assertEqual(output["trading_mode"], "paper")
        self.assertFalse(output["live_enabled"])
        self.assertFalse(output["api_credentials_configured"])


if __name__ == "__main__":
    unittest.main()
