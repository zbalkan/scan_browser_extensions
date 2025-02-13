import base64
import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional, Union

import psutil


class ExtensionEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__dict__"):  # Serialize objects with attributes
            return obj.__dict__
        elif isinstance(obj, datetime):  # Serialize datetime objects
            return obj.isoformat()
        return super().default(obj)  # Default behavior for other types


@dataclass
class Permission:
    permission: Optional[list[str]] = None
    origins: Optional[list[str]] = None

    @staticmethod
    def parse(data: Optional[Any]) -> Optional['Permission']:
        if data is None:
            return None
        if isinstance(data, dict):
            permission: Any = data.get('permissions', None)  # type: ignore
            origins: Any = data.get('origins', None)  # type: ignore
            return Permission(permission, origins)
        else:
            raise TypeError(f'Expected dict, got {type(data)}')


@dataclass
class Connection:
    domain_name: str
    active: bool


@dataclass
class ExtensionInfo:
    username: str
    browser: str
    browser_short: Literal['Firefox', 'Chrome', 'Edge']
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

    platform: str
    has_firefox: bool
    has_chrome: bool
    has_edge: bool

    def __init__(self) -> None:
        self.platform = sys.platform

        self.has_firefox = self.__is_firefox_installed()
        self.has_chrome = self.__is_chrome_installed()
        self.has_edge = self.__is_edge_installed()

    def __calculate_risk(self, permissions: Optional[Permission]) -> str:
        # Reference: https://medium.com/quiq-blog/detecting-high-risk-chrome-extensions-with-osquery-bca1a8856448
        risky_permissions: list[str] = ['clipboardWrite', '<all_urls>', 'tabs', 'cookies', '://*/']

        risky: bool = False
        if permissions is not None:
            if permissions.permission is not None:
                for permission in permissions.permission:
                    if permission in risky_permissions:
                        risky = True
        if risky:
            return '🚩'
        else:
            return '🟢'

    def __is_firefox_installed(self) -> bool:
        firefox_path: str
        if self.platform == 'win32':
            system_drive: Optional[str] = os.getenv("SystemDrive")
            if system_drive is None:
                raise Exception()
            firefox_path = os.path.join(
                system_drive, '\\\\', 'Program Files', 'Mozilla Firefox', 'firefox.exe')

        elif self.platform == "linux":
            firefox_path = shutil.which('firefox')  # type: ignore
        elif self.platform == "darwin":
            firefox_path = shutil.which('firefox')  # type: ignore
        else:
            logging.warning('Unsupported system detected')
            return False

        firefox_exists: bool = os.path.exists(firefox_path)
        if firefox_exists:
            logging.info("Firefox found.")
            return True
        else:
            logging.info("Firefox not found.")
            return False

    def __get_firefox_profile_path(self, username: str) -> str:
        if self.platform == 'win32':
            system_drive: Optional[str] = os.getenv("SystemDrive")
            if system_drive is None:
                raise Exception()
            profiles_path: str = os.path.join(
                system_drive, '\\\\', 'Users', username, 'AppData', 'Roaming', 'Mozilla', 'Firefox', 'Profiles')
        elif self.platform == "linux":
            profiles_path = os.path.join(
                'home', username, '.mozilla', 'firefox')
        elif self.platform == "darwin":
            profiles_path = os.path.join(
                'Users', username, 'Library', 'Application Support', 'Firefox', 'Profiles')
        else:
            logging.warning('Unsupported system detected')
        return profiles_path

    def __get_firefox_installed_extensions(self, usernames: list[str]) -> list[ExtensionInfo]:
        extension_info_list: list[ExtensionInfo] = []

        for username in usernames:
            # Get Firefox extension JSON files
            ext_files: list[str] = []

            profiles_path: str = self.__get_firefox_profile_path(username)

            profiles: list[str] = [os.path.join(profiles_path, name) for name in os.listdir(
                profiles_path) if os.path.isdir(os.path.join(profiles_path, name))]
            for profile in profiles:
                target: str = os.path.join(profile, 'extensions.json')
                if os.path.exists(target):
                    ext_files.append(target)
            ext_files.sort()

            for ext_file in ext_files:
                with open(ext_file, 'r', encoding='utf-8') as json_file:
                    data: Any = json.load(json_file)

                    addons: list[Any] = data.get("addons", [])

                    for addon in addons:
                        extension_info = ExtensionInfo(
                            username=username,
                            browser='Mozilla Firefox',
                            browser_short='Firefox',
                            profile=os.path.basename(os.path.dirname(ext_file)).split(".")[1],
                            extension_id=addon.get("id", ""),
                            risk=self.__calculate_risk(Permission.parse(addon.get('permissions', None))),
                            name=addon.get("defaultLocale", {}).get("name", ""),
                            version=addon.get("version", ""),
                            extension_type=addon.get("type", ""),
                            description=addon.get("defaultLocale", {}).get(
                                "description", ""),
                            creator=addon.get("defaultLocale", {}).get("creator", ""),
                            homepage_url=addon.get(
                                "defaultLocale", {}).get("homepageURL", ""),
                            active=addon.get("active", False),
                            install_date=datetime.fromtimestamp(
                                float(addon.get("installDate", 0)) / 1000),
                            update_date=datetime.fromtimestamp(
                                float(addon.get("updateDate", 0)) / 1000),
                            path=addon.get("path", ""),
                            user_permissions=Permission.parse(
                                addon.get("userPermissions", None)),
                            optional_permissions=Permission.parse(
                                addon.get('optionalPermissions', None))
                        )

                        extension_info_list.append(extension_info)

        return extension_info_list

    def __is_chrome_installed(self) -> bool:
        chrome_path: str
        if self.platform == 'win32':
            system_drive: Optional[str] = os.getenv("SystemDrive")
            if system_drive is None:
                raise Exception()
            chrome_path = os.path.join(
                system_drive, '\\\\', 'Program Files', 'Google', 'Chrome', 'Application', 'chrome.exe')
        elif self.platform == "linux":
            chrome_path = shutil.which('chrome')  # type: ignore
        elif self.platform == "darwin":
            chrome_path = shutil.which('chrome')  # type: ignore
        else:
            logging.warning('Unsupported system detected')
            return False

        chrome_exists: bool = os.path.exists(chrome_path)
        if chrome_exists:
            logging.info("Chrome found.")
            return True
        else:
            logging.info("Chrome not found.")
            return False

    def __get_chrome_profile_path(self, username: str, browser: str) -> str:

        browser_specific_path: list[str]
        if self.platform == 'win32':
            system_drive: Optional[str] = os.getenv("SystemDrive")
            if system_drive is None:
                raise Exception()
            browser_specific_path = browser.split(' ')
            profiles_path: str = os.path.join(system_drive, '\\\\', 'Users', username, 'AppData', 'Local', browser_specific_path[0], browser_specific_path[1], 'User Data')
        elif self.platform == "linux":
            browser_specific_path = browser.replace(' ', '-').lower()  # type: ignore
            profiles_path = os.path.join('home', username, '.config', browser_specific_path)  # type: ignore
        elif self.platform == "darwin":
            browser_specific_path = browser.split(' ')
            profiles_path = os.path.join(
                'Users', username, 'Library', 'Application Support', browser_specific_path[0], browser_specific_path[1])
        else:
            logging.warning('Unsupported system detected')
        return profiles_path

    def __get_chrome_installed_extensions(self, usernames: list[str]) -> list[ExtensionInfo]:
        return self.__get_chromium_installed_extensions(usernames=usernames, browser='Google Chrome')

    def __is_edge_installed(self) -> bool:
        edge_path: str
        if self.platform == 'win32':
            edge_path = 'C:\\\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
        elif self.platform == "linux":
            edge_path = shutil.which('edge')  # type: ignore
        elif self.platform == "darwin":
            edge_path = shutil.which('edge')  # type: ignore
        else:
            logging.warning('Unsupported system detected')
            return False

        edge_exists: bool = os.path.exists(edge_path)
        if edge_exists:
            logging.info("Edge found.")
            return True
        else:
            logging.info("Edge not found.")
            return False

    def __get_edge_installed_extensions(self, usernames: list[str]) -> list[ExtensionInfo]:
        return self.__get_chromium_installed_extensions(usernames=usernames, browser='Microsoft Edge')

    def __parse_chrome_extension_description(self, extension_description: str, messages: dict[str, Any]) -> str:
        desc_field: str = extension_description.removeprefix(
            '__MSG_').removesuffix('__')
        ext_desc_obj: Union[dict[str, Any], str] = messages.get(
            desc_field.lower(), desc_field)

        if isinstance(ext_desc_obj, dict):
            new_extension_description: str = str(ext_desc_obj.get(
                'message', ''))
        elif isinstance(ext_desc_obj, str):  # type: ignore
            # There are packages in a weird nested structure
            temp: Any = messages.get(ext_desc_obj, None)
            if temp:
                new_extension_description = str(temp.get(
                    'message', None))
            else:
                new_extension_description = ext_desc_obj
        else:
            raise TypeError(
                f'Expected str or dict, got {type(ext_desc_obj)}')

        return new_extension_description

    def __parse_chrome_extension_name(self, extension_name: str, messages: dict[str, Any]) -> str:
        name_field: str = extension_name.removeprefix(
            '__MSG_').removesuffix('__')
        ext_name_obj: dict | str = messages.get(name_field.lower(), name_field)  # type: ignore
        if isinstance(ext_name_obj, dict):
            new_extension_name: str = str(ext_name_obj.get('message', ''))  # type: ignore
        elif isinstance(ext_name_obj, str):   # type: ignore
            # There are packages in a weird nested structure
            temp: Any = messages.get(
                ext_name_obj, None)
            if temp:
                new_extension_name = str(temp.get(
                    'message', None))
            else:
                new_extension_name = ext_name_obj
        else:
            raise TypeError(
                f'Expected str or dict, got {type(ext_name_obj)}')

        return new_extension_name

    def __decode(self, encoded: str) -> Optional[str]:
        try:
            decoded = base64.b64decode(encoded).decode('utf-8')
            if 'chrome-extension://' in decoded:
                return decoded.split('chrome-extension://')[-1]
            return None
        except Exception as e:
            print(e)
            return None

    def __get_chromium_installed_extensions(self, usernames: list[str], browser: Literal['Google Chrome', 'Microsoft Edge']) -> list[ExtensionInfo]:
        extension_info_list: list[ExtensionInfo] = []

        browser_short: str
        if browser == 'Google Chrome':
            browser_short = 'Chrome'
        else:
            browser_short = 'Edge'

        for username in usernames:
            profiles_path: str = self.__get_chrome_profile_path(
                username=username, browser=browser)

            local_state_path: str = os.path.join(profiles_path, 'Local State')
            try:
                with open(local_state_path, 'r', encoding='utf-8') as local_state_file:
                    local_state: Any = json.load(local_state_file)

                chrome_profiles: list[Any] = local_state.get(
                    'profile').get('info_cache').keys()

                for profile in chrome_profiles:
                    extensions_path: str = os.path.join(
                        profiles_path, profile, 'Extensions')
                    if os.path.exists(extensions_path):
                        extension_folders: list[str] = [e for e in os.listdir(
                            extensions_path) if e != "Temp"]
                        extension_folders.sort()

                        for extension_folder in extension_folders:
                            extension_version: str = os.listdir(os.path.join(
                                extensions_path, extension_folder))[0]
                            manifest_path: str = os.path.join(
                                extensions_path, extension_folder, extension_version, 'manifest.json')

                            with open(manifest_path, 'r', encoding='utf-8') as manifest_file:
                                manifest: Any = json.load(manifest_file)

                            extension_name: str = manifest.get(
                                'name', '')
                            extension_description: str = manifest.get(
                                'description', '')
                            extension_type = 'extension'

                            if "MSG" in extension_name:
                                messages_folder: str = os.path.join(
                                    extensions_path, extension_folder, extension_version, '_locales', 'en')
                                if os.path.exists(messages_folder) is False:
                                    messages_folder = os.path.join(
                                        extensions_path, extension_folder, extension_version, '_locales', 'en-US')

                                messages_file: str = os.listdir(messages_folder)[0]

                                with open(os.path.join(messages_folder, messages_file), 'r', encoding='utf-8') as messages_json:
                                    messages: Any = json.load(messages_json)

                                    extension_name = self.__parse_chrome_extension_name(
                                        extension_name, messages)
                                    extension_description = self.__parse_chrome_extension_description(
                                        extension_description, messages)
                                    extension_type = 'app'

                            extension_creator: str = manifest.get('author', '')
                            extension_install_date: datetime = datetime.fromtimestamp(
                                os.path.getctime(os.path.join(extensions_path, extension_folder)))
                            extension_update_date: datetime = datetime.fromtimestamp(
                                os.path.getmtime(os.path.join(extensions_path, extension_folder)))

                            perms = dict({'permissions': manifest.get(
                                'permissions', None), 'origins': manifest.get('hostPermissions', None)})

                            connections = self.__get_chromium_connections(os.path.join(
                                profiles_path, profile))

                            extension_info = ExtensionInfo(
                                username=username,
                                browser=browser,
                                browser_short=browser_short,  # type: ignore
                                profile=profile,
                                risk=self.__calculate_risk(Permission.parse(perms)),
                                extension_id=extension_folder,
                                name=extension_name,
                                version=extension_version.replace('_0', ''),
                                extension_type=extension_type,
                                description=extension_description,
                                creator=extension_creator,
                                homepage_url="",
                                active=True,
                                install_date=extension_install_date,
                                update_date=extension_update_date,
                                path=os.path.join(
                                    extensions_path, extension_folder),
                                user_permissions=Permission().parse(perms),
                                optional_permissions=Permission(),
                                connections=connections
                            )

                            extension_info_list.append(extension_info)
                    else:
                        logging.info(
                            f"There are no installed extensions for {profile} profile.")
            except Exception as e:
                logging.info(
                    f"Something went wrong for user {username}. Exception: {str(e)}")

        return extension_info_list

    def __get_chromium_connections(self, profile_path: str) -> list[Any]:
        # Define possible paths
        possible_paths = [
            os.path.join(profile_path, 'Network', 'Network Persistent State'),
            os.path.join(profile_path, 'Network Persistent State')
        ]

        # Select the first valid file path
        network_state_file = next(
            (path for path in possible_paths if os.path.exists(path)), None)

        if network_state_file is None:
            logging.warning(
                f"No Network Persistent State file found in {profile_path}")
            return []

        # Attempt to read and parse the JSON file
        try:
            with open(network_state_file, 'r', encoding='utf-8') as nf:
                network_state: Any = json.load(nf)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to read {network_state_file}: {e}")
            return []

        connections: list[Connection] = []
        properties = network_state.get('net', {}).get(
            'http_server_properties', {})

        # Process active connections
        connections.extend(filter(None, [
            Connection(domain_name=server.get('server', '').replace(
                'https://', '').split(':')[0], active=True)
            if self.__decode(server.get('anonymization', [None])[0]) and server.get('server')
            else None
            for server in properties.get('servers', [])
        ]))

        # Process broken connections
        connections.extend(filter(None, [
            Connection(domain_name=broken.get('host', ''), active=False)
            if self.__decode(broken.get('anonymization', [None])[0]) and broken.get('host')
            else None
            for broken in properties.get('broken_alternative_services', [])
        ]))

        return connections

    def get_extension_info(self) -> list[ExtensionInfo]:
        extension_info_list: list[ExtensionInfo] = []
        user_list: list[str] = [u.name for u in psutil.users()]

        if self.has_firefox:
            extension_info_list.extend(
                self.__get_firefox_installed_extensions(user_list))
        if self.has_chrome:
            extension_info_list.extend(
                self.__get_chrome_installed_extensions(user_list))
        if self.has_edge:
            extension_info_list.extend(self.__get_edge_installed_extensions(user_list))

        return extension_info_list
