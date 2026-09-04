# Version Registry

> `versions.json` is the machine-readable source of truth. Update it first, then update this table and rebuild HTML/PDF.

## Current versions

| Component | Version | Date / Pin | Source of truth |
|---|---:|---|---|
| Quick Start document | 1.4.1 | 2026-09-04 | `versions.json` → `document` |
| `apply-holmes-patch` scripts | 1.1.1 | commit `b244576e48206f3ade97cac5d0b8125033970c66` | `versions.json` → `patch_scripts` |
| `wiki-companion` plugin | 1.0.0 | 2026-09-04 | External companion; not included in this repository |
| Hermes-Wiki schema | 1.0.0 | 2026-09-04 | External companion; not included in this repository |

## Document history

| Version | Date | Main changes |
|---|---|---|
| 1.4.1 | 2026-09-04 | Reject credential-bearing remote URLs before logging; avoid persistent remote changes |
| 1.4.0 | 2026-09-04 | Public-release privacy sanitization, stable pinned deployment, reproducible build dependency |
| 1.3.0 | 2026-09-04 | Obsidian/Hermes-Wiki, human-work structure, immediate/candidate capture policy, Wiki hook, centralized version manifest |
| 1.2.0 | 2026-09-03 | Holmes patch deployment, rollback, and three-layer verification |
| 1.1.0 | 2026-09-03 | Initial Windows/Orca/Codex/Hermes guide |

## Release procedure

1. Update versions and pinned SHAs in `versions.json`.
2. Keep `PATCH_VERSION` in `scripts/apply-holmes-patch.py` equal to the manifest.
3. Update README content and the visible cover version.
4. Run `python build.py`; confirm HTML contains the current manifest version.
5. Render PDF from the generated HTML.
6. Extract PDF text and confirm the version, new headings, and critical commands.
7. Visually inspect pages containing changed sections.
8. Run `python scripts/apply-holmes-patch.py --version` and plugin Doctor.

Do not claim a release is complete when README, HTML, PDF, patch scripts, and `versions.json` disagree.
