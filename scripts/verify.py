#!/usr/bin/env python3
"""Verify a handoff snapshot, PDF geometry, and optionally rendered equivalence.

Hash/source checks need only Python 3.9+. PDF checks require pypdf.
Optional rendered comparison and PNG export require PyMuPDF and Pillow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
PDF_NAMES = ("五年级数学小测_试题版.pdf", "五年级数学小测_答案版.pdf")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resolve_path(value):
    return value.resolve() if value.is_absolute() else (ROOT / value).resolve()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skip-checksums", action="store_true", help="use only after intentional edits")
    p.add_argument("--files-only", action="store_true", help="stdlib-only integrity/source checks")
    p.add_argument("--strict", action="store_true", help="reject unlisted files in a fresh snapshot")
    p.add_argument("--pdf-dir", type=Path, default=Path("pdf"))
    p.add_argument("--compare-dir", type=Path)
    p.add_argument("--require-identical-render", action="store_true")
    p.add_argument("--render-dir", type=Path)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    if args.require_identical_render and (not args.compare_dir or args.files_only):
        p.error("--require-identical-render requires --compare-dir and PDF checks")
    if args.files_only and (args.compare_dir or args.render_dir):
        p.error("--files-only cannot be combined with rendering/comparison options")
    if args.strict and args.skip_checksums:
        p.error("--strict requires checksum verification")
    report = {"checks": [], "pdfs": [], "errors": []}
    errors = report["errors"]
    if not args.skip_checksums:
        checksum_file = ROOT / "SHA256SUMS"
        listed = {"SHA256SUMS"}
        count = 0
        if not checksum_file.exists():
            errors.append("SHA256SUMS is missing")
        else:
            for line in checksum_file.read_text(encoding="utf-8").splitlines():
                if not line:
                    continue
                parts = line.split("  ", 1)
                if len(parts) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]) or not parts[1]:
                    errors.append("Malformed SHA256SUMS entry")
                    continue
                digest, name = parts
                rel = Path(name)
                if rel.is_absolute() or ".." in rel.parts:
                    errors.append("Unsafe checksum path: " + name)
                    continue
                if rel.as_posix() in listed:
                    errors.append("Duplicate checksum path: " + name)
                    continue
                listed.add(rel.as_posix())
                f = ROOT / rel
                if not f.is_file():
                    errors.append("Missing: " + name)
                elif sha256(f) != digest:
                    errors.append("SHA-256 mismatch: " + name)
                count += 1
            if count == 0:
                errors.append("SHA256SUMS contains no valid file entries")
            if args.strict:
                actual = {f.relative_to(ROOT).as_posix() for f in ROOT.rglob("*")
                          if f.is_file() and f.relative_to(ROOT).parts[0] != ".git"}
                extra = sorted(actual - listed)
                if extra:
                    errors.append("Unlisted files: " + ", ".join(extra))
        report["checks"].append({"name": "SHA256SUMS", "entries": count})
    sources = [ROOT / "src" / (n[:-4] + ".tex") for n in PDF_NAMES]
    for f in [*sources, ROOT / "src/图形.tex", ROOT / "src/原题模糊图.png"]:
        if not f.is_file():
            errors.append("Missing source/resource: " + f.name)
    for f in sources:
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        if "paperwidth=420mm,paperheight=297mm" not in text:
            errors.append("Unexpected source page dimensions: " + f.name)
        if r"\input{图形.tex}" not in text or r"{原题模糊图.png}" not in text:
            errors.append("Shared graphic resource reference is missing: " + f.name)
        if re.search(r"/workspace/|/home/agent/|[A-Za-z]:\\", text):
            errors.append("Machine-specific absolute source path: " + f.name)
    report["checks"].append({"name": "source structure", "files": len(sources)})
    if not args.files_only:
        try:
            from pypdf import PdfReader
        except ImportError:
            errors.append("pypdf is missing; install requirements.txt or use --files-only")
            PdfReader = None
        if PdfReader:
            folder = resolve_path(args.pdf_dir)
            for name in PDF_NAMES:
                f = folder / name
                item = {"file": name, "sha256": sha256(f) if f.is_file() else None, "pages": []}
                report["pdfs"].append(item)
                if not f.is_file():
                    errors.append("Missing PDF: " + str(f))
                    continue
                try:
                    reader = PdfReader(f)
                    if len(reader.pages) != 2:
                        errors.append(name + ": expected 2 pages, found " + str(len(reader.pages)))
                    for i, page in enumerate(reader.pages, 1):
                        width = float(page.mediabox.width) * 25.4 / 72
                        height = float(page.mediabox.height) * 25.4 / 72
                        text = page.extract_text() or ""
                        item["pages"].append({"page": i, "width_mm": round(width, 4),
                                              "height_mm": round(height, 4), "text_chars": len(text)})
                        if abs(width - 420) > .05 or abs(height - 297) > .05:
                            errors.append(name + ": page " + str(i) + " is not A3 landscape")
                        if len(text.strip()) < 100:
                            errors.append(name + ": page " + str(i) + " appears blank or textless")
                except Exception as e:
                    errors.append(name + ": " + str(e))
        if args.compare_dir or args.render_dir:
            try:
                import fitz
                from PIL import Image, ImageChops, ImageStat
            except ImportError:
                errors.append("PyMuPDF/Pillow missing; install requirements.txt for rendering")
            else:
                render_to = resolve_path(args.render_dir) if args.render_dir else None
                if render_to:
                    render_to.mkdir(parents=True, exist_ok=True)
                report["render_checks"] = []
                for kind, name in zip(("exam", "answer"), PDF_NAMES):
                    f = resolve_path(args.pdf_dir) / name
                    if not f.is_file():
                        continue
                    doc = fitz.open(f)
                    comparison = resolve_path(args.compare_dir) / name if args.compare_dir else None
                    other = fitz.open(comparison) if comparison and comparison.is_file() else None
                    if args.compare_dir and other is None:
                        errors.append("Comparison PDF missing: " + name)
                    if other is not None and len(other) != len(doc):
                        errors.append("Comparison page-count mismatch: " + name)
                    for i, page in enumerate(doc):
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                        if render_to:
                            img.save(render_to / (kind + "_page_" + str(i + 1) + ".png"))
                        item = {"file": name, "page": i + 1, "dpi": 108}
                        colors = [s["color"] for b in page.get_text("dict")["blocks"] if "lines" in b
                                  for line in b["lines"] for s in line["spans"] if s["text"].strip()]
                        item["colored_text_spans"] = sum(c not in (0, 16777215) for c in colors)
                        if kind == "exam" and item["colored_text_spans"]:
                            errors.append(name + ": unexpected colored text on page " + str(i + 1))
                        if other is not None and i < len(other):
                            q = other[i].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                            baseline = Image.frombytes("RGB", (q.width, q.height), q.samples)
                            item["same_dimensions"] = img.size == baseline.size
                            item["same_extracted_text"] = re.sub(r"\s+", "", page.get_text()) == re.sub(r"\s+", "", other[i].get_text())
                            if img.size == baseline.size:
                                difference = ImageChops.difference(img, baseline)
                                item["identical_render"] = difference.getbbox() is None
                                item["mean_abs_channel_difference_0_255"] = [round(v, 8) for v in ImageStat.Stat(difference).mean]
                            else:
                                item["identical_render"] = False
                            if not item["same_extracted_text"]:
                                errors.append(name + ": extracted text differs on page " + str(i + 1))
                            if args.require_identical_render and not item["identical_render"]:
                                errors.append(name + ": render differs on page " + str(i + 1))
                        report["render_checks"].append(item)
                    doc.close()
                    if other is not None:
                        other.close()
    render_differences = [r for r in report.get("render_checks", [])
                          if r.get("identical_render") is False]
    report["render_differences_require_visual_review"] = bool(render_differences)
    report["passed"] = not errors
    if args.report:
        destination = resolve_path(args.report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
