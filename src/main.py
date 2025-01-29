#! /usr/bin/env python3

import logging
import os
import sys
from typing import Optional

from crxcavator import RiskReport, get_risk_report
from extensions import ExtensionInfo, get_extension_info

APPNAME: str = "BROWSER_EXTS"


def get_root_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)
    else:
        return './'


def main() -> None:

    extensions: list[ExtensionInfo] = get_extension_info()

    for ext in extensions:
        report: Optional[RiskReport] = get_risk_report(
            extension_id=ext.extension_id, extension_version=ext.version, extension_platform=ext.browser_short)
        level: str = 'Unknown'
        if report is not None:
            level = report.RiskLevel
        print(
            f"{ext.browser}\t: {ext.name} {ext.version} ({ext.extension_type})\t(Risk:\t{level})")


if __name__ == "__main__":
    try:
        logging.basicConfig(filename=os.path.join(get_root_dir(), f'{APPNAME}.log'),
                            encoding='utf-8',
                            format='%(asctime)s:%(levelname)s:%(message)s',
                            datefmt="%Y-%m-%dT%H:%M:%S%z",
                            level=logging.INFO)

        excepthook = logging.error
        logging.info('Starting')
        main()
        logging.info('Exiting')
    except KeyboardInterrupt:
        logging.info('Cancelled by user.')
        logging.error("Cancelled by user.")
        logging.info('Exiting')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)  # type: ignore
    except Exception as ex:
        logging.info('ERROR: ' + str(ex))
        logging.info('Exiting')
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)  # type: ignore
