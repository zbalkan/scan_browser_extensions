import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Browser = Literal["Firefox", "Chrome", "Edge"]


@dataclass(frozen=True)
class BrowserProfileRoot:
    username: str
    browser: Browser
    path: Path


def _user_roots(platform: str) -> Path:
    if platform == "win32":
        return Path(os.environ.get("SystemDrive", "C:")) / "Users"
    if platform == "darwin":
        return Path("/Users")
    return Path("/home")


def discover_user_homes(platform: str | None = None) -> dict[str, Path]:
    """Return local user homes that can contain browser profile artifacts."""
    platform = platform or sys.platform
    root = _user_roots(platform)
    if not root.is_dir():
        return {}

    homes = {
        path.name: path
        for path in root.iterdir()
        if path.is_dir() and not path.is_symlink()
    }

    # Linux commonly has a useful non-/home account (for example root). Add the
    # current home only when it exists and was not already discovered.
    current_home = Path.home()
    if current_home.is_dir():
        homes.setdefault(current_home.name, current_home)

    return homes


def browser_profile_roots(
    username: str, home: Path, platform: str | None = None
) -> list[BrowserProfileRoot]:
    """Return known browser data roots without requiring browser executables."""
    platform = platform or sys.platform

    if platform == "win32":
        roots = [
            ("Firefox", home / "AppData/Roaming/Mozilla/Firefox/Profiles"),
            ("Chrome", home / "AppData/Local/Google/Chrome/User Data"),
            ("Edge", home / "AppData/Local/Microsoft/Edge/User Data"),
        ]
    elif platform == "darwin":
        app_support = home / "Library/Application Support"
        roots = [
            ("Firefox", app_support / "Firefox/Profiles"),
            ("Chrome", app_support / "Google/Chrome"),
            ("Edge", app_support / "Microsoft Edge"),
        ]
    else:
        roots = [
            ("Firefox", home / ".mozilla/firefox"),
            ("Chrome", home / ".config/google-chrome"),
            ("Edge", home / ".config/microsoft-edge"),
        ]

    return [
        BrowserProfileRoot(username, browser, path)
        for browser, path in roots
        if path.is_dir()
    ]
