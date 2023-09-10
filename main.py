#! /usr/bin/env python3
# -*- coding: UTF-8 -*-


import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional

import psutil

APPNAME: str = "BROWSER_EXTS"


@dataclass
class Permission:
    permission: Optional[list[str]] = None
    origins: Optional[list[str]] = None

    @staticmethod
    def parse(data: Optional[Any]) -> Optional['Permission']:
        if data is None:
            return None
        if type(data) is dict:
            permission = data.get('permissions', None)
            origins = data.get('origins', None)
            return Permission(permission, origins)
        else:
            raise TypeError(f'Expected dict, got {type(data)}')


@dataclass
class ExtensionInfo:
    username: str
    browser: str
    profile: str
    id: str
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


def is_firefox_installed() -> bool:
    firefox_path: str
    if sys.platform == 'win32':
        logging.info('Windows system detected')
        firefox_path = 'C:\\Program Files\\Mozilla Firefox\\firefox.exe'
    elif sys.platform == "linux":
        logging.info('Linux system detected')
        firefox_path = shutil.which('firefox')
        return False
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')
        firefox_path = shutil.which('firefox')
        return False
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


def get_firefox_installed_extensions(usernames: list[str]) -> list[ExtensionInfo]:
    extension_info_list: list[ExtensionInfo] = []

    for username in usernames:
        # Get Firefox extension JSON files
        ext_files: list[str] = []

        profiles_path: str = f"C:\\\\Users\\{username}\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\"
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
                        username,
                        "Mozilla Firefox",
                        os.path.dirname(ext_file),
                        addon.get("id", ""),
                        addon.get("defaultLocale", {}).get("name", ""),
                        addon.get("version", ""),
                        addon.get("Type", ""),
                        addon.get("defaultLocale", {}).get("description", ""),
                        addon.get("defaultLocale", {}).get("creator", ""),
                        addon.get("defaultLocale", {}).get("homepageURL", ""),
                        addon.get("active", False),
                        datetime.fromtimestamp(
                            float(addon.get("installDate", 0)) / 1000),
                        datetime.fromtimestamp(
                            float(addon.get("updateDate", 0)) / 1000),
                        addon.get("path", ""),
                        Permission.parse(addon.get("userPermissions", None)),
                        Permission.parse(
                            addon.get('optionalPermissions', None))
                    )

                    extension_info_list.append(extension_info)

    return extension_info_list


def is_chrome_installed() -> bool:
    chrome_path: str
    if sys.platform == 'win32':
        logging.info('Windows system detected')
        chrome_path = 'C:\\\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
    elif sys.platform == "linux":
        logging.info('Linux system detected')
        chrome_path = shutil.which('chrome')
        return True
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')
        chrome_path = shutil.which('chrome')
        return True
    else:
        logging.warning('Unsupported system detected')
        return False

    chrome_exists: bool = os.path.exists(chrome_path)
    if chrome_exists:
        logging.info("chrome found.")
        return True
    else:
        logging.info("chrome not found.")
        return False


def get_chrome_installed_extensions(usernames: list[str]) -> list[ExtensionInfo]:
    return __get_chromium_installed_extensions(usernames=usernames, browser='Google Chrome')


def is_edge_installed() -> bool:
    chrome_path: str
    if sys.platform == 'win32':
        logging.info('Windows system detected')
        edge_path = 'C:\\\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    elif sys.platform == "linux":
        logging.info('Linux system detected')
        edge_path = shutil.which('edge')
        return True
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')
        edge_path = shutil.which('edge')
        return True
    else:
        logging.warning('Unsupported system detected')
        return False

    edge_exists: bool = os.path.exists(edge_path)
    if edge_exists:
        logging.info("edge found.")
        return True
    else:
        logging.info("edge not found.")
        return False


def get_edge_installed_extensions(usernames: list[str]) -> list[ExtensionInfo]:
    return __get_chromium_installed_extensions(usernames=usernames, browser='Microsoft Edge')


