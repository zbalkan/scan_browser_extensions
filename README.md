# Browser Extension Scanner

This proof of concept application scans extensions on Mozilla Firefox, Google Chrome and Microsoft Edge.

Even though we can have an inventory of software on our servers, the extensions are another threat vector to be considered. The goal is to allow a cross-platform script to allow extension information collection.

The code is based on [Andy Svintsitsky's work](https://github.com/andysvints/PowerShellIT/tree/master/PowerShellIT%20%235%20-%20Browser%20Extensions).

## Usage

1. Create a virtual environment of your choice.
2. Use `pip install - r requirements.txt`.
3. Run `python3 src/main.py`.
4. Profit!

## Roadmap

- [x] Add extension risk analysis
- [ ] Test on Linux
- [ ] Test on Mac
