# RamBlock local source patch

The frozen raphael builds use RamBlock `25c57e0e9b68bf452dd1986914525edc9d2320bc` plus this patch. It preserves the existing sparse zero-write optimization, scratch-buffer short-copy handling, Data solid-state characteristics and their test updates. These changes were already present in the active local component; exporting them adds no new handset behavior.

After obtaining that exact upstream revision, apply from the RamBlock checkout:

```sh
git apply /absolute/path/to/UniXNU-raphael/development/source-patches/RamBlock/0001-sparse-zero-writes-and-solid-state.patch
```

Do this before building the native diagnostic profiles. Preserve any unrelated local changes. Other upstream inputs remain at the existing source locks. Original SPDX and copyright notices are retained.
