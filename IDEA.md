# Ideas / Parked Work

## IDEA: YAML-driven features.nix generation

**Goal:** Auto-generate the `options.notenix.features` attrset in
`modules/system/features.nix` from `default.yaml` so adding a feature only
requires a YAML entry — no manual Nix edit.

### Scope

Generate **only** the `options.notenix.features` block (each item under the
`bool_options` tab). The `config = mkMerge [...]` block stays hand-written
because config blocks reference `pkgs.*` and arbitrary NixOS options that
can't be derived from YAML.

### Approach

1. Add `kanalctl gen-features` subcommand to `cli.py`.
2. New function `generate_features_options(yaml_path, nix_path)` in e.g.
   `machine.py` or a new `generator.py`.
3. Delimit the generated section with sentinel comments:
   ```nix
   # BEGIN GENERATED — do not edit between these markers
   # END GENERATED
   ```
4. Function reads `default.yaml`, renders each `bool_options` item as:
   ```nix
   <id> = lib.mkOption {
     type        = lib.types.bool;
     default     = false;
     description = "<title>: <subtitle>";
   };
   ```
5. Replaces the region between sentinels in-place (same `_upsert_*` pattern
   used by `nixfiles.py`).
6. `kanalctl gen-features` requires root (writes to `/etc/nixos/`) — wrap with
   `pkexec` like other subcommands, or run manually as part of a dev workflow.

### Risks / open questions

| Risk | Mitigation |
|------|-----------|
| Nix string escaping — subtitles may contain `"`, `$`, `\` | Escape on render: `s.replace("\\", "\\\\").replace('"', '\\"')` |
| Sentinel drift — someone edits file, moves sentinels | Guard: abort if only one sentinel found |
| options/config sync — option added in YAML but config block not updated | Document convention; CI `nix build` catches missing options |
| `pkgs` refs in config blocks — config uses `pkgs.openssh` etc. | Out of scope — config stays manual |
| Two sources of truth diverge — YAML updated, gen not re-run | Add `kanalctl gen-features --check` (diff-only) mode for CI |
| Root required for `/etc/nixos` writes | Same pattern as existing subcommands |

### Open decision

- Should `gen-features` be idempotent/automatic (run on every `kanalctl apply`)
  or a developer-only tool run manually when YAML changes?
- Preference: **manual dev tool** — keeps the apply path simple and avoids
  surprising Nix file mutations during normal upgrades.