def __get_chromium_installed_extensions(usernames: list[str], browser: Literal['Google Chrome', 'Microsoft Edge']) -> list[ExtensionInfo]:
    extension_info_list: list[ExtensionInfo] = []
    browser_specific_path: str = browser.replace(' ', '\\')
    system_drive: Optional[str] = os.getenv("SystemDrive")
    if system_drive is None:
        raise Exception()

    for username in usernames:
        local_state_path: str = f"{system_drive}\\\\Users\\{username}\\AppData\\Local\\{browser_specific_path}\\User Data\\Local State"

        try:
            with open(local_state_path, 'r', encoding='utf-8') as local_state_file:
                local_state: Any = json.load(local_state_file)

            chrome_profiles: list[Any] = local_state.get(
                'profile').get('info_cache').keys()

            for profile in chrome_profiles:
                extensions_path: str = f"{system_drive}\\Users\\{username}\\AppData\\Local\\{browser_specific_path}\\User Data\\{profile}\\Extensions"
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
                            manifest = json.load(manifest_file)

                        extension_name: str = manifest.get(
                            'name', '')
                        extension_description: str = manifest.get(
                            'description', '')
                        extension_type = 'extension'

                        if "MSG" in extension_name:
                            if extension_folder == 'nngceckbapebfimnlniiiahkandclblb' or extension_folder == 'kcpnkledgcbobhkgimpbmejgockkplob':
                                print('Beware of the problems!')

                            messages_folder: str = os.path.join(
                                extensions_path, extension_folder, extension_version, '_locales', 'en')
                            messages_file: str = os.listdir(messages_folder)[0]

                            with open(os.path.join(messages_folder, messages_file), 'r', encoding='utf-8') as messages_json:
                                messages = json.load(messages_json)

                                name_field: str = extension_name.removeprefix(
                                    '__MSG_').removesuffix('__')
                                ext_name_obj: dict | str = messages.get(
                                    name_field.lower(), name_field)
                                if isinstance(ext_name_obj, dict):
                                    extension_name: str = ext_name_obj.get(
                                        'message', '')
                                elif isinstance(ext_name_obj, str):
                                    # There are packages in a weird nested structure
                                    temp = messages.get(ext_name_obj, None)
                                    if temp:
                                        extension_name = temp.get('message', None)
                                    else:
                                        extension_name = ext_name_obj
                                else:
                                    raise TypeError(
                                        f'Expected str or dict, got {type(ext_name_obj)}')

                                desc_field: str = extension_description.removeprefix(
                                    '__MSG_').removesuffix('__')
                                ext_desc_obj: dict | str = messages.get(
                                    desc_field.lower(), desc_field)

                                if isinstance(ext_desc_obj, dict):
                                    extension_description: str = ext_desc_obj.get(
                                        'message', '')
                                elif isinstance(ext_desc_obj, str):
                                    # There are packages in a weird nested structure
                                    temp = messages.get(ext_desc_obj, None)
                                    if temp:
                                        extension_description = temp.get('message', None)
                                    else:
                                        extension_description = ext_desc_obj
                                else:
                                    raise TypeError(
                                        f'Expected str or dict, got {type(ext_desc_obj)}')

                                extension_type = 'app'

                        extension_creator: str = manifest.get('author', '')
                        extension_install_date: datetime = datetime.fromtimestamp(
                            os.path.getctime(os.path.join(extensions_path, extension_folder)))
                        extension_update_date: datetime = datetime.fromtimestamp(
                            os.path.getmtime(os.path.join(extensions_path, extension_folder)))

                        perms = dict({'permissions': manifest.get(
                            'permissions', None), 'origins': manifest.get('hostPermissions', None)})

                        extension_info = ExtensionInfo(
                            username=username,
                            browser=browser,
                            profile=profile,
                            id=extension_folder,
                            name=extension_name,
                            version=extension_version,
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
                            optional_permissions=Permission()
                        )

                        extension_info_list.append(extension_info)
                else:
                    logging.info(
                        f"There are no installed extensions for {profile} profile.")
        except Exception as e:
            logging.info(
                f"Something went wrong for user {username}. Exception: {str(e)}")

    return extension_info_list


def get_extension_info() -> list[ExtensionInfo]:
    extension_info_list: list[ExtensionInfo] = []
    user_list: list[str] = [u.name for u in psutil.users()]

    if is_firefox_installed():
        extension_info_list.extend(get_firefox_installed_extensions(user_list))
    if is_chrome_installed():
        extension_info_list.extend(get_chrome_installed_extensions(user_list))
    if is_edge_installed():
        extension_info_list.extend(get_edge_installed_extensions(user_list))

    return extension_info_list


def get_root_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)
    else:
        return './'


def main() -> None:

    logging.basicConfig(filename=os.path.join(get_root_dir(), f'{APPNAME}.log'),
                        encoding='utf-8',
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        datefmt="%Y-%m-%dT%H:%M:%S%z",
                        level=logging.INFO)

    excepthook = logging.error
    logging.info('Starting')

    extensions: list[ExtensionInfo] = get_extension_info()
    for ext in extensions:
        print(f"{ext.browser}\t:\t{ext.name} {ext.version}")


if __name__ == "__main__":
    try:
        main()
        logging.info('Exiting')
    except KeyboardInterrupt:
        logging.info('Cancelled by user.')
        logging.error("Cancelled by user.")
        logging.info('Exiting')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as ex:
        logging.info('ERROR: ' + str(ex))
        logging.info('Exiting')
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)
