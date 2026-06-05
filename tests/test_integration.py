import json
import time
import pytest
from pathlib import Path


def wait_for(condition, timeout=5, interval=0.3, msg="condition never met"):
    """Poll until condition() is truthy or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise TimeoutError(msg)


def send_statistics(rpc, accid, chat_id, stats_data, tmp_path, filename="statistics.txt"):
    stats_file = tmp_path / filename
    stats_file.write_text(json.dumps(stats_data))
    from deltachat2.types import MsgData
    return rpc.send_msg(accid, chat_id, MsgData(file=str(stats_file)))


def assert_bot_cleaned_up(bot_rpc, bot_accid):
    chat_ids = bot_rpc.get_chatlist_entries(bot_accid, None, None, None)
    assert len(chat_ids) == 0

    contacts = bot_rpc.get_contacts(bot_accid, 0, None)
    assert len(contacts) == 0


def test_valid_report_gets_reaction(
    user_rpc, user_accid, bot_rpc, bot_accid, chat_id_with_bot, reports_dir, tmp_path
):
    stats = {"stats_id": "test_reaction_id", "metric": 1}
    sent_stats_msg_id = send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

    def got_reaction():
        reactions = user_rpc.get_message_reactions(user_accid, sent_stats_msg_id)
        return reactions is not None and reactions.reactions[0].emoji == '❤️'

    wait_for(got_reaction, msg="Bot never sent a reaction")

    assert_bot_cleaned_up(bot_rpc, bot_accid)


def test_valid_report_is_saved_to_disk(
    chat_id_with_bot, user_rpc, bot_rpc, bot_accid, user_accid, reports_dir, tmp_path
):
    stats_id = "test_saved_to_disk_id"
    stats = {"stats_id": stats_id, "some_metric": 99}
    send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

    def report_exists():
        p = reports_dir / stats_id
        try:
            return p.exists() and json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return False

    saved = wait_for(report_exists, msg="Report never appeared on disk")
    assert saved[0]["some_metric"] == 99
    assert "timestamp_received_by_bot" in saved[0]

    assert_bot_cleaned_up(bot_rpc, bot_accid)


def test_invalid_stats_id_sends_error_message(
    chat_id_with_bot, user_rpc, bot_rpc, bot_accid, user_accid, reports_dir, tmp_path
):
    stats = {"stats_id": "bad id"}  # spaces are invalid
    send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

    def got_error_reply():
        msg_ids = user_rpc.get_message_ids(user_accid, chat_id_with_bot, False, False)
        messages = user_rpc.get_messages(user_accid, msg_ids)
        return any(
            "couldn't understand" in (getattr(m, "text", "") or "")
            for m in messages.values()
        )

    wait_for(got_error_reply, msg="Bot never sent error message")
    time.sleep(1)
    assert not (reports_dir / "bad id").exists()

    assert_bot_cleaned_up(bot_rpc, bot_accid)
