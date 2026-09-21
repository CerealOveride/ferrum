"""Smoke tests for Textual message types."""


def test_smb_auth_required_import_and_fields():
    from ferrum.messages import SMBAuthRequired

    msg = SMBAuthRequired(host="nas.local", share="media", path="//nas.local/media/films")
    assert msg.host == "nas.local"
    assert msg.share == "media"
    assert msg.path == "//nas.local/media/films"


def test_core_messages_importable():
    from ferrum.messages import (
        DirectoryRequested,
        DirectoryLoaded,
        DirectoryError,
        FileSelected,
        FileOpened,
        StatusMessage,
    )

    assert DirectoryRequested("/tmp").path == "/tmp"
    assert DirectoryError("/x", "boom").error == "boom"
    assert FileSelected("/f").path == "/f"
    assert FileOpened("/f").path == "/f"
    assert StatusMessage("ok").text == "ok"
    assert DirectoryLoaded("/tmp", []).entries == []
