import json
import pytest
from unittest.mock import patch, MagicMock
from self_reporting_bot import on_new_message, cleanup_after_message


VALID_STATS = {"stats_id": "abc123XYZ-_00", "some_metric": 42}


class TestOnNewMessage:
    def test_valid_message_saves_report(self, bot, make_event, tmp_path):
        event = make_event(VALID_STATS)
        with patch("self_reporting_bot.Path") as mock_path, \
             patch("self_reporting_bot.os.path.exists", return_value=False), \
             patch("builtins.open", create=True) as mock_open, \
             patch("self_reporting_bot.cleanup_after_message") as mock_cleanup:

            # Use a real tmp dir for reports
            on_new_message(bot, accid=1, event=event)

        bot.rpc.send_reaction.assert_called_once_with(1, event.msg.id, ["❤️"])
        mock_cleanup.assert_called_once()

    def test_valid_message_appends_to_existing_report(self, bot, make_event, tmp_path):
        """Second report for same stats_id appends to the list."""
        stats_dir = tmp_path / "reports"
        stats_dir.mkdir()
        stats_id = VALID_STATS["stats_id"]
        existing = [{"stats_id": stats_id, "old": True}]
        (stats_dir / stats_id).write_text(json.dumps(existing))

        event = make_event(VALID_STATS)

        with patch("self_reporting_bot.os.path.join", return_value=str(stats_dir / stats_id)), \
             patch("self_reporting_bot.os.path.exists", return_value=True), \
             patch("self_reporting_bot.cleanup_after_message"):
            on_new_message(bot, accid=1, event=event)

        saved = json.loads((stats_dir / stats_id).read_text())
        assert len(saved) == 2
        assert saved[0]["old"] is True
        assert saved[1]["some_metric"] == 42

    def test_wrong_filename_sends_error(self, bot, make_event):
        event = make_event(VALID_STATS, file_name="wrong.txt")

        with patch("self_reporting_bot.cleanup_after_message"):
            on_new_message(bot, accid=1, event=event)

        bot.rpc.misc_send_text_message.assert_called_once()
        bot.rpc.send_reaction.assert_not_called()

    def test_stats_id_too_short(self, bot, make_event):
        event = make_event({"stats_id": "short"})  # only 5 chars

        with patch("self_reporting_bot.cleanup_after_message"):
            on_new_message(bot, accid=1, event=event)

        bot.rpc.misc_send_text_message.assert_called_once()

    def test_stats_id_too_long(self, bot, make_event):
        event = make_event({"stats_id": "a" * 33})

        with patch("self_reporting_bot.cleanup_after_message"):
            on_new_message(bot, accid=1, event=event)

        bot.rpc.misc_send_text_message.assert_called_once()

    def test_stats_id_invalid_chars(self, bot, make_event):
        event = make_event({"stats_id": "invalid/id!!!"})

        with patch("self_reporting_bot.cleanup_after_message"):
            on_new_message(bot, accid=1, event=event)

        bot.rpc.misc_send_text_message.assert_called_once()

    def test_outdated_core_version_message(self, bot, make_event):
        event = make_event(VALID_STATS)
        event.msg.text = "core_version 1.2.3"

        on_new_message(bot, accid=1, event=event)

        bot.rpc.misc_send_text_message.assert_called_once_with(
            1, 42, "You are using an outdated version of Delta Chat. Please update and try again."
        )

    def test_missing_stats_id_key(self, bot, make_event):
        event = make_event({"some_metric": 99})  # no stats_id key

        with patch("self_reporting_bot.cleanup_after_message"):
            on_new_message(bot, accid=1, event=event)

        bot.rpc.misc_send_text_message.assert_called_once()

    def test_timestamp_is_added(self, bot, make_event, tmp_path):
        stats_dir = tmp_path / "reports"
        stats_dir.mkdir()
        stats_id = VALID_STATS["stats_id"]

        event = make_event(VALID_STATS)

        with patch("self_reporting_bot.os.path.join", return_value=str(stats_dir / stats_id)), \
             patch("self_reporting_bot.os.path.exists", return_value=False), \
             patch("self_reporting_bot.cleanup_after_message"):
            on_new_message(bot, accid=1, event=event)

        saved = json.loads((stats_dir / stats_id).read_text())
        assert "timestamp_received_by_bot" in saved[0]


class TestCleanupAfterMessage:

    def test_deletes_chat_and_contacts(self, bot):
        bot.rpc.get_chat_contacts.return_value = [100, 101]
        cleanup_after_message(bot, accid=1, chat_id=42)

        bot.rpc.delete_chat.assert_called_once_with(1, 42)
        assert bot.rpc.delete_contact.call_count == 2

    def test_skips_special_contacts(self, bot):
        # SpecialContactId.LAST_SPECIAL is typically 10
        bot.rpc.get_chat_contacts.return_value = [1, 2, 100]
        cleanup_after_message(bot, accid=1, chat_id=42)

        # Only contact 100 should be deleted
        bot.rpc.delete_contact.assert_called_once_with(1, 100)

    def test_delete_contact_failure_is_logged(self, bot):
        bot.rpc.get_chat_contacts.return_value = [100]
        bot.rpc.delete_contact.side_effect = Exception("network error")

        cleanup_after_message(bot, accid=1, chat_id=42)  # should not raise

        bot.logger.exception.assert_called_once()