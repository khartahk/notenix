"""kanal.releases — check for notenix releases on GitHub.

Compares the tag currently pinned in the machine's flake.nix
(inputs.notenix.url ?ref=vX.Y.Z) against the latest GitHub release.
Falls back to comparing the installed kanal package version when no tag
is pinned (e.g. branch-tracking channels).

Public API
----------
get_pinned_tag() -> Version | None
    Returns the version currently pinned in flake.nix, or None.
check_update()   -> list[dict] | None
    Returns a list of release dicts (tag_name, body, published_at) that are
    newer than the pinned/installed version, or None on network/parse failure.
    Uses a local cache with ETag-based revalidation — no data transferred
    when nothing has changed on the server.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from packaging.version import InvalidVersion, Version

import re

import kanal.constants as _const

# ---------------------------------------------------------------------------
# GitHub API endpoint
# ---------------------------------------------------------------------------

_RELEASES_URL = "https://api.github.com/repos/n1x05/notenix/releases?per_page=20"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "kanal/notenix",
}

# How long a fresh cache is considered valid without revalidation (seconds).
# ETag revalidation is always attempted regardless; this is the hard TTL for
# offline / unreachable scenarios.
_CACHE_TTL_SECS = 6 * 3600  # 6 hours


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

def get_pinned_tag() -> Version | None:
    """Return the tag version currently pinned in flake.nix, or None.

    Reads ``inputs.notenix.url`` and extracts the ``?ref=vX.Y.Z`` or
    ``/vX.Y.Z`` suffix.  Returns None when tracking a branch.
    """
    try:
        from pathlib import Path
        text = _const.LOCAL_FLAKE_PATH.read_text()
        for line in text.splitlines():
            t = line.strip()
            if t.startswith("inputs.notenix.url"):
                m = re.search(r'"[^"]*[/?]ref=(v?[^"&\s]+)"', t) or \
                    re.search(r'"[^"]*/([vV]\d+\.\d+[^"]*)"', t)
                if m:
                    return Version(m.group(1).lstrip("v"))
    except Exception:
        pass
    return None


def get_installed_version() -> Version | None:
    """Return the installed kanal package version, or None if not installed.

    Set KANAL_VERSION env var to override (useful for dev testing the banner).
    """
    override = os.environ.get("KANAL_VERSION")
    if override:
        try:
            return Version(override)
        except InvalidVersion:
            pass
    try:
        return Version(version("kanal"))
    except (PackageNotFoundError, InvalidVersion):
        return None


def _current_version() -> Version | None:
    """Return pinned tag if set, else installed kanal version."""
    return get_pinned_tag() or get_installed_version()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache() -> dict | None:
    """Load the releases cache file, returning None if absent or corrupt."""
    try:
        return json.loads(_const.RELEASES_CACHE.read_text())
    except Exception:
        return None


def _save_cache(releases: list[dict], etag: str | None, fetched_at: float) -> None:
    _const.RELEASES_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _const.RELEASES_CACHE.write_text(
        json.dumps(
            {"releases": releases, "etag": etag, "fetched_at": fetched_at},
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Network fetch
# ---------------------------------------------------------------------------

def _fetch_releases(etag: str | None) -> tuple[list[dict] | None, str | None]:
    """Fetch releases from GitHub.

    Sends ``If-None-Match`` when an ETag is available so GitHub can return
    304 Not Modified with no body — zero bandwidth cost when nothing changed.

    Returns:
        (releases, new_etag)  — releases is None on 304 (use cached data)
    """
    headers = dict(_HEADERS)
    if etag:
        headers["If-None-Match"] = etag

    req = urllib.request.Request(_RELEASES_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            new_etag = resp.headers.get("ETag")
            releases = json.loads(resp.read().decode())
            return releases, new_etag
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return None, etag  # Not Modified — caller uses cached data
        return None, None
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_releases() -> list[dict]:
    """Return all non-draft, non-prerelease releases from cache, newest first.

    Falls back to empty list when cache is absent or unreadable.
    """
    cache = _load_cache()
    if not cache:
        return []
    result = []
    for rel in cache.get("releases", []):
        if rel.get("draft") or rel.get("prerelease"):
            continue
        tag = rel.get("tag_name", "")
        try:
            Version(tag.lstrip("v"))
        except InvalidVersion:
            continue
        result.append({
            "tag_name":     tag,
            "published_at": rel.get("published_at", ""),
        })
    result.sort(key=lambda r: Version(r["tag_name"].lstrip("v")), reverse=True)
    return result


def check_update() -> list[dict] | None:
    """Return releases newer than the pinned/installed version, newest first.

    Compares the tag in flake.nix (inputs.notenix.url ?ref=vX.Y.Z) against
    GitHub releases.  Falls back to the kanal package version when no tag is
    pinned (branch-tracking channels).

    Returns an empty list if up-to-date, None on unrecoverable error.
    """
    current = _current_version()
    if current is None:
        return None

    cache = _load_cache()
    now = time.time()

    etag = cache.get("etag") if cache else None
    cached_releases = cache.get("releases") if cache else None
    fetched_at = cache.get("fetched_at", 0) if cache else 0

    # Re-fetch if cache is stale (beyond TTL) or we have no data at all.
    # ETag revalidation happens on every call regardless of TTL so we never
    # use stale data when the server has something new.
    if cached_releases is None or (now - fetched_at) > _CACHE_TTL_SECS:
        fetched, new_etag = _fetch_releases(etag)
        if fetched is not None:
            # Fresh data received
            cached_releases = fetched
            etag = new_etag
            _save_cache(cached_releases, etag, now)
        elif cached_releases is None:
            return None  # no cache + no network
        # else: 304 Not Modified — keep using cached_releases, don't update fetched_at

    newer: list[dict] = []
    for rel in cached_releases:
        tag = rel.get("tag_name", "")
        try:
            rel_version = Version(tag.lstrip("v"))
        except InvalidVersion:
            continue
        if rel_version > current and not rel.get("prerelease", False) and not rel.get("draft", False):
            newer.append({
                "tag_name":     tag,
                "body":         rel.get("body") or "",
                "published_at": rel.get("published_at", ""),
            })

    # Sort newest first
    newer.sort(key=lambda r: Version(r["tag_name"].lstrip("v")), reverse=True)
    return newer
