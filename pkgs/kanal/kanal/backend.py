"""kanal.backend — file editing and status logic.

This module owns all reads/writes to the overrides file and is the single
source of truth for channel→flake-output mapping.  Neither the GUI nor the
CLI call subprocesses directly for file operations; they go through here.

The nixos-rebuild invocation (privileged) is intentionally kept here too so
both callers share identical argument lists.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOCAL_FLAKE_PATH  = Path("/etc/nixos/flake.nix")
MACHINE_PATH      = Path("/etc/nixos/machine.nix")
LOCAL_FLAKE_ATTR  = "notenix"  # nixosConfigurations.<attr> in the local flake
FLAKE_REPO        = "github:n1x05/notenix"
NIXOS_REBUILD_BIN = Path("/run/current-system/sw/bin/nixos-rebuild")
NIX_BIN           = Path("/run/current-system/sw/bin/nix")

KEY_OP       = "notenix.system.autoupgrade.operation"
KEY_FLAKEREPO = "notenix.system.autoupgrade.flakeRepo"
KEY_PRESET   = "notenix.preset"

KEY_FEATURE_SSH   = "notenix.features.ssh"
KEY_FEATURE_KIOSK = "notenix.features.kiosk"

ALL_FEATURES: list[str] = [KEY_FEATURE_SSH, KEY_FEATURE_KIOSK]

KEY_HOSTNAME    = "notenix.system.install.hostName"
KEY_USERNAME    = "notenix.system.install.userName"
KEY_USERDESC    = "notenix.system.install.userDescription"
KEY_TIMEZONE    = "notenix.system.install.timeZone"
KEY_LOCALE      = "notenix.system.install.locale"
KEY_KBLAYOUT    = "notenix.system.install.keyboardLayout"
KEY_STATEVERSION = "system.stateVersion"

# Injected by the Nix build via makeWrapper --set KANALCTL_BIN <store-path>.
# Falls back to PATH for local development.
_SELF = os.environ.get("KANALCTL_BIN", "kanalctl")

# Flake ref used for nix eval to fetch metadata.  Baked in by the Nix build.
_FLAKE_REF = os.environ.get("KANAL_FLAKE_REF", "github:n1x05/notenix")

# Set KANAL_DRY_RUN=1 to skip all file writes (useful for UI development).
DRY_RUN = os.environ.get("KANAL_DRY_RUN", "") not in ("", "0", "false")

# ---------------------------------------------------------------------------
# Metadata — channels and presets are defined in flake.nix#lib.kanal and
# cached locally so the app works offline.
# ---------------------------------------------------------------------------

METADATA_CACHE = Path("~/.cache/kanal/metadata.json").expanduser()

_DEFAULT_PRESETS = [
    {"id": "desktop",      "label": "Desktop",      "subtitle": "Full desktop with Flatpak, sound, bluetooth, printing"},
    {"id": "desktop-lite", "label": "Desktop Lite", "subtitle": "Lightweight desktop with sound, bluetooth, printing"},
    {"id": "minimal",      "label": "Minimal",      "subtitle": "No desktop, essentials only"},
]

_DEFAULT_METADATA: dict = {
    "flakeBase": "github:n1x05/notenix",
    "channels": {
        "main":     {"flake": "github:n1x05/notenix",          "label": "main",     "default": True,  "presets": _DEFAULT_PRESETS},
        "unstable": {"flake": "github:n1x05/notenix/unstable", "label": "unstable", "default": False, "presets": _DEFAULT_PRESETS},
    },
}


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


def _fetch_github_branches(owner_repo: str) -> tuple[list[str], str]:
    """Return (branch_names, default_branch) from the GitHub API.

    Raises on network / HTTP errors so callers can handle gracefully.
    """
    repo_url    = f"https://api.github.com/repos/{owner_repo}"
    branch_url  = f"https://api.github.com/repos/{owner_repo}/branches?per_page=100"
    headers     = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    req = urllib.request.Request(repo_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        repo_info      = json.loads(resp.read())
    default_branch = repo_info.get("default_branch", "main")

    req = urllib.request.Request(branch_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        branches = [b["name"] for b in json.loads(resp.read())]

    return branches, default_branch


def _fetch_branch_presets(flake_url: str, fallback: list) -> list:
    """Run ``nix eval`` to get presets from a specific branch's flake.

    Returns *fallback* if the eval fails or the key is absent.
    """
    try:
        result = subprocess.run(
            [str(NIX_BIN), "eval", "--json", "--refresh", f"{flake_url}#lib.kanal.presets"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return fallback


def refresh_metadata(callback=None) -> None:
    """Fetch fresh metadata from the GitHub API and update the cache.

    Discovers branches via the GitHub API and fetches presets for each
    branch via ``nix eval <flake>#lib.kanal.presets``. Falls back to cached
    or _DEFAULT_PRESETS if the eval fails.

    Always calls *callback(metadata)* when done.
    """
    try:
        # Use the flakeBase from the current cache if available, else _FLAKE_REF.
        current = load_metadata()
        flake_base      = current.get("flakeBase", _FLAKE_REF)
        fallback_presets = _DEFAULT_PRESETS

        # Discover branches via the GitHub API.
        owner_repo = "/".join(flake_base.split(":", 1)[-1].split("/")[:2])
        branches, default_branch = _fetch_github_branches(owner_repo)

        # Build channel entries, fetching presets from each branch's flake.
        channels = {}
        for branch in branches:
            is_default = (branch == default_branch)
            flake_url  = flake_base if is_default else f"{flake_base}/{branch}"
            presets    = _fetch_branch_presets(flake_url, fallback_presets)
            channels[branch] = {"flake": flake_url, "label": branch, "default": is_default, "presets": presets}

        data = {"flakeBase": flake_base, "channels": channels}
        METADATA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        METADATA_CACHE.write_text(json.dumps(data, indent=2))
        if callback:
            callback(data)
    except Exception:
        if callback:
            callback(load_metadata())


def _meta_channels() -> dict[str, str]:
    """Return {channel_id: flake_url} from the current metadata."""
    return {k: v["flake"] for k, v in load_metadata()["channels"].items()}


def _meta_presets(channel: str | None = None) -> list[str]:
    """Return list of preset ids for *channel* (or the default channel)."""
    channels = load_metadata()["channels"]
    if channel is None:
        channel = next((k for k, v in channels.items() if v.get("default")), next(iter(channels), ""))
    ch_data = channels.get(channel, {})
    return [p["id"] for p in ch_data.get("presets", _DEFAULT_PRESETS)]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Status:
    channel:        str   # "stable" | "unstable"
    flake_output:   str   # full flake URL for this channel
    preset:         str   # "desktop" | "minimal"
    operation:      str   # "boot" | "switch"
    overrides_path: str

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
# File helpers (no root required — read-only)
# ---------------------------------------------------------------------------

def _get_flake_url(contents: str) -> str | None:
    """Extract the notenix input URL from a local flake.nix."""
    for line in contents.splitlines():
        t = line.strip()
        if t.startswith("inputs.notenix.url"):
            m = re.search(r'"([^"]+)"', t)
            if m:
                return m.group(1)
    return None


_CORRECT_OUTPUTS = (
    "  outputs = {{ notenix, ... }}: {{\n"
    "    nixosConfigurations.notenix =\n"
    "      notenix.lib.mkMachineSystem {{ modules = [ ./machine.nix ]; }};\n"
    "  }};\n"
)

_CANONICAL_FLAKE = (
    "{{\n"
    "  inputs.notenix.url = \"{url}\";\n"
    + _CORRECT_OUTPUTS +
    "}}\n"
)


def _has_nixos_configurations(contents: str) -> bool:
    """Return True if the flake already has a nixosConfigurations output."""
    return "nixosConfigurations" in contents


def _set_flake_url(contents: str, url: str) -> str:
    """Patch inputs.notenix.url in a local flake.nix.

    Also rewrites the outputs block to the canonical form if it is missing
    nixosConfigurations (e.g. old machines with the bare mkMachineSystem form).
    """
    # Migrate outputs if needed
    if not _has_nixos_configurations(contents):
        return _CANONICAL_FLAKE.format(url=url)

    # Normal case: just update the URL line
    new_line = f'  inputs.notenix.url = "{url}";'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().startswith("inputs.notenix.url"):
            lines[i] = new_line + "\n"
            return "".join(lines)
    # Not found — insert before first closing brace
    joined = "".join(lines)
    pos = joined.find("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"


def _get_value(contents: str, key: str) -> str | None:
    """Extract the value from a  key = lib.mkForce "value";  line."""
    for line in contents.splitlines():
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            after = t.split("=", 1)[1].strip()
            after = re.sub(r"^lib\.mkForce\s*", "", after)
            return after.strip('" ;')
    return None


def _upsert_value(contents: str, key: str, value: str) -> str:
    """Replace an existing assignment or insert one before the closing }."""
    new_line = f'  {key} = lib.mkForce "{value}";'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            lines[i] = new_line + "\n"
            return "".join(lines)
    # Not found — insert before last }
    joined = "".join(lines)
    pos = joined.rfind("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"


def _upsert_bool(contents: str, key: str, value: bool) -> str:
    """Like _upsert_value but writes a bare Nix boolean (true/false)."""
    nix_val  = "true" if value else "false"
    new_line = f'  {key} = lib.mkForce {nix_val};'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            lines[i] = new_line + "\n"
            return "".join(lines)
    joined = "".join(lines)
    pos = joined.rfind("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"


def _remove_key(contents: str, key: str) -> str:
    """Remove a key assignment (reset to module default)."""
    lines = [
        ln for ln in contents.splitlines(keepends=True)
        if not (ln.strip().startswith(key) and
                ln.strip()[len(key):].lstrip().startswith("="))
    ]
    return "".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _env_fallbacks() -> dict[str, str]:
    """Best-effort values read from the live system environment."""
    import pwd
    import socket
    fallbacks: dict[str, str] = {}
    # hostname
    try:
        fallbacks[KEY_HOSTNAME] = socket.gethostname()
    except Exception:
        pass
    # current user
    try:
        uid = os.getuid()
        pw  = pwd.getpwuid(uid)
        fallbacks[KEY_USERNAME] = pw.pw_name
        fallbacks[KEY_USERDESC] = pw.pw_gecos.split(",")[0] or pw.pw_name
    except Exception:
        pass
    # timezone
    try:
        tz_path = Path("/etc/localtime").resolve()
        # /nix/store/.../zoneinfo/Europe/Ljubljana  or  /usr/share/zoneinfo/...
        for marker in ("zoneinfo/",):
            idx = str(tz_path).find(marker)
            if idx != -1:
                fallbacks[KEY_TIMEZONE] = str(tz_path)[idx + len(marker):]
                break
    except Exception:
        pass
    # locale
    try:
        locale_str = os.environ.get("LANG") or os.environ.get("LC_ALL", "")
        if locale_str:
            fallbacks[KEY_LOCALE] = locale_str
    except Exception:
        pass
    # stateVersion from /etc/os-release
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("VERSION_ID="):
                fallbacks[KEY_STATEVERSION] = line.split("=", 1)[1].strip('"')
                break
    except Exception:
        pass
    return fallbacks


def read_machine() -> dict[str, str]:
    """Return machine-specific settings from machine.nix (no root required)."""
    keys = [KEY_HOSTNAME, KEY_USERNAME, KEY_USERDESC,
            KEY_TIMEZONE, KEY_LOCALE, KEY_KBLAYOUT, KEY_STATEVERSION]
    result = {k: "" for k in keys}
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
        for k in keys:
            v = _get_value(contents, k)
            if v is not None:
                result[k] = v
    # Fill any still-empty field from the live system
    fallbacks = _env_fallbacks()
    for k, v in fallbacks.items():
        if not result.get(k):
            result[k] = v
    return result


# Reasonable locale → XKB layout mapping for auto-suggestion
_LOCALE_TO_KBD: dict[str, str] = {
    "af": "za", "sq": "al", "ar": "ara", "az": "az",
    "be": "by", "bn": "bd", "bs": "ba", "bg": "bg",
    "ca": "es", "cs": "cz", "cy": "gb", "da": "dk",
    "de": "de", "el": "gr", "en_US": "us", "en_GB": "gb",
    "en_AU": "au", "en_CA": "ca", "eo": "epo",
    "es": "es", "es_MX": "latam", "es_AR": "latam",
    "et": "ee", "eu": "es", "fa": "ir", "fi": "fi",
    "fr": "fr", "fr_BE": "be", "fr_CA": "ca",
    "ga": "ie", "gl": "es", "gu": "in",
    "he": "il", "hi": "in", "hr": "hr", "hu": "hu",
    "hy": "am", "id": "us", "is": "is", "it": "it",
    "ja": "jp", "ka": "ge", "kk": "kz", "km": "kh",
    "kn": "in", "ko": "kr", "ky": "kg",
    "lt": "lt", "lv": "lv", "mk": "mk", "ml": "in",
    "mn": "mn", "mr": "in", "ms": "us",
    "nb": "no", "ne": "np", "nl": "nl", "nl_BE": "be",
    "pa": "in", "pl": "pl", "pt": "pt", "pt_BR": "br",
    "ro": "ro", "ru": "ru", "sk": "sk", "sl": "si",
    "sq": "al", "sr": "rs", "sv": "se",
    "ta": "in", "te": "in", "th": "th", "tr": "tr",
    "uk": "ua", "ur": "pk", "uz": "uz",
    "vi": "vn", "zh_CN": "cn", "zh_TW": "tw",
}


def kbd_default_for_locale(locale_str: str) -> str | None:
    """Return a likely XKB layout code for *locale_str* (e.g. 'en_US.UTF-8' → 'us')."""
    # Try progressively shorter prefixes
    for sep in (".", "@", "_"):
        base = locale_str.split(sep)[0]
        if base in _LOCALE_TO_KBD:
            return _LOCALE_TO_KBD[base]
    lang = locale_str[:2]
    return _LOCALE_TO_KBD.get(lang)


def list_locales() -> list[tuple[str, str]]:
    """Return sorted (code, display_label) pairs for all common UTF-8 locales.

    Uses a comprehensive hardcoded list (what the user might *configure*,
    not just what is currently generated on this machine).
    Labels are native-language names so the user can search in their own language.
    """
    # (locale_code, native_display_name)
    _ALL: list[tuple[str, str]] = [
        ("en_US.UTF-8",  "English (US)"),
        ("en_GB.UTF-8",  "English (UK)"),
        ("sl_SI.UTF-8",  "Slovenščina"),
    ]
    _NATIVE: dict[str, str] = {code.split(".")[0]: name for code, name in _ALL}

    # Try the path baked in by the Nix build first, then common fallbacks
    supported_path_str = os.environ.get("KANAL_LOCALE_SUPPORTED", "")
    candidates = (
        [Path(supported_path_str)] if supported_path_str else []
    ) + [
        Path("/run/current-system/sw/share/i18n/SUPPORTED"),
        Path("/usr/share/i18n/SUPPORTED"),
        Path("/etc/locale.gen"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text()
        # Skip the single-line NixOS stub "SUPPORTED-LOCALES=..."
        if text.startswith("SUPPORTED-LOCALES=") and text.count("\n") <= 1:
            continue
        seen: set[str] = set()
        pairs: list[tuple[str, str]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            code = line.split()[0]
            if not code.upper().endswith(".UTF-8") and "/UTF-8" not in line:
                continue
            # Normalise to .UTF-8 suffix
            if "/" in code:
                code = code.split("/")[0]
            if code not in seen:
                seen.add(code)
                base = code.split(".")[0]
                name = _NATIVE.get(base, base)
                pairs.append((code, f"{name}  ({code})"))
        if pairs:
            return sorted(pairs, key=lambda x: x[1].lower())

    # Ultimate fallback: hardcoded list
    return sorted(
        ((code, f"{name}  ({code})") for code, name in _ALL),
        key=lambda x: x[1].lower(),
    )


def list_kbd_layouts() -> list[tuple[str, str]]:
    """Return sorted (code, display_label) pairs from evdev.xml.

    Falls back to symbol filenames if the XML is absent.
    """
    import xml.etree.ElementTree as ET

    xml_candidates = []
    env_xml = os.environ.get("KANAL_XKB_EVDEV_XML", "")
    if env_xml:
        xml_candidates.append(Path(env_xml))
    xml_candidates += [
        Path("/run/current-system/sw/share/X11/xkb/rules/evdev.xml"),
        Path("/usr/share/X11/xkb/rules/evdev.xml"),
    ]

    for xml_path in xml_candidates:
        if not xml_path.exists():
            continue
        try:
            root = ET.parse(xml_path).getroot()
            results: list[tuple[str, str]] = []
            for layout in root.findall(".//layout"):
                ci = layout.find("configItem")
                if ci is None:
                    continue
                name_el = ci.find("name")
                desc_el = ci.find("description")
                if name_el is None or desc_el is None:
                    continue
                code = name_el.text.strip()
                desc = desc_el.text.strip()
                results.append((code, desc))
                # Also add variants
                for variant in layout.findall(".//variant"):
                    vci = variant.find("configItem")
                    if vci is None:
                        continue
                    vn = vci.find("name")
                    vd = vci.find("description")
                    if vn is not None and vd is not None:
                        results.append((
                            f"{code}({vn.text.strip()})",
                            vd.text.strip(),
                        ))
            if results:
                return sorted(results, key=lambda x: x[1].lower())
        except Exception:
            pass

    # Fallback: symbol filenames without descriptions
    xkb_dir = Path("/run/current-system/sw/share/X11/xkb/symbols")
    if xkb_dir.exists():
        codes = sorted(
            f.name for f in xkb_dir.iterdir()
            if f.is_file() and not f.name.startswith(".")
            and f.name not in {"CONTRIBUTORS", "README", "Makefile", "compose"}
        )
        return [(c, c) for c in codes]
    return [("us", "English (US)"), ("gb", "English (UK)"), ("de", "German"),
            ("fr", "French"), ("si", "Slovenian")]


def save_machine(settings: dict[str, str]) -> None:
    """Write machine-specific settings to machine.nix.

    Must be called as root (e.g. via pkexec kanalctl set-machine …).
    settings is a {KEY_*: value} dict; keys absent from the dict are left
    unchanged in the file.
    """
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
    else:
        MACHINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        contents = "{ lib, ... }:\n{\n}\n"

    for key, value in settings.items():
        if value:
            contents = _upsert_value(contents, key, value)

    if DRY_RUN:
        print(f"[kanal dry-run] would write to {MACHINE_PATH}:\n{contents}", flush=True)
        return

    MACHINE_PATH.write_text(contents)


def read_features() -> dict[str, bool]:
    """Return {KEY_FEATURE_*: bool} from machine.nix (no root required)."""
    result = {k: False for k in ALL_FEATURES}
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
        for k in ALL_FEATURES:
            v = _get_value(contents, k)
            if v == "true":
                result[k] = True
    return result


def save_features(features: dict[str, bool]) -> None:
    """Write feature flags to machine.nix. Must be called as root."""
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
    else:
        MACHINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        contents = "{ lib, ... }:\n{\n}\n"

    for key, enabled in features.items():
        if enabled:
            contents = _upsert_bool(contents, key, True)
        else:
            contents = _remove_key(contents, key)

    if DRY_RUN:
        print(f"[kanal dry-run] would write features to {MACHINE_PATH}:\n{contents}", flush=True)
        return
    MACHINE_PATH.write_text(contents)


def pkexec_save_features_stream(features: dict[str, bool], rebuild: bool = True):
    """Invoke ``pkexec kanalctl set-features`` and stream output."""
    if DRY_RUN:
        yield f"[kanal dry-run] set-features: {features!r}\n"
        yield None, 0
        return
    cmd = ["pkexec", _SELF, "set-features"]
    for key, enabled in features.items():
        flag = {
            KEY_FEATURE_SSH:   "--ssh",
            KEY_FEATURE_KIOSK: "--kiosk",
        }.get(key)
        if flag:
            cmd.append(flag if enabled else flag.replace("--", "--no-"))
    if rebuild:
        cmd.append("--rebuild")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode


def read_status() -> Status:
    """Read current channel/operation from the local flake + machine files (no root)."""
    meta     = load_metadata()
    channels = meta["channels"]

    # Determine default channel: first entry marked default=True, else first key.
    default_channel = next(
        (k for k, v in channels.items() if v.get("default")),
        next(iter(channels), "main"),
    )
    default_presets = _meta_presets(default_channel)
    default_preset  = default_presets[0] if default_presets else "desktop"

    channel   = default_channel
    preset    = default_preset
    operation = "boot"

    # Read branch/channel from local flake.nix (inputs.notenix.url)
    if LOCAL_FLAKE_PATH.exists():
        flake_contents = LOCAL_FLAKE_PATH.read_text()
        raw_url = _get_flake_url(flake_contents)
        if raw_url:
            matched = next((k for k, v in channels.items() if v["flake"] == raw_url), None)
            if matched:
                channel = matched

    # Read preset and operation from machine.nix
    if MACHINE_PATH.exists():
        machine_contents = MACHINE_PATH.read_text()
        raw_op     = _get_value(machine_contents, KEY_OP)
        raw_preset = _get_value(machine_contents, KEY_PRESET)

        if raw_op in ("boot", "switch"):
            operation = raw_op
        channel_presets = _meta_presets(channel)
        if raw_preset in channel_presets:
            preset = raw_preset
        elif channel_presets:
            preset = channel_presets[0]

    flake_url = channels.get(channel, {}).get("flake", _FLAKE_REF)
    return Status(
        channel        = channel,
        flake_output   = flake_url,
        preset         = preset,
        operation      = operation,
        overrides_path = str(MACHINE_PATH),
    )


def set_channel(channel: str, operation: str | None = None, preset: str | None = None,
                flake_url: str | None = None) -> None:
    """Write channel to local flake.nix and preset/operation to machine.nix.

    Must be called as root (e.g. via ``pkexec kanalctl set …``).
    Raises ValueError/OSError on failure.
    """
    if operation is not None and operation not in ("boot", "switch"):
        raise ValueError(f"Unknown operation: {operation!r}. Valid: boot, switch")

    # Resolve the flake URL: prefer the explicitly passed URL, fall back to cache.
    if not flake_url:
        channels = _meta_channels()
        if channel not in channels:
            raise ValueError(f"Unknown channel: {channel!r}. Valid: {list(channels)}")
        flake_url = channels[channel]

    # --- Update inputs.notenix.url in /etc/nixos/flake.nix ---
    LOCAL_FLAKE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCAL_FLAKE_PATH.exists():
        flake_contents = LOCAL_FLAKE_PATH.read_text()
    else:
        flake_contents = (
            "{\n"
            "  inputs.notenix.url = \"github:n1x05/notenix\";\n"
            "  outputs = { notenix, ... }: {\n"
            "    nixosConfigurations.notenix =\n"
            "      notenix.lib.mkMachineSystem { modules = [ ./machine.nix ]; };\n"
            "  };\n"
            "}\n"
        )
    flake_contents = _set_flake_url(flake_contents, flake_url)

    # --- Update preset / operation in /etc/nixos/machine.nix ---
    if MACHINE_PATH.exists():
        machine_contents = MACHINE_PATH.read_text()
    else:
        machine_contents = "{ lib, ... }:\n{\n}\n"

    if preset is not None:
        machine_contents = _upsert_value(machine_contents, KEY_PRESET, preset)
    if operation is not None:
        machine_contents = _upsert_value(machine_contents, KEY_OP, operation)
    else:
        machine_contents = _remove_key(machine_contents, KEY_OP)
    # Always pin the auto-upgrade service to the local flake
    machine_contents = _upsert_value(machine_contents, KEY_FLAKEREPO, "github:n1x05/notenix")
    if DRY_RUN:
            print(f"[kanal dry-run] would write to {LOCAL_FLAKE_PATH}:\n{flake_contents}", flush=True)
            print(f"[kanal dry-run] would write to {MACHINE_PATH}:\n{machine_contents}", flush=True)
            return

    LOCAL_FLAKE_PATH.write_text(flake_contents)
    MACHINE_PATH.write_text(machine_contents)


def run_upgrade(channel: str, operation: str) -> tuple[int, str]:
    """Run nixos-rebuild directly against the local flake (already root via pkexec).

    First updates the flake lock file so the latest remote commits are fetched,
    then runs nixos-rebuild with the requested operation.
    Streams combined stdout+stderr to our own stdout so the GUI can capture it.
    Returns (returncode, "").
    """
    import sys as _sys
    flake_dir = str(LOCAL_FLAKE_PATH.parent)
    flake_arg = f"path:/etc/nixos#{LOCAL_FLAKE_ATTR}"

    # Step 1: update the lock file so we pull the latest remote commits.
    print("Updating flake inputs…", flush=True)
    update_proc = subprocess.Popen(
        [str(NIX_BIN), "flake", "update", "--flake", flake_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in update_proc.stdout:
        print(line, end="", flush=True)
    update_proc.wait()
    if update_proc.returncode != 0:
        print(f"nix flake update failed (exit {update_proc.returncode})", flush=True)
        return update_proc.returncode, ""

    # Step 2: rebuild with the now-updated lock file.
    proc = subprocess.Popen(
        [str(NIXOS_REBUILD_BIN), operation, "--flake", flake_arg],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in proc.stdout:
        print(line, end="", flush=True)
    proc.wait()
    return proc.returncode, ""


def pkexec_set(channel: str, operation: str | None, preset: str | None = None,
               flake_url: str | None = None) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl set`` — one password prompt, saves only."""
    if DRY_RUN:
        print(f"[kanal dry-run] pkexec_set({channel!r}, {operation!r}, {preset!r}, url={flake_url!r})", flush=True)
        return 0, ""
    cmd = ["pkexec", _SELF, "set", channel]
    if operation is not None:
        cmd.append(operation)  # positional arg
    if preset is not None:
        cmd += ["--preset", preset]
    if flake_url is not None:
        cmd += ["--flake-url", flake_url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode, r.stderr.strip() or r.stdout.strip()


def pkexec_apply(channel: str, operation: str, preset: str | None = None,
                 flake_url: str | None = None) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl apply`` — one password prompt, saves + upgrades."""
    if DRY_RUN:
        print(f"[kanal dry-run] pkexec_apply({channel!r}, {operation!r}, {preset!r}, url={flake_url!r})", flush=True)
        return 0, ""
    cmd = ["pkexec", _SELF, "apply", channel, operation]
    if preset is not None:
        cmd += ["--preset", preset]
    if flake_url is not None:
        cmd += ["--flake-url", flake_url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stderr.strip() or r.stdout.strip())


def pkexec_apply_stream(channel: str, operation: str, preset: str | None = None,
                        flake_url: str | None = None):
    """Like pkexec_apply but yields (line: str) while running, then (None, rc: int) at the end."""
    if DRY_RUN:
        yield f"[kanal dry-run] pkexec_apply({channel!r}, {operation!r}, {preset!r}, url={flake_url!r})\n"
        yield None, 0
        return
    cmd = ["pkexec", _SELF, "apply", channel, operation]
    if preset is not None:
        cmd += ["--preset", preset]
    if flake_url is not None:
        cmd += ["--flake-url", flake_url]
    import os as _os
    env = _os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode


def pkexec_save_machine(settings: dict[str, str]) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl set-machine ...`` - saves machine.nix only."""
    if DRY_RUN:
        print(f"[kanal dry-run] pkexec_save_machine({settings!r})", flush=True)
        return 0, ""
    cmd = ["pkexec", _SELF, "set-machine"]
    mapping = {
        KEY_HOSTNAME:     "--hostname",
        KEY_USERNAME:     "--username",
        KEY_USERDESC:     "--userdesc",
        KEY_TIMEZONE:     "--timezone",
        KEY_LOCALE:       "--locale",
        KEY_KBLAYOUT:     "--kblayout",
        KEY_STATEVERSION: "--stateversion",
    }
    for key, flag in mapping.items():
        if key in settings and settings[key]:
            cmd += [flag, settings[key]]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, (r.stderr.strip() or r.stdout.strip())


def pkexec_save_machine_stream(settings: dict[str, str]):
    """Invoke ``pkexec kanalctl set-machine --rebuild`` and stream output."""
    if DRY_RUN:
        yield f"[kanal dry-run] pkexec_save_machine({settings!r})\n"
        yield None, 0
        return
    cmd = ["pkexec", _SELF, "set-machine", "--rebuild"]
    mapping = {
        KEY_HOSTNAME:     "--hostname",
        KEY_USERNAME:     "--username",
        KEY_USERDESC:     "--userdesc",
        KEY_TIMEZONE:     "--timezone",
        KEY_LOCALE:       "--locale",
        KEY_KBLAYOUT:     "--kblayout",
        KEY_STATEVERSION: "--stateversion",
    }
    for key, flag in mapping.items():
        if key in settings and settings[key]:
            cmd += [flag, settings[key]]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode
