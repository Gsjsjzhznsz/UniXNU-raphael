# Raphael device repository

Read README.md, board.toml, porting.toml, docs/PUBLICATION.zh-CN.md and development/docs/HANDOFF-20261101.zh-CN.md before changing this port. Follow the linked official device-repository, records, drivers, UFS and bring-up guides.

Board code belongs in package/; shared SM8150 operations belong in the pinned UniXNU-sm8150-common feed. Preserve configuration and patch order. Record implementation, host build, image inspection and handset execution separately. The default profile is compile-only. A visible handset desktop has not been verified.

Keep private dumps, device identifiers, owner secrets, firmware and generated images out of Git. Preserve existing local changes and source pins; do not fetch automatically. The development/ directory preserves the former workspace's public orchestration and tests; use its README to restore the expected layout.
