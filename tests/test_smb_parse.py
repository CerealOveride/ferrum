"""Tests for SMB path parsing helpers."""

from ferrum.backends.smb import parse_smb_url, smb_path


def test_parse_smb_url_host_share_path():
    host, share, path = parse_smb_url("//nas.local/media/films/2024")
    assert host == "nas.local"
    assert share == "media"
    assert path == "films/2024"


def test_parse_smb_url_share_root():
    host, share, path = parse_smb_url("//nas/share")
    assert host == "nas"
    assert share == "share"
    assert path == ""


def test_parse_smb_url_extra_slashes():
    host, share, path = parse_smb_url("////host/share/a/b")
    assert host == "host"
    assert share == "share"
    assert path == "a/b"


def test_smb_path_builds_unc():
    assert smb_path("host", "share") == r"\\host\share"
    assert smb_path("host", "share", "dir/file") == r"\\host\share\dir\file"
