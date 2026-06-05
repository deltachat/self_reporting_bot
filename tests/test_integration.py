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
    return rpc.send_msg(accid, chat_id, MsgData(file=str(stats_file)))


class TestBotIntegration:

    def test_valid_report_gets_reaction(
        self, user_rpc, user_accid, chat_id_with_bot, reports_dir, tmp_path
    ):
        print("dbg start 1")
        stats = {"stats_id": "test_reaction_id", "metric": 1}
        sent_stats_msg_id = send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)
        print("dbg stats_msg_id", sent_stats_msg_id)

        def got_reaction():
            msg_ids = user_rpc.get_message_ids(user_accid, chat_id_with_bot, False, False)
            for m in msg_ids:
                print("dbg reaction:", user_rpc.get_message_reactions(user_accid, m), "on", m)
            return any(user_rpc.get_message_reactions(user_accid, m) for m in msg_ids)

        wait_for(got_reaction, msg="Bot never sent a reaction")
        print("dbg end 1")

    def test_valid_report_is_saved_to_disk(
        self, chat_id_with_bot, user_rpc, user_accid, reports_dir, tmp_path
    ):
        print("dbg start 2")
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
        print("dbg end 2")

    def test_cleanup(
        self, bot_rpc, bot_accid, user_rpc, user_accid, chat_id_with_bot, reports_dir, tmp_path
    ):
        print("dbg start 3")
        stats = {"stats_id": "test_cleanup_id", "x": 1}
        sent_stats_msg_id = send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

        def got_reaction():
            reactions = user_rpc.get_message_reactions(user_accid, sent_stats_msg_id)
            print("Reactions for message", sent_stats_msg_id, ":", reactions)
            return reactions == ["♥️"]

        wait_for(got_reaction, msg="Reaction never delivered to user")

        # Check that the bot properly cleaned up the chat:
        # TODO this should be extracted into a function and called at the end of every test

        chat_ids = bot_rpc.get_chatlist_entries(bot_accid, None, None, None)
        for chat_id in chat_ids:
            chat_snapshot = bot_rpc.get_basic_chat_info(bot_accid, chat_id)
            assert chat_snapshot.name == "Saved messages" or chat_snapshot.name == "Device messages"
        assert len(chat_ids) == 2

        contacts = bot_rpc.get_contacts(bot_accid, 0, None)
        assert not contacts
        print("dbg end 3")

    # def test_invalid_stats_id_sends_error_message(
    #     self, chat_id_with_bot, user_rpc, user_accid, reports_dir, tmp_path
    # ):
    #     print("dbg start 4")
    #     stats = {"stats_id": "bad id"}  # spaces are invalid
    #     send_statistics(user_rpc, user_accid, chat_id_with_bot, stats, tmp_path)

    #     def got_error_reply():
    #         msg_ids = user_rpc.get_message_ids(user_accid, chat_id_with_bot, False, False)
    #         messages = user_rpc.get_messages(user_accid, msg_ids)
    #         print("dbg")
    #         for m in messages.values():
    #             print(getattr(m, "text", ""))
    #         return True
    #         return any(
    #             "couldn't understand" in (getattr(m, "text", "") or "")
    #             for m in messages.values()
    #         )

    #     wait_for(got_error_reply, msg="Bot never sent error message")
    #     time.sleep(1)
    #     assert not (reports_dir / "bad id").exists()
    #     print("dbg end 4")