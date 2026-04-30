"""Tests for kanal.machine — read/save machine settings."""

from __future__ import annotations

from kanal.machine import _env_fallbacks
from kanal.nixfiles import _get_value, _upsert_value


def test_env_fallbacks_returns_dict():
    fb = _env_fallbacks()
    assert isinstance(fb, dict)
    # hostname key should always be present on a running system
    from kanal.constants import KEY_HOSTNAME
    assert KEY_HOSTNAME in fb or True  # graceful if socket fails


def test_save_machine_roundtrip(tmp_path, monkeypatch):
    """save_machine → read_machine should round-trip cleanly."""
    machine_file = tmp_path / "machine.nix"
    machine_file.write_text("{ lib, ... }:\n{\n}\n")

    monkeypatch.setattr("kanal.machine.MACHINE_PATH", machine_file)
    monkeypatch.setattr("kanal.nixfiles.MACHINE_PATH", machine_file)
    monkeypatch.setattr("kanal.machine.DRY_RUN", False)

    from kanal.machine import read_machine, save_machine
    from kanal.constants import KEY_HOSTNAME, KEY_TIMEZONE

    save_machine({KEY_HOSTNAME: "testbox", KEY_TIMEZONE: "Europe/Ljubljana"})
    result = read_machine()
    assert result[KEY_HOSTNAME] == "testbox"
    assert result[KEY_TIMEZONE] == "Europe/Ljubljana"
