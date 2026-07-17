# PDF parity foundation

The first Stage 4 slice proves the export boundary without pretending that Stage 1 text placeholders are production typography.

## Current contract

`pydesign.pdf.export_layout_pdf()` consumes the same schema-versioned display list as the canvas. Before publishing it:

1. validates document/page/operation structure and finite physical dimensions;
2. rejects unknown operations and all `text_placeholder` operations;
3. writes rectangles and cubic paths through a project-owned ReportLab adapter using the document's top-left coordinate system;
4. reopens the temporary PDF with pikepdf and verifies page count and every MediaBox;
5. hashes the exact PDF bytes and writes a deterministic build manifest;
6. replaces the requested output only after writing and inspection succeed.

The ReportLab invariant mode makes an identical display list byte-deterministic. The manifest records source revision, document identity, page sizes, operation counts, writer/inspector authorities and PDF SHA-256. Failure-injection tests prove that preflight, writer or inspection failure leaves an older PDF untouched.

## CLI

```bash
python -m pip install -e '.[pdf]'
pydesign build-pdf project --output publication.pdf
```

The default manifest path is `publication.pdf.manifest.json`; `--manifest` may choose another path.

## Parity gate still open

This is a vector proof slice, not the Stage 4 exit. Searchable shaped glyph placement, subset embedding, ToUnicode, images, transforms, clipping/transparency, Poppler difference views and proof/preflight commands remain. Until the shared typography display operation exists, refusing text is the only honest parity behavior.
