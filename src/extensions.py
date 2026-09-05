import base64
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional, Union

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
        risky_permissions = {"clipboardWrite", "<all_urls>", "tabs", "cookies", "://*/"}
        if permissions and permissions.permission:
            if any(permission in risky_permissions for permission in permissions.permission):
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
                extension_info_list.append(
                    ExtensionInfo(
                        username=root.username,
                        browser="Mozilla Firefox",
                        browser_short="Firefox",
                        profile=profile_path.name,
                        extension_id=addon.get("id", ""),
                        risk=self.__calculate_risk(
                            Permission.parse(addon.get("permissions"))
                        ),
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
                        user_permissions=Permission.parse(addon.get("userPermissions")),
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
            if "chrome-extension://" in decoded:
                return decoded.split("chrome-extension://")[-1]
            return None
        except Exception as exc:
            logging.debug("Failed to decode anonymization key: %s", exc)
            return None

    def __get_chromium_installed_extensions(
        self, root: BrowserProfileRoot
    ) -> list[ExtensionInfo]:
        extension_info_list: list[ExtensionInfo] = []
        browser = "Google Chrome" if root.browser == "Chrome" else "Microsoft Edge"

        local_state_path = root.path / "Local State"
        try:
            with local_state_path.open("r", encoding="utf-8") as local_state_file:
                local_state: Any = json.load(local_state_file)
            chrome_profiles = local_state.get("profile", {}).get("info_cache", {}).keys()
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            logging.warning("Failed to read %s: %s", local_state_path, exc)
            return extension_info_list

        for profile in chrome_profiles:
            extensions_path = root.path / profile / "Extensions"
            if not extensions_path.is_dir():
                continue

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
                try:
                    version_dirs = [path for path in extension_folder.iterdir() if path.is_dir()]
                    if not version_dirs:
                        continue
                    extension_version_path = version_dirs[0]
                    manifest_path = extension_version_path / "manifest.json"
                    with manifest_path.open("r", encoding="utf-8") as manifest_file:
                        manifest: Any = json.load(manifest_file)
                except (OSError, json.JSONDecodeError) as exc:
                    logging.warning("Failed to read extension %s: %s", extension_folder, exc)
                    continue

                extension_name = manifest.get("name", "")
                extension_description = manifest.get("description", "")
                extension_type = "extension"

                if "MSG" in extension_name:
                    messages_folder = extension_version_path / "_locales" / "en"
                    if not messages_folder.is_dir():
                        messages_folder = extension_version_path / "_locales" / "en-US"
                    try:
                        messages_file = next(messages_folder.iterdir())
                        with messages_file.open("r", encoding="utf-8") as messages_json:
                            messages: Any = json.load(messages_json)
                        extension_name = self.__parse_chrome_extension_name(
                            extension_name, messages
                        )
                        extension_description = self.__parse_chrome_extension_description(
                            extension_description, messages
                        )
                        extension_type = "app"
                    except (OSError, StopIteration, json.JSONDecodeError):
                        pass

                perms = {
                    "permissions": manifest.get("permissions"),
                    "origins": manifest.get("hostPermissions"),
                }
                profile_path = root.path / profile

                extension_info_list.append(
                    ExtensionInfo(
                        username=root.username,
                        browser=browser,
                        browser_short=root.browser,
                        profile=profile,
                        risk=self.__calculate_risk(Permission.parse(perms)),
                        extension_id=extension_folder.name,
                        name=extension_name,
                        version=extension_version_path.name.replace("_0", ""),
                        extension_type=extension_type,
                        description=extension_description,
                        creator=manifest.get("author", ""),
                        homepage_url="",
                        active=True,
                        install_date=datetime.fromtimestamp(
                            os.path.getctime(extension_folder)
                        ),
                        update_date=datetime.fromtimestamp(
                            os.path.getmtime(extension_folder)
                        ),
                        path=str(extension_folder),
                        user_permissions=Permission.parse(perms),
                        optional_permissions=Permission(),
                        connections=self.__get_chromium_connections(profile_path),
                    )
                )

        return extension_info_list

    def __get_chromium_connections(self, profile_path: Path) -> list[Connection]:
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
            if anonymization and self.__decode(anonymization[0]) and server.get("server"):
                connections.append(
                    Connection(
                        domain_name=server["server"].replace("https://", "").split(":")[0],
                        active=True,
                    )
                )

        for broken in properties.get("broken_alternative_services", []):
            anonymization = broken.get("anonymization", [None])
            if anonymization and self.__decode(anonymization[0]) and broken.get("host"):
                connections.append(Connection(domain_name=broken["host"], active=False))

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
