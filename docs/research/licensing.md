# Licensing and legal audit

**PHASE:** 2 (preliminary)  
**STATUS:** Source-backed matrix. Several rows remain `LEGAL_REVIEW_REQUIRED`. This is not legal advice.

## Three different acts

| Act | Meaning | Typical risk |
| --- | --- | --- |
| Execute | Run an installed tool | Use must comply with its license/EULA; path controls do not establish permission |
| Link | Compile/link a library into our process | Obligations depend on the license and whether the result is distributed |
| Distribute | Deliver copies, including browser assets, to others | Preserve notices and satisfy applicable source/redistribution conditions; this project excludes Bethesda files |

These acts are not equivalent. Do not treat “we call xEdit” as “we can ship xEdit”.

## Creation Kit EULA (Steam 1946180)

Retrieved 2026-03-22 from https://store.steampowered.com//eula/1946180_eula_0

**VERIFICADO excerpts:**

- The Editor is licensed, not sold.
- Use is personal non-commercial, or Creations Paid Content.
- You may not reverse engineer, derive source, modify, disassemble, decompile, or create derivative works of the Editor (except where permitted by law).
- Distributed Game Mods grant ZeniMax a broad irrevocable license.
- Mods must state they are not made, guaranteed, or supported by ZeniMax.
- Charging for Game Mods is restricted except Bethesda Creations / written consent.

Implication: an in-process CKPE-style patch of the Editor is `LEGAL_REVIEW_REQUIRED` even if CKPE itself is LGPLv3.

## Matrix

| Component | License | Use | Modify | Distribute | Risk |
| --- | --- | --- | --- | --- | --- |
| Skyrim SE/AE | Proprietary | User’s legal copy as read-only input | No | No | Critical if assets leak into git |
| Creation Kit | ZeniMax EULA | Execute user’s install | EULA forbids RE/modify | No | Critical for in-process hooks |
| steam_api64.dll | Valve / game files | Present because CK needs it | No | No | High if we juggle DLLs |
| CKPE | LGPLv3 (v0.6+) + proprietary blobs | Optional user install | LGPL vs EULA overlay | Do not redistribute | Critical |
| Mutagen / Synthesis / Spriggit | GPL-3.0-only | Preferred headless engine | Allowed under GPL | Source obligation | High product-license impact |
| xEdit | MPL-2.0 (repo); site still says 1.1 | Execute user’s copy | Not required | Do not bundle | Medium |
| LOOT / libloot | GPL-3.0 | Optional later | No | Do not bundle | Medium if linked |
| esper C# | Unconfirmed | Possible MIT-like alternative | After LICENSE read | After LICENSE read | `LEGAL_REVIEW_REQUIRED` |
| esper-js / esper-cpp | MIT | Possible | Allowed | Allowed | Lower |
| PapyrusCompiler + vanilla .psc | Proprietary, ships with CK | Invoke locally | No | No | High if committed |
| FlaUI | MIT | Possible UIA worker | No need | OK | Low license |
| WinAppDriver | Unpublished server | None | Impossible | Do not adopt | Abandoned |

## Fixture rule

Do **not** store `Skyrim.esm`, DLC, vanilla `.psc`, FaceGen, or any Bethesda binary in this repository. Synthetic TES4 headers authored here are acceptable. esper’s own test fixtures require copying game files locally — do not follow that into git.

## Discovery Desk dependencies and notices

The original repository code is MIT licensed. That grant does not relicense dependencies,
fonts, quotations, or material whose rights have not been established.

The [npm inventory](npm-license-inventory.md) records the exact lockfile entries, including
development and optional platform packages. The [third-party notices](../../public/licenses/THIRD_PARTY_NOTICES.md)
cover direct dependencies, non-permissive/transitive license considerations, fonts and prior art.

| Component used by the desk | License in the reviewed source | Distribution considerations |
| --- | --- | --- |
| Next.js, React, React DOM, dotenv, node-postgres | MIT | Preserve applicable copyright and license notices with distributed copies |
| Drizzle ORM / Kit | Apache-2.0 | Preserve license, applicable notices, and change notices where required |
| sharp and platform binaries / libvips | Apache-2.0; LGPL-3.0-or-later; some combined expressions | Optional runtime packages; inspect shipped native libraries and satisfy their actual license/source/relinking requirements |
| lightningcss and axe-core | MPL-2.0 | Development dependencies; source/notice duties apply to covered material actually redistributed, not automatically to generated CSS |
| caniuse-lite | CC-BY-4.0 | Preserve attribution and license information when sharing covered data |
| Fraunces, IBM Plex Sans, IBM Plex Mono | SIL OFL 1.1 | Preserve each font's copyright and OFL text; bundled at `public/licenses/` |

An inventory is not a certification of a release. Before shipping a container, executable,
static export, or web deployment, inspect that artifact, retain upstream license/NOTICE
files, and record how applicable obligations are satisfied. Do not infer obligations
from a package count alone. There is no automatic whole-project GPL conversion from
the mere presence of LGPL or MPL packages.

For existing desk databases, apply the normal `npm run db:migrate` workflow to update
the stored licensing content. Do not force-reseed the research database to apply these corrections.

## Game Mod notice

For Game Mods subject to Creation Kit EULA section 2.B, include the required conspicuous notice:

> THIS MOD IS NOT MADE, GUARANTEED OR SUPPORTED BY ZENIMAX OR ITS AFFILIATES.

The repository's non-affiliation disclaimer is not a replacement for this notice on
future distributed mods. This does not authorize distribution or commercial use of a mod.
See the [official EULA](https://store.steampowered.com/eula/1946180_eula_0).

## Imported research provenance

See the [source manifest and maintainer statement](source-manifest.md). AI generation
does not establish originality, copyright ownership, or permission to reuse third-party
material. The unresolved provenance is `LEGAL_REVIEW_REQUIRED`; this update does not
certify or extend rights over the ZIP contents.

## Mutagen product license strategy

ADR-003 records the owner's technical preference for L3, a separately maintained GPL
worker. The legal determination remains `LEGAL_REVIEW_REQUIRED`; the ADR is still
`PROPOSED`. Separate processes or repositories do not by themselves settle whether a
distributed system is one combined work.

MIT code may be combined with GPL code. A distributed combined work must comply with
the GPL, including corresponding-source and notice requirements; it cannot be offered
under MIT alone. The original MIT portions retain their notices. This compatibility
does not remove the project's existing ADR-003 implementation/distribution gate.
See [ADR-003](../adr/ADR-003-mutagen-runtime-and-license-boundary.md) and
[GNU's compatibility guidance](https://www.gnu.org/licenses/license-compatibility.html).
