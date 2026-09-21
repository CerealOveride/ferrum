"""Tests for path → backend routing."""

from ferrum.backends.local import LocalBackend
from ferrum.backends.router import get_backend_for_path, is_smb_path
from ferrum.backends.smb import SMBBackend


def test_is_smb_path():
    assert is_smb_path("//host/share") is True
    assert is_smb_path(r"\\host\share") is True
    assert is_smb_path("/home/user") is False
    assert is_smb_path("relative") is False


def test_get_backend_local():
    backend = get_backend_for_path("/tmp")
    assert isinstance(backend, LocalBackend)


def test_get_backend_smb():
    backend = get_backend_for_path("//nas.local/media/films")
    assert isinstance(backend, SMBBackend)
    assert backend.connection.host == "nas.local"
    assert backend.connection.share == "media"
