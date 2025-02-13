# Browser Extension Scanner

This proof of concept application scans extensions on Mozilla Firefox, Google Chrome and Microsoft Edge.

Even though we can have an inventory of software on our servers, the extensions are another threat vector to be considered. The goal is to allow a cross-platform script to allow extension information collection.

The code is based on [Andy Svintsitsky's work](https://github.com/andysvints/PowerShellIT/tree/master/PowerShellIT%20%235%20-%20Browser%20Extensions).

I recently added the connections/domains used by extensions thanks to [ExtensionHound](https://github.com/arsolutioner/ExtensionHound) project.

## About risk reports

Since CRXcavator is not active for some time, the risk assessment feature is removed.

Instead, I used the high-risk permission checks listed by [Qliq team](https://medium.com/quiq-blog/detecting-high-risk-chrome-extensions-with-osquery-bca1a8856448). While they mention `osquery` and Chrome, the same permissions apply to Firefox as well and we can use the scanner.

## Usage

1. Create a virtual environment of your choice.
2. Use `pip install - r requirements.txt`.
3. Run `python3 src/main.py`.
4. Profit!
