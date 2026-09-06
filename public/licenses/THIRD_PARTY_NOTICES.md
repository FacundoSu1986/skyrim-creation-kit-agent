# Third-party notices — Discovery Desk

Reviewed 2026-09-06. The repository MIT license applies only to material the
licensor has authority to license. External software, data, fonts and quotations
retain their own rights and licenses. This document is an attribution index and
distribution guide, not a substitute for upstream license files or a release audit.

## Direct application dependencies

Versions refer to the committed package-lock.json, not a potentially stale local install.

| Package | Version | License | Upstream / attribution source |
| --- | --- | --- | --- |
| dotenv | 17.4.2 | MIT | [Mot / dotenv contributors](https://github.com/motdotla/dotenv) |
| drizzle-orm | 0.45.2 | Apache-2.0 | [Drizzle Team and contributors](https://github.com/drizzle-team/drizzle-orm) |
| next | 16.3.4 | MIT | [Vercel and Next.js contributors](https://github.com/vercel/next.js) |
| pg | 8.23.0 | MIT | [Brian Carlson and node-postgres contributors](https://github.com/brianc/node-postgres) |
| react / react-dom | 19.2.8 | MIT | [Meta Platforms and React contributors](https://github.com/facebook/react) |

These descriptive credits do not replace the exact copyright statements shipped
with each package. Preserve those statements and license texts with redistributed
copies. For Apache-2.0 material, preserve applicable NOTICE content and identify
modifications as required by the license.

The complete lockfile metadata inventory, including development and optional
platform dependencies, is in `docs/research/npm-license-inventory.md` in the source
repository. It includes permissive licenses as well as the following components:

| Component | License | Scope and obligations to review |
| --- | --- | --- |
| [sharp](https://github.com/lovell/sharp) / [libvips](https://github.com/libvips/libvips) | Apache-2.0 / LGPL-3.0-or-later; package expressions vary | Optional runtime/native packages. Preserve actual notices and satisfy applicable LGPL source and replacement/relinking provisions when redistributing. Inspect each platform's binaries and embedded libraries. |
| [Lightning CSS](https://github.com/parcel-bundler/lightningcss) | MPL-2.0 | Development tool. Preserve notices and make covered source available as required when distributing the covered software. Generated CSS is not automatically MPL licensed. |
| [axe-core](https://github.com/dequelabs/axe-core) | MPL-2.0 | Development dependency via lint tooling. Review redistribution of axe code, rather than assuming it ships to website visitors. |
| [caniuse-lite](https://github.com/browserslist/caniuse-lite) | CC-BY-4.0 | Browser compatibility data derived from Can I Use, by Alexis Deveria and contributors. Preserve supplied attribution, copyright/license information and identify modifications when sharing covered data. [License](https://github.com/browserslist/caniuse-lite/blob/main/LICENSE). |

Listing a dependency does not mean all optional platforms or development packages
ship in a release. An MIT core can use LGPL/MPL components subject to their terms;
this does not automatically license the entire application under GPL.

## Fonts distributed with the web application

`next/font/google` downloads and self-hosts the fonts used by `src/app/layout.tsx`.
The fonts remain under SIL Open Font License 1.1, not the repository MIT license.

| Family | Copyright notice | Full license |
| --- | --- | --- |
| Fraunces | Copyright 2018 The Fraunces Project Authors (https://github.com/undercasetype/Fraunces) | [Fraunces OFL](fraunces-OFL.txt) |
| IBM Plex Sans | Copyright © 2017 IBM Corp. with Reserved Font Name "Plex" | [IBM Plex Sans OFL](ibmplexsans-OFL.txt) |
| IBM Plex Mono | Copyright © 2017 IBM Corp. with Reserved Font Name "Plex" | [IBM Plex Mono OFL](ibmplexmono-OFL.txt) |

The linked files contain the full upstream copyright and OFL wording, with line
endings normalized to LF. Immutable source URLs, upstream byte hashes and normalized
repository SHA-256 hashes are in [font-sources.json](font-sources.json).
Those records pin the license texts, not the Google Fonts binary responses downloaded
by a build. When updating or distributing fonts, check the actual binary metadata
against these notices and preserve the notices alongside the distributed font files.
Include this entire directory in web deployments and packaged public assets.

## Research sources and prior art

The research identifies [houseCARL](https://github.com/Avick3110/houseCARL),
[SkyrimForge](https://github.com/ShugokiFable/SkyrimForge),
[SkyrimCK-MCP](https://github.com/Pyrhame/SkyrimCK-MCP),
[Mutagen](https://github.com/Mutagen-Modding/Mutagen),
[xEdit](https://github.com/TES5Edit/TES5Edit), and
[CKPE](https://github.com/Perchik71/Creation-Kit-Platform-Extended) as prior art/tools.
See `docs/research/existing-projects.md` and `src/lib/research/sources.ts` for the
research references, including UESP, Creation Kit Wiki and GNU/FSF guidance.
Citation is not permission to copy code, documentation, or assets, and does not
endorse or relicense those projects.

Imported research ZIP provenance remains LEGAL_REVIEW_REQUIRED. The maintainer
reports probable AI generation and no personally written lines, but has not
identified the generator or confirmed third-party inputs. See
`docs/research/source-manifest.md`; no rights clearance is implied by these notices.

## Before distributing an artifact

1. Inventory the actual delivered files, including browser JS/fonts and any native libraries.
2. Keep upstream LICENSE/COPYING/NOTICE files and required attribution; provide covered
   source or other license-required materials where applicable. This index alone is insufficient.
3. Keep these font notices accessible at `/licenses/` and with packaged font assets.
4. Record the artifact/version, included components and evidence of compliance. Dependency
   metadata and this source-only review do not certify an unexamined deployment.

Creation Kit, Skyrim game assets, PapyrusCompiler and vanilla scripts are not licensed
by this repository and must not be bundled. The current Mutagen/CKPE review gates remain
open. This project is unaffiliated with Bethesda, ZeniMax and the tool authors.
