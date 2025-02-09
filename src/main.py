#! /usr/bin/env python3

import logging
import os
import sys

from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Header, Label, MarkdownViewer
from textual.widgets._data_table import RowKey

from extensions import Scanner

APP_NAME: str = "scan_browser_extensions"


def get_root_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)
    else:
        return './'


class MyModalScreen(ModalScreen):
    DEFAULT_CSS = """
        MyModalScreen {
            align: center middle;
        }
        """

    content: str = ''

    def compose(self):

        markdown_content = f"""
# Extension Details
```json
{self.content}
```
        """
        container = HorizontalGroup(
            Button("Back"),
            Button("Copy"))
        container.styles.align_horizontal = "center"

        yield MarkdownViewer(markdown_content, show_table_of_contents=False)
        yield container

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.label.plain == "Back":  # type: ignore
            self.dismiss()
        elif event.button.label.plain == "Copy":  # type: ignore
            self.app.copy_to_clipboard(self.content)
            self.app.notify("Copied to clipboard.", timeout=2)
        else:
            pass


class ScannerApp(App):
    """A Textual app to manage stopwatches."""

    extensions: dict = {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(name=APP_NAME)
        yield DataTable()

    def on_mount(self) -> None:
        """Called when the app is mounted."""

        self.title = APP_NAME

        datatable = self.query_one(DataTable)
        datatable.cursor_type = "row"

        datatable.add_column("Username")
        datatable.add_column("Browser")
        datatable.add_column("Profile")
        datatable.add_column("Extension")
        datatable.add_column("Version")
        datatable.add_column("Type")
        datatable.add_column("Active")
        datatable.add_column("Installed")
        datatable.add_column("Updated")

        for ext in Scanner().get_extension_info():
            row_key = datatable.add_row(
                ext.username,
                ext.browser_short,
                ext.profile,
                ext.name,
                ext.version,
                ext.extension_type,
                ext.active,
                ext.install_date,
                ext.update_date
            )
            self.extensions[row_key] = ext

        self.app.notify("Press Ctrl+Q to exit.", timeout=2)

    def on_data_table_row_selected(
        self,
        event: DataTable.RowSelected,
    ) -> None:
        row_key: RowKey = event.row_key
        ext = self.extensions[row_key]
        screen = MyModalScreen()
        screen.content = str(ext)
        self.push_screen(screen, self.modal_screen_callback)

    def modal_screen_callback(self, time) -> None:
        self.mount(Label(f"Modal dismissed at {time}."))


if __name__ == "__main__":
    try:
        logging.basicConfig(filename=os.path.join(get_root_dir(), f'{APP_NAME}.log'),
                            encoding='utf-8',
                            format='%(asctime)s:%(levelname)s:%(message)s',
                            datefmt="%Y-%m-%dT%H:%M:%S%z",
                            level=logging.INFO)

        excepthook = logging.error
        logging.info('Starting')
        app = ScannerApp()
        app.run()
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
