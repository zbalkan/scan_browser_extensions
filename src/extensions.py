import base64
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional, Union
from urllib.parse import urlparse

from profiles import BrowserProfileRoot, browser_profile_roots, discover_user_homes


class ExtensionEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class Permission:
    permission: Optional[list[str]] = None
    origins: Optional[list[str]] = None

    @staticmethod
    def parse(data: Optional[Any]) -> Optional["Permission"]:
        if data is None:
            return None
        if isinstance(data, dict):
            return Permission(data.get("permissions"), data.get("origins"))
        raise TypeError(f"Expected dict, got {type(data)}")


@dataclass
class Connection:
    domain_name: str
    active: bool


@dataclass
class ExtensionInfo:
    username: str
    browser: str
    browser_short: Literal["Firefox", "Chrome", "Edge"]
    profile: str
    extension_id: str
    risk: str
    name: str
    version: str
    extension_type: str
    description: str
    creator: str
    homepage_url: str
    active: bool
    install_date: datetime
    update_date: datetime
    path: str
    user_permissions: Optional[Permission] = None
    optional_permissions: Optional[Permission] = None
    connections: Optional[list[Connection]] = None

    def __str__(self) -> str:
        return json.dumps(self, cls=ExtensionEncoder, indent=4, sort_keys=True)


