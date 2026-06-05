# tests/test_integration.py
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
    rpc.send_msg(accid, chat_id, MsgData(file=str(stats_file)))


class TestBotIntegration:

    def test_valid_report_gets_reaction_not_text(
        self, user_rpc, user_accid, chat_id_with_bot, reports_dir, tmp_path
    ):
        stats = {"stats_id": "validId_test001", "metric": 1}
        chat_id = send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

        def got_reaction():
            msgs = user_rpc.get_messages(user_accid, chat_id)
            return any(getattr(m, "reactions", None) for m in msgs)

        wait_for(got_reaction, msg="Bot never sent a reaction")

        msgs = user_rpc.get_messages(user_accid, chat_id)
        bot_text_replies = [
            m for m in msgs
            if getattr(m, "from_id", None) != user_accid
            and getattr(m, "text", None)
            and not getattr(m, "is_info", False)
        ]
        assert bot_text_replies == [], "Bot should react, not reply with text"

    def test_valid_report_is_saved_to_disk(
        self, chat_id_with_bot, user_rpc, user_accid, reports_dir, tmp_path
    ):
        stats_id = "savedToDisk001"
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

    def test_cleanup(
        self, bot_rpc, bot_accid, user_rpc, user_accid, chat_id_with_bot, reports_dir, tmp_path
    ):
        stats = {"stats_id": "cleanupOrder001", "x": 1}
        send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

        def got_reaction():
            msg_ids = user_rpc.get_message_ids(user_accid, chat_id_with_bot, False, False)
            return any(user_rpc.get_message_reactions(user_accid, m) for m in msg_ids)

        wait_for(got_reaction, msg="Reaction never delivered to user — cleanup may have fired too early")

        # Check that the bot properly cleaned up the chat:

        chat_ids = bot_rpc.get_chatlist_entries(bot_accid, None, None, None)
        assert len(chat_ids) == 2
        for chat_id in chat_ids:
            chat_snapshot = bot_rpc.get_basic_chat_info(bot_accid, chat_id)
            assert chat_snapshot.name == "Saved messages" or chat_snapshot.name == "Device messages"

        contacts = bot_rpc.get_contacts(bot_accid, 0, None)
        assert not contacts

    # def test_invalid_stats_id_sends_error_message(
    #     self, chat_id_with_bot, user_rpc, user_accid, reports_dir, tmp_path
    # ):
    #     stats = {"stats_id": "bad id!!!"}  # spaces and ! are invalid
    #     chat_id = send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

    #     def got_error_reply():
    #         msgs = user_rpc.get_messages(user_accid, chat_id)
    #         return any(
    #             "couldn't understand" in (getattr(m, "text", "") or "")
    #             for m in msgs
    #         )

    #     wait_for(got_error_reply, msg="Bot never sent error message")

    #     # Nothing should be saved for an invalid stats_id
    #     time.sleep(1)
    #     assert not (reports_dir / "bad id!!!").exists()
