"""kanal.metadata — channel/preset metadata: defaults, cache, and refresh.

This module is the single source of truth for the channel→flake-URL and
channel→preset mapping.  It is read-only with respect to the NixOS config
files; all writes go through nixfiles and machine modules.

Public API
----------
Status              dataclass holding the current system state
load_metadata()     returns cached or built-in metadata dict
is_cache_stale()    True if the cache is missing or older than N hours
refresh_metadata()  fetches fresh data from GitHub + nix eval, updates cache
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import kanal.constants as _const

# ---------------------------------------------------------------------------
# Cache location
# ---------------------------------------------------------------------------

METADATA_CACHE = Path("~/.cache/kanal/metadata.json").expanduser()

# ---------------------------------------------------------------------------
# Built-in defaults (used when the cache is absent and GitHub is unreachable)
# ---------------------------------------------------------------------------

_DEFAULT_PRESETS: list[dict] = [
    {"id": "desktop",      "label": "Desktop",
     "subtitle": "Full desktop with Flatpak, sound, bluetooth, printing"},
    {"id": "desktop-lite", "label": "Desktop Lite",
     "subtitle": "Lightweight desktop with sound, bluetooth, printing"},
    {"id": "minimal",      "label": "Minimal",
     "subtitle": "No desktop, essentials only"},
]

_DEFAULT_METADATA: dict = {
    "flakeBase": _const.FLAKE_REF,
    "channels": {
        "stable":   {"flake": _const.FLAKE_REF,                         "label": "Stable releases",
                     "default": True,  "experimental": False, "presets": _DEFAULT_PRESETS},
        "main":     {"flake": f"{_const.FLAKE_REF}/main",              "label": "main (branch)",
                     "default": False, "experimental": True,  "presets": _DEFAULT_PRESETS},
        "unstable": {"flake": f"{_const.FLAKE_REF}/unstable",          "label": "unstable (branch)",
                     "default": False, "experimental": True,  "presets": _DEFAULT_PRESETS},
    },
}

# ---------------------------------------------------------------------------
# Status dataclass
# ---------------------------------------------------------------------------

@dataclass
class Status:
    """Snapshot of the currently configured channel, preset, and operation."""

    channel:        str   # e.g. "main" | "unstable"
    flake_output:   str   # full flake URL for this channel
    preset:         str   # e.g. "desktop" | "minimal"
    operation:      str   # "boot" | "switch"
    overrides_path: str   # path to machine.nix

    def to_dict(self) -> dict:
        return {
            "channel":        self.channel,
            "flake_output":   self.flake_output,
            "preset":         self.preset,
            "operation":      self.operation,
            "overrides_path": self.overrides_path,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def load_metadata() -> dict:
    """Return metadata from the local cache, or built-in defaults if missing."""
    if METADATA_CACHE.exists():
        try:
            return json.loads(METADATA_CACHE.read_text())
        except Exception:
            pass
    return _DEFAULT_METADATA


def is_cache_stale(hours: float = 24) -> bool:
    """Return True if the cache is missing or older than *hours*."""
    if not METADATA_CACHE.exists():
        return True
    age = time.time() - METADATA_CACHE.stat().st_mtime
    return age > hours * 3600

# ---------------------------------------------------------------------------
# Metadata accessors
# ---------------------------------------------------------------------------

def channels() -> dict[str, str]:
    """Return ``{channel_id: flake_url}`` from the current metadata."""
    return {k: v["flake"] for k, v in load_metadata()["channels"].items()}


def presets_for(channel: str | None = None) -> list[str]:
    """Return preset ids for *channel* (or the default channel)."""
    ch_map = load_metadata()["channels"]
    if channel is None:
        channel = next(
            (k for k, v in ch_map.items() if v.get("default")),
            next(iter(ch_map), ""),
        )
    ch_data = ch_map.get(channel, {})
    return [p["id"] for p in ch_data.get("presets", _DEFAULT_PRESETS)]

# ---------------------------------------------------------------------------
# Refresh (network + nix eval — run in a background thread)
# ---------------------------------------------------------------------------

def _fetch_github_branches(owner_repo: str) -> tuple[list[str], str]:
    """Return ``(branch_names, default_branch)`` from the GitHub API."""
    _token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": f"Bearer {_token}"} if _token else {}),
    }
    repo_url   = f"https://api.github.com/repos/{owner_repo}"
    branch_url = f"https://api.github.com/repos/{owner_repo}/branches?per_page=100"

    req = urllib.request.Request(repo_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            repo_info = json.loads(resp.read())
    except Exception:
        repo_info = {}
    default_branch = repo_info.get("default_branch", "main")

    req = urllib.request.Request(branch_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            branches = [b["name"] for b in json.loads(resp.read())]
    except Exception:
        branches = []

    return branches, default_branch


def _fetch_branch_presets(flake_url: str, fallback: list) -> list:
    """Run ``nix eval`` to get presets from *flake_url*; returns *fallback* on error."""
    try:
        result = subprocess.run(
            [str(_const.NIX_BIN), "eval", "--json", "--refresh",
             f"{flake_url}#lib.kanal.presets"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return fallback


def refresh_metadata(callback=None) -> None:
    """Fetch fresh metadata from GitHub and ``nix eval``; update the cache.

    Discovers branches via the GitHub API and fetches presets for each branch.
    Falls back to cached or built-in defaults if anything fails.
    Always calls ``callback(metadata)`` when done (even on error).
    """
    try:
        current    = load_metadata()
        flake_base = current.get("flakeBase", _const.FLAKE_REF)
        fallback   = _DEFAULT_PRESETS

        owner_repo            = "/".join(flake_base.split(":", 1)[-1].split("/")[:2])
        branches, default_br  = _fetch_github_branches(owner_repo)

        ch_map = {}
        # Stable release-tracking channel (not experimental)
        stable_presets = _fetch_branch_presets(flake_base, fallback)
        ch_map["stable"] = {
            "flake":        flake_base,
            "label":        "Stable releases",
            "default":      True,
            "experimental": False,
            "presets":      stable_presets,
        }
        # Branch-tracking channels (experimental)
        for branch in branches:
            is_default_branch = (branch == default_br)
            flake_url  = flake_base if is_default_branch else f"{flake_base}/{branch}"
            presets    = _fetch_branch_presets(flake_url, fallback)
            ch_map[branch] = {
                "flake":        flake_url,
                "label":        f"{branch} (branch)",
                "default":      False,
                "experimental": True,
                "presets":      presets,
            }

        data = {"flakeBase": flake_base, "channels": ch_map}
        METADATA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        METADATA_CACHE.write_text(json.dumps(data, indent=2))
        if callback:
            callback(data)
    except Exception:
        if callback:
            callback(load_metadata())
