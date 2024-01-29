import logging
import os.path
from pathlib import Path

from deltabot_cli import BotCli, events

cli = BotCli("self_reporting_bot")


@cli.on(events.RawEvent)
def log_event(event):
    logging.info(event)


@cli.on(events.NewMessage)
def on_new_message(event):
    try:
        rpc = event.rpc
        accid = event.accid
        chatid = event.msg.chat_id
        text = event.msg.text
        rpc.delete_messages(accid, [event.msg.id])

        if not text.startswith("core_version "):
            raise ValueError("Message doesn't start with core_version")

        statistics = {}
        for l in text.splitlines():
            parts = l.split()
            statistics[parts[0]] = parts[1]

        self_reporting_id = statistics["self_reporting_id"]
        if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in self_reporting_id):
            raise ValueError("Invalid self_reporting_id")
        if len(self_reporting_id) != 11:
            raise ValueError("self_reporting_id has the wrong length")

        Path("reports").mkdir(exist_ok=True)
        filename = os.path.join("reports", self_reporting_id)
        version = 1
        while os.path.exists(filename + "." + str(version)):
            version += 1
        filename = filename + "." + str(version)

        with open(filename, "w") as file:
            file.write(text)

        rpc.misc_send_text_message(
            accid,
            chatid,
            "Thanks for sending statistics about your usage of Delta Chat to us! We will use it to get a feeling of how people use Delta Chat, and to improve often-occuring issues.",
        )
    except Exception:
        logging.exception("Could not parse self_reporting message")
        rpc.misc_send_text_message(
            accid,
            chatid,
            "Sorry, I couldn't understand your message.\n\nI am a bot for receiving statistics about your usage of Delta Chat. All other messages will be ignored.",
        )


def main():
    cli.start()


if __name__ == "__main__":
    main()
