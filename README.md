# lookup

echo is a Python3 script that looks for Destiny 2 screenshots to be created and then uses the Open AI API to parse the bungie id from the screenshot and launch [Trials Report](https://www.destinytrialsreport.com) with the parsed player's info.

This automates player lookup in game. Simple click on the player name, take a screenshot, and Trials Report will be launched with that player's info.

If you run into any issues, have any ideas, or just want to chat, please post in [issues](https://github.com/mikechambers/lookup/issues) or share on [Discord](https://discord.gg/2Y8bV2Mq3p).

## Requirements

This script requires that:

-   Python 3 is installed
-   You have a valid Destiny 2 Developer API Key. You can grab one from the [Bungie Developer Portal](https://www.bungie.net/en/User/API)
-   You have a valid [Open AI API key](https://platform.openai.com/api-keys)
-   Your API keys are stored in environment variables named DESTINY_API_KEY and OPENAI_API_KEY respectively.

## Usage

First, before running the script you must install the required libraries:

```
pip install -r requirements.txt
```

To start the script, simply call it, passing the directory where screenshots will be saved:

```
$python lookup.py --screenshot-dir "C:/Users/USERACCOUNT/Documents/Destiny 2/Screenshots/"
```

Then, within Destiny, open the player detail screen and take a screenshot.

![image](images/screenshot.png)

The script will detect the screenshot, parse the bungie id, play a sound and then launch trials report with the player's info.

## Known Issues

You may get a "Error retrieving member from Destiny API" message. This can happen if the bungie id is not extracted correctly from the screenshot (sometimes characters may be missing).

## License

Project released under a [MIT License](LICENSE.md).

[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE.md)
