# lookup

echo is a Python3 script that looks for Destiny 2 screenshots to be created and then uses the Open AI API to parse the bungie id from the screenshot and launch [Trials Report](https://www.destinytrialsreport.com)

This automates player lookup in game. Simple click on the player name, take a screenshot, and Trials Report will be launched with that player's info.

If you run into any issues, have any ideas, or just want to chat, please post in [issues](https://github.com/mikechambers/lookup/issues) or share on [Discord](https://discord.gg/2Y8bV2Mq3p).

## Requirements

This script requires that:

-   Python 3 is installed
-   You have a valid Destiny 2 Developer API Key. You can grab one from the [Bungie Developer Portal](https://www.bungie.net/en/User/API)
-   You have a valid [Open AI API key](https://platform.openai.com/api-keys)
-   Your API keys are stored in environment variables named DESTINY_API_KEY and OPENAI_API_KEY respectively.