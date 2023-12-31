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


@dataclass
class Permission:
    permission: Optional[list[str]] = None
    origins: Optional[list[str]] = None

    @staticmethod
    def parse(data: Optional[Any]) -> Optional['Permission']:
        if data is None:
            return None
        if type(data) is dict:
            permission: Any = data.get('permissions', None)
            origins: Any = data.get('origins', None)
            return Permission(permission, origins)
        else:
            raise TypeError(f'Expected dict, got {type(data)}')


@dataclass
class ExtensionInfo:
    username: str
    browser: str
    browser_short: Literal['Firefox', 'Chrome', 'Edge']
    profile: str
    extension_id: str
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


def __is_firefox_installed() -> bool:
    firefox_path: str
    if sys.platform == 'win32':
        logging.info('Windows system detected')
        system_drive: Optional[str] = os.getenv("SystemDrive")
        if system_drive is None:
            raise Exception()
        firefox_path = os.path.join(
            system_drive, '\\\\', 'Program Files', 'Mozilla Firefox', 'firefox.exe')

    elif sys.platform == "linux":
        logging.info('Linux system detected')
        firefox_path = shutil.which('firefox')
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')
        firefox_path = shutil.which('firefox')
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


def __get_firefox_profile_path(username) -> str:
    if sys.platform == 'win32':
        logging.info('Windows system detected')
        system_drive: Optional[str] = os.getenv("SystemDrive")
        if system_drive is None:
            raise Exception()
        profiles_path: str = os.path.join(
            system_drive, '\\\\', 'Users', username, 'AppData', 'Roaming', 'Mozilla', 'Firefox', 'Profiles')
    elif sys.platform == "linux":
        logging.info('Linux system detected')
        profiles_path = os.path.join(
            'home', username, '.mozilla', 'firefox')
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')
        profiles_path = os.path.join(
            'Users', username, 'Library', 'Application Support', 'Firefox', 'Profiles')
    else:
        logging.warning('Unsupported system detected')
        raise Exception('Unsupported system detected')
    return profiles_path


def __get_firefox_installed_extensions(usernames: list[str]) -> list[ExtensionInfo]:
    extension_info_list: list[ExtensionInfo] = []

    for username in usernames:
        # Get Firefox extension JSON files
        ext_files: list[str] = []

        profiles_path: str = __get_firefox_profile_path(username)

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
                        profile=os.path.dirname(ext_file),
                        extension_id=addon.get("id", ""),
                        name=addon.get("defaultLocale", {}).get("name", ""),
                        version=addon.get("version", ""),
                        extension_type=addon.get("type", ""),
                        description=addon.get("defaultLocale", {}).get(
                            "description", ""),
                        creator=addon.get("defaultLocale", {}
                                          ).get("creator", ""),
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


def __is_chrome_installed() -> bool:
    chrome_path: str
    if sys.platform == 'win32':
        logging.info('Windows system detected')
        system_drive: Optional[str] = os.getenv("SystemDrive")
        if system_drive is None:
            raise Exception()
        chrome_path = os.path.join(
            system_drive, '\\\\', 'Program Files', 'Google', 'Chrome', 'Application', 'chrome.exe')
    elif sys.platform == "linux":
        logging.info('Linux system detected')
        chrome_path = shutil.which('chrome')
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')
        chrome_path = shutil.which('chrome')
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


def __get_chrome_profile_path(username: str, browser: str) -> str:

    if sys.platform == 'win32':
        logging.info('Windows system detected')
        system_drive: Optional[str] = os.getenv("SystemDrive")
        if system_drive is None:
            raise Exception()
        browser_specific_path: list[str] = browser.split(' ')

        profiles_path: str = os.path.join(system_drive, '\\\\', 'Users',
                                          username, 'AppData', 'Local', browser_specific_path[0], browser_specific_path[1], 'User Data')
    elif sys.platform == "linux":
        logging.info('Linux system detected')

        browser_specific_path: str = browser.replace(' ', '-').lower()
        profiles_path = os.path.join(
            'home', username, '.config', browser_specific_path)
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')

        browser_specific_path: list[str] = browser.split(' ')
        profiles_path = os.path.join(
            'Users', username, 'Library', 'Application Support', browser_specific_path[0], browser_specific_path[1])
    else:
        logging.warning('Unsupported system detected')
        raise Exception('Unsupported system detected')
    return profiles_path


def __get_chrome_installed_extensions(usernames: list[str]) -> list[ExtensionInfo]:
    return __get_chromium_installed_extensions(usernames=usernames, browser='Google Chrome')


def __is_edge_installed() -> bool:
    chrome_path: str
    if sys.platform == 'win32':
        logging.info('Windows system detected')
        edge_path = 'C:\\\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    elif sys.platform == "linux":
        logging.info('Linux system detected')
        edge_path = shutil.which('edge')
    elif sys.platform == "darwin":
        logging.info('Mac OS system detected')
        edge_path = shutil.which('edge')
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


def __get_edge_installed_extensions(usernames: list[str]) -> list[ExtensionInfo]:
    return __get_chromium_installed_extensions(usernames=usernames, browser='Microsoft Edge')


def __parse_chrome_extension_description(extension_description, messages) -> str:
    desc_field: str = extension_description.removeprefix(
        '__MSG_').removesuffix('__')
    ext_desc_obj: dict | str = messages.get(
        desc_field.lower(), desc_field)

    if isinstance(ext_desc_obj, dict):
        new_extension_description: str = str(ext_desc_obj.get(
            'message', ''))
    elif isinstance(ext_desc_obj, str):
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


def __parse_chrome_extension_name(extension_name, messages) -> str:
    name_field: str = extension_name.removeprefix(
        '__MSG_').removesuffix('__')
    ext_name_obj: dict | str = messages.get(
        name_field.lower(), name_field)
    if isinstance(ext_name_obj, dict):
        new_extension_name: str = str(ext_name_obj.get(
            'message', ''))
    elif isinstance(ext_name_obj, str):
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


def __get_chromium_installed_extensions(usernames: list[str], browser: Literal['Google Chrome', 'Microsoft Edge']) -> list[ExtensionInfo]:
    extension_info_list: list[ExtensionInfo] = []

    if browser == 'Google Chrome':
        browser_short = 'Chrome'
    else:
        browser_short = 'Edge'

    for username in usernames:
        profiles_path: str = __get_chrome_profile_path(
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
                                messages_folder: str = os.path.join(
                                    extensions_path, extension_folder, extension_version, '_locales', 'en-US')

                            messages_file: str = os.listdir(messages_folder)[0]

                            with open(os.path.join(messages_folder, messages_file), 'r', encoding='utf-8') as messages_json:
                                messages: Any = json.load(messages_json)

                                extension_name = __parse_chrome_extension_name(
                                    extension_name, messages)
                                extension_description = __parse_chrome_extension_description(
                                    extension_description, messages)
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
                            browser_short=browser_short,
                            profile=profile,
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

    if __is_firefox_installed():
        extension_info_list.extend(
            __get_firefox_installed_extensions(user_list))
    if __is_chrome_installed():
        extension_info_list.extend(
            __get_chrome_installed_extensions(user_list))
    if __is_edge_installed():
        extension_info_list.extend(__get_edge_installed_extensions(user_list))

    return extension_info_list
