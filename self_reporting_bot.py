import logging
import os.path
from pathlib import Path
import time
import json

from deltabot_cli import BotCli
from deltachat2 import EventType, events
from deltachat2.types import SpecialContactId
from rich.logging import RichHandler

cli = BotCli("self_reporting_bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)],
)


@cli.on(events.NewMessage)
def on_new_message(bot, accid, event):
    chatid = event.msg.chat_id
    msg = event.msg
    try:
        if msg.text.startswith("core_version "):
            bot.rpc.misc_send_text_message(
                accid,
                chatid,
                "Thanks for sending statistics about your usage of Delta Chat to us!",  # TODO
            )
            return

        if msg.file_name != "statistics.txt":
            raise ValueError("Message doesn't contain statistics.txt")

        with open(msg.file) as file:
            new_data = json.load(file)

        statistics_id = new_data["statistics_id"]
        if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in statistics_id):
            raise ValueError("Invalid statistics_id")
        if len(statistics_id) < 11 or len(statistics_id) > 32:
            raise ValueError("statistics_id has the wrong length")

        Path("reports").mkdir(exist_ok=True)
        filename = os.path.join("reports", statistics_id)

        new_data["timestamp_received_by_bot"] = int(time.time())

        if os.path.exists(filename):
            with open(filename) as file:
                existing_data = json.load(file)
        else:
            existing_data = []
        existing_data.append(new_data)

        with open(filename, "w") as file:
            json.dump(existing_data, file, indent=4)

        bot.rpc.misc_send_text_message(
            accid,
            chatid,
            "Thanks for sending statistics about your usage of Delta Chat to us! We will use it to improve the security of Delta Chat.",
        )
    except Exception:
        bot.logger.exception("Could not parse self_reporting message")
        bot.rpc.misc_send_text_message(
            accid,
            chatid,
            "Sorry, I couldn't understand your message.\n\nI am a bot for receiving statistics about your usage of Delta Chat. All other messages will be ignored.",
        )


@cli.on(events.RawEvent)
def log_event(bot, accid, event):
    if event.kind == EventType.INFO:
        bot.logger.info(event.msg)
    elif event.kind == EventType.WARNING:
        bot.logger.warning(event.msg)
    elif event.kind == EventType.ERROR:
        bot.logger.error(event.msg)
    elif event.kind == EventType.MSG_DELIVERED:
        delete_everything(bot, accid, bot.rpc.get_message(accid, event.msg_id))

def delete_everything(bot, accid, msg):
    contact_ids = bot.rpc.get_chat_contacts(accid, msg.chat_id)
    bot.rpc.delete_chat(accid, msg.chat_id)
    for contact_id in contact_ids:
        if contact_id != SpecialContactId.SELF:
            bot.rpc.delete_contact(accid, contact_ids[0])


def main():
    cli.start()


if __name__ == "__main__":
    main()


@cli.on_init
def on_init(bot, args):
    bot.logger.info("Initializing CLI with args: %s", args)
    for accid in bot.rpc.get_all_account_ids():
        bot.rpc.set_config(accid, "delete_server_after", "1")
        bot.rpc.set_config(accid, "delete_device_after", "3600")
