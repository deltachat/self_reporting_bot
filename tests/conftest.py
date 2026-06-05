# tests/conftest.py
import json
import logging
import threading
import time
import pytest
from pathlib import Path
from deltachat2 import Bot, events
from deltachat2.rpc import Rpc
from deltachat2.transport import IOTransport
from deltachat2.types import EventType

CHATMAIL_QR = "dcaccount:ci-chatmail.testrun.org"


def make_rpc(accounts_dir: Path) -> tuple:
    transport = IOTransport(accounts_dir=str(accounts_dir))
    transport.start()
    return Rpc(transport), transport


def wait_for_event(rpc, kind, predicate=lambda e: True, timeout=30):
    """Poll get_next_event until an event matching kind and predicate arrives."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        event = rpc.get_next_event()
        if event.event.kind == kind and predicate(event.event):
            return event
    raise TimeoutError(f"Timed out waiting for event {kind}")


@pytest.fixture(scope="session")
def bot_rpc(tmp_path_factory):
    accounts_dir = tmp_path_factory.mktemp("bot_accounts")
    rpc, transport = make_rpc(accounts_dir)
    yield rpc
    transport.close()


@pytest.fixture(scope="session")
def user_rpc(tmp_path_factory):
    accounts_dir = tmp_path_factory.mktemp("user_accounts")
    rpc, transport = make_rpc(accounts_dir)
    yield rpc
    transport.close()


@pytest.fixture(scope="session")
def bot_accid(bot_rpc):
    accid = bot_rpc.add_account()
    bot_rpc.set_config(accid, "displayname", "TestBot")
    bot_rpc.set_config(accid, "bot", "1")
    bot_rpc.add_transport_from_qr(accid, CHATMAIL_QR)
    return accid


@pytest.fixture(scope="session")
def user_accid(user_rpc):
    accid = user_rpc.add_account()
    user_rpc.set_config(accid, "displayname", "TestUser")
    user_rpc.add_transport_from_qr(accid, CHATMAIL_QR)
    return accid


@pytest.fixture(scope="session")
def reports_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("reports")


@pytest.fixture(scope="session", autouse=True)
def running_bot(bot_rpc, bot_accid, reports_dir):
    import self_reporting_bot
    self_reporting_bot.REPORTS_DIR = reports_dir

    from self_reporting_bot import cli
    bot = Bot(bot_rpc, cli._hooks)

    t = threading.Thread(target=bot.run_forever, args=(bot_accid,), daemon=True)
    t.start()
    yield bot


@pytest.fixture(scope="session")
def chat_id_with_bot(bot_rpc, bot_accid, user_rpc, user_accid):
    """A chat between user and bot with keys already exchanged."""

    qr = bot_rpc.get_chat_securejoin_qr_code(bot_accid, None)

    chat_id = user_rpc.secure_join(user_accid, qr)

    wait_for_event(
        user_rpc,
        EventType.SECUREJOIN_JOINER_PROGRESS,
        predicate=lambda e: e.progress == 1000,
    )

    return chat_id