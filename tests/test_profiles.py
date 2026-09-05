import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from profiles import browser_profile_roots


class BrowserProfileRootTests(unittest.TestCase):
    def test_linux_returns_only_existing_browser_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "alice"
            (home / ".mozilla" / "firefox").mkdir(parents=True)
            (home / ".config" / "google-chrome").mkdir(parents=True)

            roots = browser_profile_roots("alice", home, "linux")

            self.assertEqual(["Firefox", "Chrome"], [root.browser for root in roots])

    def test_windows_paths_are_derived_from_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "Alice"
            chrome = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
            edge = home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data"
            chrome.mkdir(parents=True)
            edge.mkdir(parents=True)

            roots = browser_profile_roots("Alice", home, "win32")

            self.assertEqual(["Chrome", "Edge"], [root.browser for root in roots])
            self.assertEqual([chrome, edge], [root.path for root in roots])

    def test_macos_paths_are_absolute_under_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "alice"
            firefox = home / "Library" / "Application Support" / "Firefox" / "Profiles"
            firefox.mkdir(parents=True)

            roots = browser_profile_roots("alice", home, "darwin")

            self.assertEqual(1, len(roots))
            self.assertEqual(firefox, roots[0].path)


if __name__ == "__main__":
    unittest.main()
