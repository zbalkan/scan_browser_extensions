#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Header, MarkdownViewer

from extensions import ExtensionInfo, Scanner

APP_NAME = "scan_browser_extensions"


def get_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


class DetailsScreen(ModalScreen):
    DEFAULT_CSS = """
        DetailsScreen {
            align: center middle;
        }
    """

    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        safe_content = self.content.replace("```", "\\`\\`\\`")
        markdown_content = f"""
# Extension Details
```json
{safe_content}
```
"""
        container = HorizontalGroup(Button("Back"), Button("Copy"))
        container.styles.align_horizontal = "center"

        yield MarkdownViewer(markdown_content, show_table_of_contents=False)
        yield container

    def on_button_pressed(self, event: Button.Pressed) -> None:
        label = event.button.label.plain
        if label == "Back":
            self.dismiss()
        elif label == "Copy":
            self.app.copy_to_clipboard(self.content)
            self.app.notify("Copied to clipboard.", timeout=2)


class ScannerApp(App):
    """Display browser extension inventory."""

    def compose(self) -> ComposeResult:
        yield Header(name=APP_NAME)
        yield DataTable()

    def on_mount(self) -> None:
        self.title = APP_NAME
        self.extensions: dict[object, ExtensionInfo] = {}

        datatable = self.query_one(DataTable)
        datatable.cursor_type = "row"
        for column in (
            "Username",
            "Browser",
            "Profile",
            "Risk",
            "Extension",
            "Version",
            "Type",
            "Active",
            "Installed",
            "Updated",
        ):
            datatable.add_column(column)

        for extension in Scanner().get_extension_info():
            row_key = datatable.add_row(
                extension.username,
                extension.browser_short,
                extension.profile,
                extension.risk,
                extension.name,
                extension.version,
                extension.extension_type,
                extension.active,
                extension.install_date,
                extension.update_date,
            )
            self.extensions[row_key] = extension

        self.notify("Press Ctrl+Q to exit.", timeout=2)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        extension = self.extensions[event.row_key]
        self.push_screen(DetailsScreen(str(extension)))


def main() -> int:
    logging.basicConfig(
        filename=get_root_dir() / f"{APP_NAME}.log",
        encoding="utf-8",
        format="%(asctime)s:%(levelname)s:%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        level=logging.INFO,
    )

    try:
        logging.info("Starting")
        ScannerApp().run()
        logging.info("Exiting")
        return 0
    except KeyboardInterrupt:
        logging.info("Cancelled by user")
        return 0
    except Exception:
        logging.exception("Unhandled error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
