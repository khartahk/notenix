"""kanal.releases — check for notenix releases on GitHub.

Compares the installed kanal version (from package metadata, baked in at
build time from pyproject.toml) against the latest GitHub release.

Public API
----------
check_update()   -> list[dict] | None
    Returns a list of release dicts (tag_name, body, published_at) that are
    newer than the installed version, or None on network/parse failure.
    Uses a local cache with ETag-based revalidation — no data transferred
    when nothing has changed on the server.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from packaging.version import InvalidVersion, Version

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

def get_installed_version() -> Version | None:
    """Return the installed kanal package version, or None if not installed."""
    try:
        return Version(version("kanal"))
    except (PackageNotFoundError, InvalidVersion):
        return None


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

def check_update() -> list[dict] | None:
    """Return releases newer than the installed version, newest first.

    Returns an empty list if up-to-date, None on unrecoverable error
    (no network, package not installed, etc.).
    """
    installed = get_installed_version()
    if installed is None:
        return None  # running from source without install — skip

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
        if rel_version > installed and not rel.get("prerelease", False):
            newer.append({
                "tag_name":     tag,
                "body":         rel.get("body") or "",
                "published_at": rel.get("published_at", ""),
            })

    # Sort newest first
    newer.sort(key=lambda r: Version(r["tag_name"].lstrip("v")), reverse=True)
    return newer
