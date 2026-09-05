# Browser Extension Scanner

This proof of concept scans Mozilla Firefox, Google Chrome and Microsoft Edge extension artifacts across local user profiles.

Browser extensions are part of the software inventory, but they are easy to miss when inventory is limited to installed applications. The scanner reads browser profile artifacts directly, normalizes the extension information, and displays it in a small Textual interface. It does not require the browser executable to be present or running.

The original code was based on [Andy Svintsitsky's work](https://github.com/andysvints/PowerShellIT/tree/master/PowerShellIT%20%235%20-%20Browser%20Extensions). Connection and domain extraction was inspired by the [ExtensionHound](https://github.com/arsolutioner/ExtensionHound) project.

## Risk flag

The risk flag is deliberately simple. It highlights extensions that request selected sensitive permissions, such as cookie, clipboard, debugger, proxy, scripting, history or native-messaging access, or broad host access such as `<all_urls>` and `*://*/*`.

The flag is an inventory aid rather than a malware verdict. The extension details show the underlying permissions and host permissions so they can be reviewed directly.

## Usage

1. Create and activate a virtual environment.
2. Run `pip install -r requirements.txt`.
3. Run `python src/main.py`.
