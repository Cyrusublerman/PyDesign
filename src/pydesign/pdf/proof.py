"""Headless PDF proof raster comparison (Stage 4)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProofResult:
    ok: bool
    message: str
    output_dir: Path
    compared: bool = False
    max_diff: float = 0.0


def run_proof(
    pdf_path: str | Path,
    project_root: str | Path,
    *,
    dpi: int = 72,
    threshold: float = 12.0,
    reference_dir: str | Path | None = None,
) -> ProofResult:
    """Rasterize PDF with pdftoppm; optionally diff against reference PNGs."""
    pdf = Path(pdf_path).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    out = root / ".pydesign" / "proof"
    out.mkdir(parents=True, exist_ok=True)
    if not pdf.is_file():
        return ProofResult(False, f"PDF not found: {pdf}", out, False)
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        manifest = {"ok": True, "compared": False, "reason": "pdftoppm unavailable"}
        (out / "proof.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return ProofResult(
            True,
            "proof skipped: Poppler pdftoppm not installed; wrote proof.json stub",
            out,
            False,
        )
    prefix = out / "page"
    for stale in out.glob("page*.png"):
        stale.unlink()
    for stale in out.glob("diff-*.png"):
        stale.unlink()
    completed = subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf), str(prefix)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ProofResult(False, completed.stderr.strip() or "pdftoppm failed", out, False)
    pages = sorted(out.glob("page-*.png")) + sorted(out.glob("page*.png"))
    pages = sorted({path.resolve() for path in pages})
    max_diff = 0.0
    compared = False
    ref_root = (
        root / ".pydesign" / "proof" / "reference" if reference_dir is None else Path(reference_dir)
    )
    if ref_root.is_dir():
        for page in pages:
            reference = ref_root / page.name
            if not reference.is_file():
                continue
            diff_value, _diff_path = _difference_png(page, reference, out / f"diff-{page.name}")
            if diff_value is None:
                continue
            compared = True
            max_diff = max(max_diff, diff_value)
    ok = (not compared) or max_diff <= threshold
    manifest = {
        "ok": ok,
        "compared": compared,
        "dpi": dpi,
        "threshold": threshold,
        "max_diff": max_diff,
        "pdf": str(pdf),
        "pages": [path.name for path in pages],
    }
    (out / "proof.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not ok:
        return ProofResult(
            False,
            f"proof threshold breached: max_diff={max_diff:.2f} > {threshold}",
            out,
            compared,
            max_diff,
        )
    return ProofResult(
        True,
        f"wrote {len(pages)} proof raster(s) under {out}"
        + (f"; max_diff={max_diff:.2f}" if compared else ""),
        out,
        compared,
        max_diff,
    )


def _difference_png(
    actual: Path,
    reference: Path,
    destination: Path,
) -> tuple[float | None, Path | None]:
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return None, None
    left = Image.open(actual).convert("RGB")
    right = Image.open(reference).convert("RGB")
    if left.size != right.size:
        right = right.resize(left.size)
    diff = ImageChops.difference(left, right)
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / max(1, len(stat.mean))
    diff.save(destination)
    return float(mean), destination
