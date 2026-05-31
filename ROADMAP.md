# notenix Roadmap

This document describes the intended direction for notenix and the Kanal settings app. It is a living document — items move, get dropped, or get replaced as priorities change.

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Shipped |
| 🔄 | In progress |
| 📋 | Planned — requirements clear, not yet started |
| 💡 | Idea — direction agreed, details open |
| 🔬 | Proposal — worth exploring, no commitment |

---

## Completed

### System
- ✅ Automatic daily updates (systemd timer + nixos-rebuild)
- ✅ Atomic rollback via NixOS generations
- ✅ Hardware graphics enabled unconditionally (AMD / Intel / NVIDIA)
- ✅ Swap: 4 GiB swapfile + zram/zstd, enabled by default

### Kanal app
- ✅ Channel / preset / activation mode selection
- ✅ Machine identity settings (hostname, user, timezone, locale, keyboard)
- ✅ Feature toggles (SSH, Kiosk, Swap, NVIDIA, Steam, Tailscale, …)
- ✅ Live log panel during rebuild
- ✅ Release update checker with install flow
- ✅ Experimental branch selection (main / unstable / feat/*)
- ✅ GNOME extension side-effects wired to feature toggles
- ✅ Feature catalog defaults respected — `default: true` features show as enabled on fresh machines
- ✅ GitHub API authentication (GITHUB_TOKEN) to avoid rate limiting
- ✅ Branch dropdown correctly restores selected branch after rebuild

---

## Near-term

### System

- 📋 **Installer improvements** — guided disk partitioning, ZFS option, clearer error messages
- 📋 **Printer auto-detection** — surface available network printers in Kanal without needing CUPS UI
- 📋 **Flatpak app management in Kanal** — install / remove user Flatpaks from the Apps tab

### Kanal app

- 📋 **Per-feature descriptions** — expand the subtitle in the Features tab to a detail panel with what the feature actually does on the system (ports opened, services started, etc.)
- 📋 **Rollback from UI** — list available NixOS generations and allow switching back to one with a single click
- 📋 **Update history** — show past rebuilds with timestamps and outcomes in the log panel

---

## Medium-term

### System

- 💡 **Multi-user support** — allow adding/removing additional user accounts through Kanal
- 💡 **Disk usage panel** — show Nix store size, generation count, offer garbage collection
- 💡 **Localisation** — ship Kanal translated into Slovenian (sl) and other languages

### Kanal app

- 💡 **Preset customisation** — allow choosing individual packages within a preset rather than preset-as-atomic-unit
- 💡 **Settings export / import** — export `machine.nix` state as a portable file for cloning to another machine
- 💡 **Offline mode** — degrade gracefully when GitHub API is unreachable (use last-known metadata cache)

---

## Ideas & Proposals

These items have no commitment. They are recorded here to avoid losing them and to provide enough detail to pick up later.

---

### 🔬 Replace `machine.nix` string manipulation with `nix-editor`

**Context**

`machine.py` currently reads and writes `machine.nix` using a set of regex-based string helpers (`_upsert_value`, `_upsert_bool`, `_remove_key`, `_get_value`, `_get_list`, `_upsert_list`). These work but are fragile — edge cases in whitespace, comments, or unusual formatting could silently corrupt the file.

**What `nix-editor` is**

[`nix-editor`](https://github.com/snowfallorg/nix-editor) is a small Rust CLI tool (MIT, ~100 stars) that reads and writes NixOS configuration files at the AST level using [`rnix-parser`](https://github.com/nix-community/rnix-parser). It preserves all formatting and comments and cannot produce syntactically invalid output.

```
nix-editor <FILE> <DOTTED.ATTR.PATH> --val <VALUE>   # write / upsert
nix-editor <FILE> <DOTTED.ATTR.PATH> -r              # read raw Nix value
nix-editor <FILE> <DOTTED.ATTR.PATH> --deref         # delete key
nix-editor <FILE> <DOTTED.ATTR.PATH> --inplace       # edit in-place
```

**Tested behaviour against notenix `machine.nix`** (2026-05-31, `github:snowfallorg/nix-editor`):

| Operation | Command | Result |
|---|---|---|
| Read existing scalar | `--deref` ... wait, use `-r` | Returns raw Nix value (`"desktop"`, `true`) |
| Read missing key | `-r` on absent attr | Exits 1 with error — needs `try/except` around subprocess |
| Write / upsert scalar | `--val true` | Creates or updates the line correctly |
| Write new key on empty `{ lib, ... }: {}` | `--val true` | Inserts correctly inside the braces |
| Delete key | `--deref` | Removes the line cleanly |
| Write full list with `lib.mkForce` | `--val 'lib.mkForce [ "a" "b" ]'` | Works — kanal already builds full list before write |
| Add element to existing `lib.mkForce` list | `--arr "x"` | **Fails** — nix-editor can't modify `lib.mkForce` wrapped lists via `--arr` |

> Note: `--deref` is delete, not read. Use `-r` (no `--val`) to read.

**What would change in kanal**

Replace ~120 lines in `machine.py`:
```
_upsert_value / _upsert_bool / _remove_key / _get_value / _get_list / _upsert_list
_load_machine / _write_machine
```

With ~30 lines of subprocess wrappers:
```python
NIX_EDITOR_BIN = os.environ.get("NIX_EDITOR_BIN", "nix-editor")

def _ne_read(key: str) -> str | None:
    """Return raw Nix value string or None if key absent."""
    r = subprocess.run([NIX_EDITOR_BIN, str(_const.MACHINE_PATH), key, "-r"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

def _ne_write(key: str, value: str) -> None:
    """Write/upsert a value. value is a raw Nix expression string."""
    subprocess.run([NIX_EDITOR_BIN, str(_const.MACHINE_PATH), key,
                    "--val", value, "--inplace"], check=True)

def _ne_delete(key: str) -> None:
    """Remove key from machine.nix. No-op if absent."""
    r = subprocess.run([NIX_EDITOR_BIN, str(_const.MACHINE_PATH), key, "--deref", "--inplace"],
                       capture_output=True)
    # exit 1 = key not found, that's fine
```

`read_features()` becomes a loop of `_ne_read` calls. `save_features()` calls `_ne_write` or `_ne_delete` per key.

**What needs to change in `flake.nix`**

Add `nix-editor` to the `makeWrapper` `--prefix PATH` for both `kanal` and `kanalctl` packages:

```nix
# In pkgs/kanal/flake.nix (or wherever makeWrapper is called)
makeWrapper ${pkgs.nix-editor}/bin/nix-editor  # add to PATH deps
# and set NIX_EDITOR_BIN or rely on PATH lookup
```

`nix-editor` is available in nixpkgs as `pkgs.nix-editor`.

**Trade-offs**

| | Current (regex) | With nix-editor |
|---|---|---|
| Code size | ~120 lines | ~30 lines |
| Correctness | Regex — can break on unusual formatting | AST — structurally correct always |
| Dependency | None (stdlib only) | `nix-editor` runtime binary |
| Performance | Single string pass | One subprocess per key (~10–15 on save) |
| Maturity | Known-working in production | Small project, actively maintained |
| `lib.mkForce` lists | Full list write via regex | Full list write via `--val` (same approach) |

**Recommendation**: adopt when `machine.py` next needs significant changes, or if a regex bug is found in production. Not urgent given current code works correctly.

---


### GUI installer replacing the text-based one

TODO

## Out of scope

These are currently not planned:
- **Remote management / fleet control** — notenix is designed for single-machine personal use
- **Package manager UI** — Flatpak via GNOME Software covers this
