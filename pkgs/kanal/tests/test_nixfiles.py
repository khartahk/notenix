"""Tests for kanal.nixfiles — pure string-manipulation functions.

These tests require no root, no GTK, and no running NixOS system.
"""

from __future__ import annotations

import pytest

from kanal.nixfiles import (
    _get_flake_url,
    _get_value,
    _remove_key,
    _set_flake_url,
    _upsert_bool,
    _upsert_value,
)

# ---------------------------------------------------------------------------
# _get_flake_url / _set_flake_url
# ---------------------------------------------------------------------------

SAMPLE_FLAKE = """\
{
  inputs.notenix.url = "github:n1x05/notenix";
  outputs = { notenix, ... }: {
    nixosConfigurations.notenix =
      notenix.lib.mkMachineSystem { modules = [ ./machine.nix ]; };
  };
}
"""


def test_get_flake_url_extracts_url():
    assert _get_flake_url(SAMPLE_FLAKE) == "github:n1x05/notenix"


def test_get_flake_url_missing_returns_none():
    assert _get_flake_url("{ }") is None


def test_set_flake_url_patches_existing():
    updated = _set_flake_url(SAMPLE_FLAKE, "github:n1x05/notenix/unstable")
    assert 'inputs.notenix.url = "github:n1x05/notenix/unstable"' in updated
    # Original URL must be gone
    assert '"github:n1x05/notenix";' not in updated


def test_set_flake_url_roundtrip():
    patched = _set_flake_url(SAMPLE_FLAKE, "github:n1x05/notenix/unstable")
    assert _get_flake_url(patched) == "github:n1x05/notenix/unstable"


def test_set_flake_url_migrates_old_format():
    old = '{\n  inputs.notenix.url = "github:n1x05/notenix";\n  outputs = { };\n}\n'
    new = _set_flake_url(old, "github:n1x05/notenix/stable")
    assert "nixosConfigurations" in new
    assert "github:n1x05/notenix/stable" in new

# ---------------------------------------------------------------------------
# _get_value / _upsert_value
# ---------------------------------------------------------------------------

SAMPLE_MACHINE = """\
{ lib, ... }:
{
  notenix.preset = lib.mkForce "desktop";
  notenix.system.autoupgrade.operation = lib.mkForce "boot";
}
"""


def test_get_value_existing():
    assert _get_value(SAMPLE_MACHINE, "notenix.preset") == "desktop"


def test_get_value_missing():
    assert _get_value(SAMPLE_MACHINE, "notenix.features.ssh") is None


def test_upsert_value_updates_existing():
    result = _upsert_value(SAMPLE_MACHINE, "notenix.preset", "minimal")
    assert _get_value(result, "notenix.preset") == "minimal"
    assert result.count("notenix.preset") == 1


def test_upsert_value_inserts_new():
    result = _upsert_value(SAMPLE_MACHINE, "notenix.features.ssh", "true")
    assert _get_value(result, "notenix.features.ssh") == "true"

# ---------------------------------------------------------------------------
# _upsert_bool
# ---------------------------------------------------------------------------


def test_upsert_bool_true():
    result = _upsert_bool("{ lib, ... }:\n{\n}\n", "notenix.features.ssh", True)
    assert "lib.mkForce true" in result


def test_upsert_bool_false():
    base   = _upsert_bool("{ lib, ... }:\n{\n}\n", "notenix.features.ssh", True)
    result = _upsert_bool(base, "notenix.features.ssh", False)
    assert "lib.mkForce false" in result

# ---------------------------------------------------------------------------
# _remove_key
# ---------------------------------------------------------------------------


def test_remove_key_removes_existing():
    result = _remove_key(SAMPLE_MACHINE, "notenix.preset")
    assert "notenix.preset" not in result


def test_remove_key_noop_when_absent():
    result = _remove_key(SAMPLE_MACHINE, "notenix.features.kiosk")
    assert result == SAMPLE_MACHINE
