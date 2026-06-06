#!/usr/bin/env python3
"""
fetch_image.py — find and download a CC-licensed image from Openverse, cropped
to the newsletter's 600x400 convention.

Replaces the old Unsplash flow (which needed an API key we don't have). Openverse
is free and key-less; results are Creative-Commons licensed. We filter to
commercially-usable licenses by default.

Stdlib + ffmpeg only — no pip installs.

Usage:
  # See candidates before committing to one (good for the editorial gate):
  python3 scripts/fetch_image.py --query "stock market trading floor" --list

  # Download + crop to 600x400:
  python3 scripts/fetch_image.py --query "stock market trading floor" --out assets/ep10_1_anthropic.jpg

  # Pick a specific candidate from --list (0-based):
  python3 scripts/fetch_image.py --query "data center servers" --out assets/ep10_2_aws.jpg --index 2

Notes:
- Prints attribution (title / creator / license / source URL) so you can credit
  if you ever want to. CC-BY/BY-SA technically require attribution.
- After download, run `git add` + push BEFORE referencing the image anywhere:
  both the newsletter (raw.githubusercontent URLs) and the Mailchimp campaign
  preview pull images from GitHub `main`, so an unpushed image shows broken.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.openverse.org/v1/images/"
UA = "ai-podcast-newsletter/1.0 (https://github.com/ruthships/ai-podcast)"
DEFAULT_W, DEFAULT_H = 600, 400
TIMEOUT = 30


def search(query: str, license_type: str, n: int = 10) -> list[dict]:
    params = urllib.parse.urlencode({
        "q": query,
        "page_size": n,
        "license_type": license_type,   # "commercial" => by, by-sa, cc0, pdm
        "size": "large",
        "mature": "false",
    })
    req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        sys.exit(f"ERROR: Openverse search failed: {e}")
    results = [r for r in data.get("results", []) if r.get("url")]
    if not results:
        sys.exit(f"ERROR: no Openverse results for {query!r} (license_type={license_type}). Try a broader query.")
    return results


def describe(r: dict) -> str:
    return (f"{(r.get('title') or 'untitled')[:50]:50} | {r.get('license','?'):6} "
            f"| {(r.get('creator') or '?')[:20]:20} | {r.get('url')[:60]}")


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            dest.write_bytes(resp.read())
    except Exception as e:
        sys.exit(f"ERROR: download failed ({url}): {e}")


def crop(src: Path, out: Path, w: int, h: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
        "-frames:v", "1", str(out),
    ]
    try:
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        sys.exit(f"ERROR: ffmpeg crop failed ({e}). Is ffmpeg installed? `brew install ffmpeg`")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", required=True, help="Image search term.")
    ap.add_argument("--out", help="Output path, e.g. assets/ep10_hero.jpg (required unless --list).")
    ap.add_argument("--index", type=int, default=0, help="Which candidate to use (0-based; see --list).")
    ap.add_argument("--width", type=int, default=DEFAULT_W)
    ap.add_argument("--height", type=int, default=DEFAULT_H)
    ap.add_argument("--license", default="commercial",
                    help="Openverse license_type: 'commercial' (default), 'all', 'commercial,modification'.")
    ap.add_argument("--list", action="store_true", help="List top candidates and exit (no download).")
    args = ap.parse_args()

    results = search(args.query, args.license)

    if args.list:
        print(f"Top candidates for {args.query!r} (license_type={args.license}):\n")
        for i, r in enumerate(results):
            print(f"  [{i}] {describe(r)}")
        print("\nRe-run with --out <path> [--index N] to download + crop.")
        return 0

    if not args.out:
        sys.exit("ERROR: --out is required unless --list is passed.")
    if not (0 <= args.index < len(results)):
        sys.exit(f"ERROR: --index {args.index} out of range (0-{len(results)-1}).")

    chosen = results[args.index]
    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).resolve().parent.parent / args.out

    print(f"Chosen [{args.index}]: {describe(chosen)}")
    with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    download(chosen["url"], tmp_path)
    crop(tmp_path, out, args.width, args.height)
    tmp_path.unlink(missing_ok=True)

    print(f"Saved {out}  ({args.width}x{args.height})")
    print("Attribution (for CC-BY/BY-SA): "
          f"{chosen.get('title')} by {chosen.get('creator')} — {chosen.get('license')} "
          f"({chosen.get('foreign_landing_url') or chosen.get('url')})")
    print("\nRemember: git add + push this file BEFORE referencing it in the newsletter / Mailchimp.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
