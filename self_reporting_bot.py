import logging
import os.path
from pathlib import Path

from deltabot_cli import BotCli, EventType, events
from rich.logging import RichHandler

cli = BotCli("self_reporting_bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)],
)


@cli.on(events.RawEvent)
def log_event(bot, accid, event):
    if event.kind == EventType.INFO:
        bot.logger.info(event.msg)
    elif event.kind == EventType.WARNING:
        bot.logger.warning(event.msg)
    elif event.kind == EventType.ERROR:
        bot.logger.error(event.msg)


@cli.on(events.NewMessage)
def on_new_message(bot, accid, event):
    chatid = event.msg.chat_id
    try:
        text = event.msg.text
        bot.rpc.delete_messages(accid, [event.msg.id])

        if not text.startswith("core_version "):
            raise ValueError("Message doesn't start with core_version")

        statistics = {}
        for l in text.splitlines():
            parts = l.split()
            statistics[parts[0]] = parts[1]

        self_reporting_id = statistics["self_reporting_id"]
        if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in self_reporting_id):
            raise ValueError("Invalid self_reporting_id")
        if len(self_reporting_id) < 11 or len(self_reporting_id) > 32:
            raise ValueError("self_reporting_id has the wrong length")

        Path("reports").mkdir(exist_ok=True)
        filename = os.path.join("reports", self_reporting_id)
        version = 1
        while os.path.exists(filename + "." + str(version)):
            version += 1
        filename = filename + "." + str(version)

        with open(filename, "w") as file:
            file.write(text)

        bot.rpc.misc_send_text_message(
            accid,
            chatid,
            "Thanks for sending statistics about your usage of Delta Chat to us! We will use it to get a feeling of how people use Delta Chat, and to improve often-occuring issues.",
        )
    except Exception:
        bot.logger.exception("Could not parse self_reporting message")
        bot.rpc.misc_send_text_message(
            accid,
            chatid,
            "Sorry, I couldn't understand your message.\n\nI am a bot for receiving statistics about your usage of Delta Chat. All other messages will be ignored.",
        )


def main():
    cli.start()


if __name__ == "__main__":
    main()
