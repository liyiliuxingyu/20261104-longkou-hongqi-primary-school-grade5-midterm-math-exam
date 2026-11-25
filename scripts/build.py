#!/usr/bin/env python3
"""Build both A3 PDFs without relying on a previous conversation's paths.

Python 3.9+ and an installed XeLaTeX toolchain are required.  No network access
or shell escape is used.  Recovered reference PDFs in pdf/ are never replaced.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("五年级数学小测_试题版", "五年级数学小测_答案版")
REQUIRED = ("article.cls", "ctexart.cls", "xeCJK.sty", "FandolSong-Regular.otf",
            "geometry.sty", "amsmath.sty", "amssymb.sty", "array.sty",
            "tabularx.sty", "graphicx.sty", "xcolor.sty", "tikz.sty")


def run_capture(command, env, cwd=None):
    return subprocess.run(command, env=env, cwd=cwd, text=True,
                          encoding="utf-8", errors="replace",
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def tool_environment(kpsewhich):
    env = os.environ.copy()
    vendor = ROOT / "vendor" / "texmf"
    notes = []
    if vendor.is_dir():
        env["TEXMFHOME"] = str(vendor)
        notes.append("Using bundled vendor/texmf as TEXMFHOME for this process only.")
    # A minimal cloud image can have readable TeX files but a missing ls-R
    # database.  Remove the database-only (!!) qualifier for this invocation.
    # This neither edits system files nor grants access to unreadable files.
    probe = run_capture([kpsewhich, "article.cls"], env)
    if probe.returncode != 0 or not probe.stdout.strip():
        tree = run_capture([kpsewhich, "-var-value=TEXMF"], env)
        if tree.returncode == 0 and tree.stdout.strip():
            env["TEXMF"] = tree.stdout.strip().replace("!!", "")
            notes.append("TeX filename-database fallback: filesystem search enabled for this process.")
    return env, notes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="check dependencies without compiling")
    p.add_argument("--output-dir", type=Path, default=ROOT / "build",
                   help="output path; relative paths are resolved from the project root")
    p.add_argument("--only", choices=("exam", "answer"))
    p.add_argument("--engine", default="xelatex", help="XeLaTeX executable name or absolute path")
    args = p.parse_args()
    engine = shutil.which(args.engine)
    kpsewhich = shutil.which("kpsewhich")
    if not engine or not kpsewhich:
        print("ERROR: XeLaTeX and kpsewhich must be installed and available on PATH.")
        print("Read docs/运行环境与依赖.txt. Bundled fonts are not a TeX engine.")
        return 2
    env, notes = tool_environment(kpsewhich)
    missing = []
    resolved = {}
    for name in REQUIRED:
        result = run_capture([kpsewhich, name], env)
        value = result.stdout.strip()
        if result.returncode or not value or not Path(value.splitlines()[0]).is_file():
            missing.append(name)
        else:
            resolved[name] = value.splitlines()[0]
    for name in ("图形.tex", "原题模糊图.png"):
        if not (ROOT / "src" / name).is_file():
            missing.append("src/" + name)
    version = run_capture([engine, "--version"], env).stdout.splitlines()[0]
    print(version)
    for note in notes:
        print(note)
    if missing:
        print("ERROR: missing dependencies: " + ", ".join(missing))
        print("See docs/运行环境与依赖.txt; no automatic download has been attempted.")
        return 2
    format_probe = run_capture([kpsewhich, "-format=fmt", "xelatex.fmt"], env)
    needs_format = format_probe.returncode != 0 or not format_probe.stdout.strip()
    if needs_format:
        ini_probe = run_capture([kpsewhich, "xelatex.ini"], env)
        if ini_probe.returncode != 0 or not ini_probe.stdout.strip():
            print("ERROR: xelatex.fmt and xelatex.ini are both missing.")
            return 2
        print("No system xelatex.fmt found; compilation will generate a project-local format.")
    map_probe = run_capture([kpsewhich, "pdftex.map"], env)
    fallback_maps = []
    needs_font_map = map_probe.returncode != 0 or not map_probe.stdout.strip()
    if needs_font_map:
        for name in ("cm.map", "cmextra.map", "lm.map"):
            result = run_capture([kpsewhich, name], env)
            path = result.stdout.strip()
            if result.returncode or not path or not Path(path).is_file():
                print("ERROR: pdftex.map is absent and fallback font map is missing: " + name)
                return 2
            fallback_maps.append(Path(path))
        print("No system pdftex.map found; compilation will assemble a project-local CM/LM font map.")
    print("Dependency check passed.")
    if args.check:
        return 0
    out = (args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir).resolve()
    if out == (ROOT / "pdf").resolve() or (ROOT / "pdf").resolve() in out.parents:
        print("ERROR: pdf/ holds recovered reference originals. Choose another output directory.")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    report = {"started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "engine_version": version, "notes": notes, "targets": [],
              "all_succeeded": False}
    if needs_font_map:
        map_directory = out / ".fontmaps"
        map_directory.mkdir(parents=True, exist_ok=True)
        contents = "% Project-local fallback assembled from installed, unmodified font maps.\n"
        for source_map in fallback_maps:
            contents += "% " + source_map.name + "\n" + source_map.read_text(encoding="utf-8") + "\n"
        (map_directory / "pdftex.map").write_text(contents, encoding="utf-8")
        env["TEXFONTMAPS"] = str(map_directory) + "//" + os.pathsep + env.get("TEXFONTMAPS", "")
        report["font_map_fallback"] = [f.name for f in fallback_maps]
        print("Generated a project-local font map, including Latin Modern symbol encoding.")
    if needs_format:
        cache = out / ".formats"
        cache.mkdir(parents=True, exist_ok=True)
        for key, folder in (("TEXMFVAR", ".texmf-var"),
                            ("TEXMFCONFIG", ".texmf-config"),
                            ("TEXMFCACHE", ".texmf-cache")):
            directory = out / folder
            directory.mkdir(parents=True, exist_ok=True)
            env[key] = str(directory)
        # Regenerate with this engine rather than shipping a version-specific
        # binary .fmt in the handoff archive.
        command = [engine, "-ini", "-etex", "-no-pdf", "-jobname=xelatex",
                   "-progname=xelatex", "-interaction=nonstopmode",
                   "-halt-on-error", "xelatex.ini"]
        result = run_capture(command, env, cwd=cache)
        (cache / "format_generation.txt").write_text(result.stdout, encoding="utf-8")
        report["format_generated"] = result.returncode == 0 and (cache / "xelatex.fmt").is_file()
        if not report["format_generated"]:
            print("ERROR: local XeLaTeX format generation failed.")
            print("\n".join(result.stdout.splitlines()[-30:]))
            (out / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 1
        env["TEXFORMATS"] = str(cache) + "//" + os.pathsep + env.get("TEXFORMATS", "")
        print("Generated a project-local xelatex.fmt for the current engine.")
    targets = TARGETS if args.only is None else (TARGETS[0 if args.only == "exam" else 1],)
    for stem in targets:
        source = ROOT / "src" / (stem + ".tex")
        if not source.is_file():
            print("ERROR: missing source:", source)
            return 2
        item = {"source": "src/" + source.name, "passes": [], "warnings": []}
        report["targets"].append(item)
        for pass_no in (1, 2):
            command = [engine, "-no-shell-escape", "-interaction=nonstopmode",
                       "-halt-on-error", "-file-line-error", "-recorder",
                       "-output-directory=" + str(out), source.name]
            result = run_capture(command, env, cwd=ROOT / "src")
            console = out / (stem + ".pass" + str(pass_no) + ".txt")
            console.write_text(result.stdout, encoding="utf-8")
            item["passes"].append({"pass": pass_no, "exit_code": result.returncode,
                                   "console": console.name})
            print(stem + ": pass " + str(pass_no) + ", exit " + str(result.returncode))
            if result.returncode:
                print("\n".join(result.stdout.splitlines()[-30:]))
                (out / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return 1
        log_path = out / (stem + ".log")
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        item["warnings"] = [line for line in log.splitlines()
                            if "Missing character:" in line or "Overfull \\" in line
                            or "Warning:" in line]
        item["missing_glyphs"] = any("Missing character:" in w for w in item["warnings"])
        pdf = out / (stem + ".pdf")
        item["pdf_exists"] = pdf.is_file()
        item["pdf_bytes"] = pdf.stat().st_size if pdf.is_file() else 0
        if item["missing_glyphs"] or not item["pdf_exists"]:
            print("ERROR: missing glyphs or missing PDF; inspect the build log.")
            (out / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 1
    report["all_succeeded"] = True
    (out / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Build complete. Reference originals remain in pdf/.")
    print("Outputs:", out)
    print("Next (from the project root): python scripts/verify.py --skip-checksums --pdf-dir \"" + str(out) + "\" --compare-dir pdf --require-identical-render")
    return 0


if __name__ == "__main__":
    sys.exit(main())
