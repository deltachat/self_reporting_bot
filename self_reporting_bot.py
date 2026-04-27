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
                "You are using an outdated version of Delta Chat. Please update and try again.",
            )
            return

        if msg.file_name != "statistics.txt":
            raise ValueError("Message doesn't contain statistics.txt")

        with open(msg.file) as file:
            new_data = json.load(file)

        stats_id = new_data["stats_id"]
        if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in stats_id):
            raise ValueError("Invalid stats_id")
        if len(stats_id) < 11 or len(stats_id) > 32:
            raise ValueError("stats_id has the wrong length")

        Path("reports").mkdir(exist_ok=True)
        filename = os.path.join("reports", stats_id)

        new_data["timestamp_received_by_bot"] = int(time.time())

        if os.path.exists(filename):
            with open(filename) as file:
                existing_data = json.load(file)
        else:
            existing_data = []
        existing_data.append(new_data)

        with open(filename, "w") as file:
            json.dump(existing_data, file, indent=4)

        bot.logger.info(f"Successfully saved statistics from message {msg.id}.")

        bot.rpc.send_reaction(
            accid,
            msg.id,
            ["❤️"],
        )
    except Exception:
        bot.logger.exception("Could not parse self_reporting message")
        bot.rpc.misc_send_text_message(
            accid,
            chatid,
            "Sorry, I couldn't understand your message.\n\nI am a bot for receiving statistics about your usage of Delta Chat. All other messages will be ignored.",
        )


def cleanup_after_message(bot, accid, msg):
    contact_ids = bot.rpc.get_chat_contacts(accid, msg.chat_id)

    # First delete the chat,
    # because contacts that are still in a chat can't be deleted
    bot.rpc.delete_chat(accid, msg.chat_id)
    bot.logger.info(f"Cleaned up chat {msg.chat_id}.")

    for contact_id in contact_ids:
        if contact_id <= SpecialContactId.LAST_SPECIAL:
            continue
        try:
            bot.rpc.delete_contact(accid, contact_id)
            bot.logger.info(f"Cleaned up contact {contact_id}.")
        except Exception:
            bot.logger.exception("Could not delete contact")


@cli.on(events.RawEvent)
def log_event(bot, accid, event):
    if event.kind == EventType.INFO:
        bot.logger.info(event.msg)
    elif event.kind == EventType.WARNING:
        bot.logger.warning(event.msg)
    elif event.kind == EventType.ERROR:
        bot.logger.error(event.msg)
    elif event.kind == EventType.MSG_DELIVERED:
        cleanup_after_message(bot, accid, bot.rpc.get_message(accid, event.msg_id))
    else:
        bot.logger.info(f"Event: {event}")


def main():
    cli.start()


if __name__ == "__main__":
    main()


@cli.on_init
def on_init(bot, args):
    bot.logger.info("Initializing CLI with args: %s", args)
    for accid in bot.rpc.get_all_account_ids():
        bot.logger.info("Using settings: %s", bot.rpc.get_info(accid))
        bot.rpc.set_config(accid, "delete_server_after", "1")
        bot.rpc.set_config(accid, "delete_device_after", "3600")
