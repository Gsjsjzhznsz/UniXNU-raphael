# Preserved development workspace

This directory contains the public host scripts, fixtures, tests, documentation and exact source/tool locks used by the raphael bring-up. The standard device layout remains at the repository root; shared hardware code is in `UniXNU-sm8150-common`.

The original scripts expect a containing workspace with `scripts/`, `tests/`, `docs/`, `UniXNU-raphael`, `UniXNU-sm8150-common` and `sources/`. On Linux or WSL, restore that layout without editing the scripts:

```sh
# Run from the directory containing both cloned repositories.
DEVICE="$(realpath UniXNU-raphael)"
SOC="$(realpath UniXNU-sm8150-common)"
WORK="$PWD/raphael-workspace"
mkdir -p "$WORK"
cp -a "$DEVICE/development/." "$WORK/"
ln -s "$DEVICE" "$WORK/UniXNU-raphael"
ln -s "$SOC" "$WORK/UniXNU-sm8150-common"
ln -s UniXNU-raphael/package/firmware "$WORK/uefi-raphael"
```

Place separately obtained upstream sources at `$WORK/sources/`, using the exact commits in `sources.lock.json`. Packaging additionally uses the separate runtime pin in `board.toml`. Configure the ignored device `local.toml` from its example for this layout. Scripts that build diagnostic handset images also require the owner's private storage ABI, signed extent/root policies and original OS inputs described in the handoff. Those inputs and historical private artifact paths are intentionally unavailable in a public checkout.

Run checks from `$WORK`; for example:

```sh
cd "$WORK"
python3 scripts/check_repository_layout.py
python3 sources/UniXNU/scripts/porting-record.py check --device UniXNU-raphael
```

The source snapshot preserves diagnostic functionality; it does not claim that a fresh checkout alone can produce a complete production phone image. Do not treat historical `artifacts/` or `evidence/private/` references in the documents as downloadable files.