class Scanner:
    def __init__(self) -> None:
        self.platform = sys.platform

    def __calculate_risk(self, permissions: Optional[Permission]) -> str:
        sensitive_permissions = {
            "clipboardRead",
            "clipboardWrite",
            "cookies",
            "debugger",
            "history",
            "management",
            "nativeMessaging",
            "proxy",
            "scripting",
            "tabs",
            "webRequest",
            "webRequestBlocking",
        }
        broad_origins = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*", "://*/"}

        if permissions is None:
            return "🟢"
        if permissions.permission and sensitive_permissions.intersection(
            permissions.permission
        ):
            return "🚩"
        if permissions.origins and broad_origins.intersection(permissions.origins):
            return "🚩"
        return "🟢"

    def __get_firefox_installed_extensions(
        self, root: BrowserProfileRoot
    ) -> list[ExtensionInfo]:
        extension_info_list: list[ExtensionInfo] = []

        try:
            profiles = sorted(path for path in root.path.iterdir() if path.is_dir())
        except OSError as exc:
            logging.warning("Failed to enumerate Firefox profiles in %s: %s", root.path, exc)
            return extension_info_list

        for profile_path in profiles:
            ext_file = profile_path / "extensions.json"
            if not ext_file.is_file():
                continue

            try:
                with ext_file.open("r", encoding="utf-8") as json_file:
                    data: Any = json.load(json_file)
            except (OSError, json.JSONDecodeError) as exc:
                logging.warning("Failed to read %s: %s", ext_file, exc)
                continue

            for addon in data.get("addons", []):
                user_permissions = Permission.parse(addon.get("userPermissions"))
                extension_info_list.append(
                    ExtensionInfo(
                        username=root.username,
                        browser="Mozilla Firefox",
                        browser_short="Firefox",
                        profile=profile_path.name,
                        extension_id=addon.get("id", ""),
                        risk=self.__calculate_risk(user_permissions),
                        name=addon.get("defaultLocale", {}).get("name", ""),
                        version=addon.get("version", ""),
                        extension_type=addon.get("type", ""),
                        description=addon.get("defaultLocale", {}).get("description", ""),
                        creator=addon.get("defaultLocale", {}).get("creator", ""),
                        homepage_url=addon.get("defaultLocale", {}).get("homepageURL", ""),
                        active=addon.get("active", False),
                        install_date=datetime.fromtimestamp(
                            float(addon.get("installDate", 0)) / 1000
                        ),
                        update_date=datetime.fromtimestamp(
                            float(addon.get("updateDate", 0)) / 1000
                        ),
                        path=addon.get("path", ""),
                        user_permissions=user_permissions,
                        optional_permissions=Permission.parse(
                            addon.get("optionalPermissions")
                        ),
                    )
                )

        return extension_info_list

    def __parse_chrome_extension_description(
        self, extension_description: str, messages: dict[str, Any]
    ) -> str:
        desc_field = extension_description.removeprefix("__MSG_").removesuffix("__")
        ext_desc_obj: Union[dict[str, Any], str] = messages.get(
            desc_field.lower(), desc_field
        )

        if isinstance(ext_desc_obj, dict):
            return str(ext_desc_obj.get("message", ""))
        if isinstance(ext_desc_obj, str):
            temp = messages.get(ext_desc_obj)
            if temp:
                return str(temp.get("message", ""))
            return ext_desc_obj
        raise TypeError(f"Expected str or dict, got {type(ext_desc_obj)}")

    def __parse_chrome_extension_name(
        self, extension_name: str, messages: dict[str, Any]
    ) -> str:
        name_field = extension_name.removeprefix("__MSG_").removesuffix("__")
        ext_name_obj: dict[str, Any] | str = messages.get(
            name_field.lower(), name_field
        )

        if isinstance(ext_name_obj, dict):
            return str(ext_name_obj.get("message", ""))
        if isinstance(ext_name_obj, str):
            temp = messages.get(ext_name_obj)
            if temp:
                return str(temp.get("message", ""))
            return ext_name_obj
        raise TypeError(f"Expected str or dict, got {type(ext_name_obj)}")

    def __decode(self, encoded: str) -> Optional[str]:
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
        except Exception as exc:
            logging.debug("Failed to decode anonymization key: %s", exc)
            return None

        marker = "chrome-extension://"
        if marker not in decoded:
            return None
        return decoded.split(marker, 1)[1].split("/", 1)[0]

    def __load_chromium_settings(self, profile_path: Path) -> dict[str, Any]:
        settings: dict[str, Any] = {}

        for filename in ("Preferences", "Secure Preferences"):
            preferences_path = profile_path / filename
            if not preferences_path.is_file():
                continue
            try:
                with preferences_path.open("r", encoding="utf-8") as preferences_file:
                    preferences: Any = json.load(preferences_file)
            except (OSError, json.JSONDecodeError) as exc:
                logging.warning("Failed to read %s: %s", preferences_path, exc)
                continue

            file_settings = preferences.get("extensions", {}).get("settings", {})
            if isinstance(file_settings, dict):
                settings.update(file_settings)

        return settings

    def __chromium_profiles(self, user_data_root: Path) -> list[str]:
        profiles: set[str] = set()
        local_state_path = user_data_root / "Local State"

        try:
            with local_state_path.open("r", encoding="utf-8") as local_state_file:
                local_state: Any = json.load(local_state_file)
            info_cache = local_state.get("profile", {}).get("info_cache", {})
            if isinstance(info_cache, dict):
                profiles.update(str(profile) for profile in info_cache)
        except (OSError, json.JSONDecodeError, AttributeError):
            pass

        try:
            for path in user_data_root.iterdir():
                if not path.is_dir():
                    continue
                if (path / "Extensions").is_dir() or (path / "Preferences").is_file() or (path / "Secure Preferences").is_file():
                    profiles.add(path.name)
        except OSError as exc:
            logging.warning("Failed to enumerate Chromium profiles in %s: %s", user_data_root, exc)

        return sorted(profiles)

    def __manifest_path(
        self,
        extensions_path: Path,
        extension_folder: Path,
        setting: dict[str, Any],
    ) -> Optional[Path]:
        configured_path = setting.get("path")
        if configured_path:
            configured = Path(configured_path)
            if not configured.is_absolute():
                configured = extensions_path / configured
            manifest_path = configured / "manifest.json"
            if manifest_path.is_file():
                return manifest_path

        try:
            version_dirs = [path for path in extension_folder.iterdir() if path.is_dir()]
        except OSError:
            return None

        latest_path: Optional[Path] = None
        latest_mtime = -1.0
        for path in version_dirs:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_path = path

        if latest_path is None:
            return None
        manifest_path = latest_path / "manifest.json"
        return manifest_path if manifest_path.is_file() else None

    def __extension_type(self, manifest: dict[str, Any]) -> str:
        if "theme" in manifest:
            return "theme"
        if "app" in manifest:
            return "app"
        return "extension"

    def __localize_manifest(
        self, manifest: dict[str, Any], extension_path: Path
    ) -> tuple[str, str]:
        extension_name = manifest.get("name", "")
        extension_description = manifest.get("description", "")
        if "__MSG_" not in extension_name and "__MSG_" not in extension_description:
            return extension_name, extension_description

        locale = manifest.get("default_locale", "en")
        messages_file = extension_path / "_locales" / locale / "messages.json"
        if not messages_file.is_file():
            return extension_name, extension_description

        try:
            with messages_file.open("r", encoding="utf-8") as messages_json:
                messages: Any = json.load(messages_json)
        except (OSError, json.JSONDecodeError):
            return extension_name, extension_description

        return (
            self.__parse_chrome_extension_name(extension_name, messages),
            self.__parse_chrome_extension_description(extension_description, messages),
        )

    def __get_chromium_installed_extensions(
        self, root: BrowserProfileRoot
    ) -> list[ExtensionInfo]:
        extension_info_list: list[ExtensionInfo] = []
        browser = "Google Chrome" if root.browser == "Chrome" else "Microsoft Edge"

        for profile in self.__chromium_profiles(root.path):
            profile_path = root.path / profile
            extensions_path = profile_path / "Extensions"
            if not extensions_path.is_dir():
                continue

            settings = self.__load_chromium_settings(profile_path)
            try:
                extension_folders = sorted(
                    path
                    for path in extensions_path.iterdir()
                    if path.is_dir() and path.name != "Temp"
                )
            except OSError as exc:
                logging.warning("Failed to enumerate %s: %s", extensions_path, exc)
                continue

            for extension_folder in extension_folders:
                extension_id = extension_folder.name
                setting = settings.get(extension_id, {})
                manifest_path = self.__manifest_path(
                    extensions_path, extension_folder, setting
                )
                if manifest_path is None:
                    continue

                try:
                    with manifest_path.open("r", encoding="utf-8") as manifest_file:
                        manifest: Any = json.load(manifest_file)
                except (OSError, json.JSONDecodeError) as exc:
                    logging.warning("Failed to read %s: %s", manifest_path, exc)
                    continue

                extension_name, extension_description = self.__localize_manifest(
                    manifest, manifest_path.parent
                )
                permissions = Permission(
                    permission=manifest.get("permissions"),
                    origins=manifest.get("host_permissions"),
                )
                optional_permissions = Permission(
                    permission=manifest.get("optional_permissions"),
                    origins=manifest.get("optional_host_permissions"),
                )

                extension_info_list.append(
                    ExtensionInfo(
                        username=root.username,
                        browser=browser,
                        browser_short=root.browser,
                        profile=profile,
                        risk=self.__calculate_risk(permissions),
                        extension_id=extension_id,
                        name=extension_name,
                        version=manifest.get("version", ""),
                        extension_type=self.__extension_type(manifest),
                        description=extension_description,
                        creator=manifest.get("author", ""),
                        homepage_url=manifest.get("homepage_url", ""),
                        active=setting.get("state") == 1,
                        install_date=datetime.fromtimestamp(
                            os.path.getctime(extension_folder)
                        ),
                        update_date=datetime.fromtimestamp(
                            os.path.getmtime(extension_folder)
                        ),
                        path=str(extension_folder),
                        user_permissions=permissions,
                        optional_permissions=optional_permissions,
                        connections=self.__get_chromium_connections(
                            profile_path, extension_id
                        ),
                    )
                )

        return extension_info_list

    def __get_chromium_connections(
        self, profile_path: Path, extension_id: str
    ) -> list[Connection]:
        possible_paths = [
            profile_path / "Network" / "Network Persistent State",
            profile_path / "Network Persistent State",
        ]
        network_state_file = next((path for path in possible_paths if path.is_file()), None)
        if network_state_file is None:
            return []

        try:
            with network_state_file.open("r", encoding="utf-8") as nf:
                network_state: Any = json.load(nf)
        except (json.JSONDecodeError, OSError) as exc:
            logging.warning("Failed to read %s: %s", network_state_file, exc)
            return []

        properties = network_state.get("net", {}).get("http_server_properties", {})
        connections: list[Connection] = []

        for server in properties.get("servers", []):
            anonymization = server.get("anonymization", [None])
            if not anonymization or self.__decode(anonymization[0]) != extension_id:
                continue
            server_url = server.get("server")
            if server_url:
                parsed = urlparse(server_url)
                connections.append(
                    Connection(domain_name=parsed.hostname or server_url, active=True)
                )

        for broken in properties.get("broken_alternative_services", []):
            anonymization = broken.get("anonymization", [None])
            if not anonymization or self.__decode(anonymization[0]) != extension_id:
                continue
            host = broken.get("host")
            if host:
                connections.append(Connection(domain_name=host, active=False))

        return connections

    def get_extension_info(self) -> list[ExtensionInfo]:
        extension_info_list: list[ExtensionInfo] = []

        for username, home in discover_user_homes(self.platform).items():
            for root in browser_profile_roots(username, home, self.platform):
                if root.browser == "Firefox":
                    extension_info_list.extend(
                        self.__get_firefox_installed_extensions(root)
                    )
                else:
                    extension_info_list.extend(
                        self.__get_chromium_installed_extensions(root)
                    )

        return extension_info_list
