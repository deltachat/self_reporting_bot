# Self_reporting Bot

If you send statistics to this bot, then it will save them. See https://github.com/deltachat/deltachat-android/issues/2909.

## Install

To install, open your terminal and run:

```sh
pip install git+https://github.com/deltachat/self_reporting_bot.git
```

## Usage

Configure the bot:

```sh
self_reporting_bot init bot@example.com PASSWORD
```

Start the bot:

```sh
self_reporting_bot serve
```

Run `self_reporting_bot --help` to see all available options.
