import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extensions import Scanner
from profiles import BrowserProfileRoot


class ScannerTests(unittest.TestCase):
    def _write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def _extension(
        self,
        root: Path,
        extension_id: str,
        version: str,
        *,
        enabled: bool = True,
        host_permissions: list[str] | None = None,
    ) -> None:
        manifest_path = root / "Default" / "Extensions" / extension_id / version / "manifest.json"
        self._write_json(
            manifest_path,
            {
                "manifest_version": 3,
                "name": f"Extension {extension_id}",
                "version": version,
                "permissions": ["storage"],
                "host_permissions": host_permissions or [],
                "optional_permissions": ["tabs"],
                "optional_host_permissions": ["https://optional.example/*"],
                "homepage_url": "https://example.test/",
            },
        )

        preferences_path = root / "Default" / "Preferences"
        if preferences_path.exists():
            preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
        else:
            preferences = {"extensions": {"settings": {}}}
        preferences["extensions"]["settings"][extension_id] = {
            "state": 1 if enabled else 0,
            "path": f"{extension_id}/{version}",
        }
        self._write_json(preferences_path, preferences)

    def test_reads_manifest_and_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "alice"
            chrome_root = home / ".config" / "google-chrome"
            self._write_json(
                chrome_root / "Local State",
                {"profile": {"info_cache": {"Default": {}}}},
            )
            self._extension(
                chrome_root,
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "1.2.3",
                enabled=False,
                host_permissions=["https://*/*"],
            )

            browser_root = BrowserProfileRoot("alice", "Chrome", chrome_root)
            with patch("extensions.discover_user_homes", return_value={"alice": home}), patch(
                "extensions.browser_profile_roots", return_value=[browser_root]
            ):
                extensions = Scanner().get_extension_info()

            self.assertEqual(1, len(extensions))
            extension = extensions[0]
            self.assertEqual("1.2.3", extension.version)
            self.assertFalse(extension.active)
            self.assertEqual(["https://*/*"], extension.user_permissions.origins)
            self.assertEqual(["tabs"], extension.optional_permissions.permission)
            self.assertEqual(
                ["https://optional.example/*"],
                extension.optional_permissions.origins,
            )
            self.assertEqual("https://example.test/", extension.homepage_url)

    def test_network_entries_are_attributed_by_extension_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "alice"
            chrome_root = home / ".config" / "google-chrome"
            self._write_json(
                chrome_root / "Local State",
                {"profile": {"info_cache": {"Default": {}}}},
            )

            extension_a = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            extension_b = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            self._extension(chrome_root, extension_a, "1.0")
            self._extension(chrome_root, extension_b, "2.0")

            def key(extension_id: str) -> str:
                value = f"chrome-extension://{extension_id}/"
                return base64.b64encode(value.encode()).decode()

            self._write_json(
                chrome_root / "Default" / "Network" / "Network Persistent State",
                {
                    "net": {
                        "http_server_properties": {
                            "servers": [
                                {
                                    "server": "https://a.example:443",
                                    "anonymization": [key(extension_a)],
                                },
                                {
                                    "server": "https://b.example:443",
                                    "anonymization": [key(extension_b)],
                                },
                            ]
                        }
                    }
                },
            )

            browser_root = BrowserProfileRoot("alice", "Chrome", chrome_root)
            with patch("extensions.discover_user_homes", return_value={"alice": home}), patch(
                "extensions.browser_profile_roots", return_value=[browser_root]
            ):
                extensions = Scanner().get_extension_info()

            by_id = {extension.extension_id: extension for extension in extensions}
            self.assertEqual(["a.example"], [c.domain_name for c in by_id[extension_a].connections])
            self.assertEqual(["b.example"], [c.domain_name for c in by_id[extension_b].connections])


if __name__ == "__main__":
    unittest.main()
