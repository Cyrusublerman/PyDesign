# Third-party dependency register

This file records intended runtime dependencies before they are introduced into a release bundle. Exact installed versions and notices will be generated during release builds.

| Component | Role | Licence family | Stage |
|---|---|---|---|
| CPython | Runtime | PSF | 0 |
| PySide6 / Qt | Desktop GUI | LGPL-3.0-only / commercial options | 1 |
| LibCST | Visible Python source transactions | MIT | 2 |
| ICU / PyICU | Unicode boundaries and bidi | Unicode-3.0 | 3 |
| HarfBuzz / uharfbuzz | OpenType shaping | MIT | 3 |
| FreeType / freetype-py | Font raster metrics | FTL or GPL-2.0 | 3 |
| FontTools | Font parsing, outlines and subsetting | MIT | 3 |
| Pyphen and dictionaries | Hyphenation | LGPL-2.1+ and dictionary-specific | 3 |
| ReportLab | Initial PDF writer adapter | BSD-3-Clause | 4 |
| pikepdf / qpdf | PDF assembly and inspection | MPL-2.0 / Apache-2.0 | 4 |
| Poppler | Local PDF proof rasterisation | GPL-2.0-or-later | 4 |
| Pillow / LittleCMS | Images and colour management | HPND / MIT | 6 |

This is a planning register, not a substitute for the exact SPDX inventory and legal review required by the release gate.

