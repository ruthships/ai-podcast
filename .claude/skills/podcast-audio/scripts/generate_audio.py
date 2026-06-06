#!/usr/bin/env python3
"""
generate_audio.py — standalone TTS audio generator for the weekly AI podcast.

Reads a podcast script JSON (produced by /ai-podcast Phase 4), calls ElevenLabs
to synthesize each speaker turn, stitches the MP3 segments with 15ms micro-fades
to eliminate boundary clicks, and writes a final MP3.

Usage:
    generate_audio.py                          # test mode (6 segs) on latest episode folder
    generate_audio.py full                     # full episode
    generate_audio.py regen 16,23,25           # regenerate specific segments, re-stitch
    generate_audio.py 2026-05-25 full          # specific date + mode
    generate_audio.py 2026-05-25 full --episode 9   # set episode number in the filename
    generate_audio.py --help

Output (the stitched 'voice only' file, before the intro music is mixed in):
    <DATE>/audio_output_elevenlabs/<run>/The AI News Podcast - Episode <N> - <Month DD YYYY> - Voice Only.mp3
Episode number <N> comes from --episode, else auto-detected as
(highest existing episode in episodes/) + 1.

API key resolution order:
    1. $ELEVENLABS_API_KEY environment variable
    2. <project-dir>/.env file with `ELEVENLABS_API_KEY=...`  (the canonical source)
    3. ~/.podcast-audio.env file with `ELEVENLABS_API_KEY=...` (legacy fallback)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# ──────────────────────────────────────────────────────────────────────────────
# Hard-coded voice config — the team uses the same hosts for consistency.
# Voice IDs from elevenlabs.io/voice-library.
# ──────────────────────────────────────────────────────────────────────────────
VOICE_HOST_A = "TX3LPaxmHKxFdv7VOQHJ"  # Liam — deep, authoritative lead
VOICE_HOST_B = "56AoDkrOh6qfVPDXZ7Pt"  # Cassidy — natural, conversational

MODEL_HOST_A = "eleven_multilingual_v2"
MODEL_HOST_B = "eleven_turbo_v2_5"  # turbo handles female intonation better

OUTPUT_FORMAT = "mp3_44100_128"

VOICE_SETTINGS_HOST_A = {
    "stability": 0.15,
    "similarity_boost": 0.75,
    "style": 0.65,
    "use_speaker_boost": True,
}
VOICE_SETTINGS_HOST_B = None  # OOB defaults

PAUSE_BETWEEN_TURNS_MS = 0  # 0 = let ElevenLabs natural pacing handle transitions
FADE_MS = 15  # inaudible fade preventing click/beep at PCM segment boundaries

DEFAULT_PROJECT_DIR = Path.home() / "Code" / "02-ai-podcast-newsletter"
ENV_FILE = Path.home() / ".podcast-audio.env"
TEST_SEGMENT_COUNT = 6
MAX_CHARS_PER_CALL = 2500


# ──────────────────────────────────────────────────────────────────────────────
# API key resolution
# ──────────────────────────────────────────────────────────────────────────────
def _key_from_env_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("ELEVENLABS_API_KEY"):
            _, _, val = line.partition("=")
            val = val.strip().strip('"').strip("'")
            if val:
                return val
    return None


def load_api_key(project_dir: Optional[Path] = None) -> str:
    # 1. environment
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    # 2. the project's .env (canonical source, verified by autobrief bootstrap)
    if project_dir is not None:
        key = _key_from_env_file(project_dir / ".env")
        if key:
            return key
    # 3. legacy standalone file
    key = _key_from_env_file(ENV_FILE)
    if key:
        return key
    repo_env = (project_dir / ".env") if project_dir else "<project-dir>/.env"
    sys.exit(
        f"ERROR: no ElevenLabs API key found.\n"
        f"Set $ELEVENLABS_API_KEY in your shell, or add this line to {repo_env}:\n"
        f"  ELEVENLABS_API_KEY=your_key_here\n"
        f"(Running /autobrief-podcast bootstrap verifies this key is present.)"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Episode folder + script JSON resolution
# ──────────────────────────────────────────────────────────────────────────────
def list_episode_folders(project_dir: Path) -> List[Path]:
    """All dated episode folders under the project, sorted oldest → newest."""
    return sorted(
        p for p in project_dir.glob("20*-*")
        if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", p.name)
    )


def find_episode_folder(date: Optional[str], project_dir: Path) -> Path:
    """Resolve the episode folder. If date is given, use that. Otherwise pick latest."""
    if date:
        folder = project_dir / date
        if not folder.is_dir():
            sys.exit(f"ERROR: episode folder not found: {folder}")
        return folder
    candidates = list_episode_folders(project_dir)
    if not candidates:
        sys.exit(f"ERROR: no episode folders under {project_dir}. Looked for YYYY-MM-DD/.")
    return candidates[-1]


def autodetect_episode_number(project_dir: Path) -> int:
    """Fallback episode number when --episode isn't passed.

    Mirrors /podcast-postprocess: (highest existing episode in episodes/) + 1,
    i.e. the *next* episode number — the same value postprocess and the website
    stage compute, so the filename stays consistent across stages. Matches both
    the legacy kebab files (`...-episode-9-...`) and the current title-case files
    (`...Episode 9...`). Falls back to dated-folder count if episodes/ is empty.
    """
    episodes_dir = project_dir / "episodes"
    nums = []
    if episodes_dir.is_dir():
        for p in episodes_dir.glob("*.mp3"):
            m = re.search(r"[Ee]pisode[ -](\d+)", p.name)
            if m:
                nums.append(int(m.group(1)))
    if nums:
        return max(nums) + 1
    return len(list_episode_folders(project_dir)) + 1


def pretty_date(folder_name: str) -> str:
    """`2026-06-02` -> `June 02 2026` (the human-readable form used in filenames)."""
    return datetime.strptime(folder_name, "%Y-%m-%d").strftime("%B %d %Y")


def final_mp3_name(episode_folder: Path, episode: int) -> str:
    """Canonical raw 'voice only' (pre-intro) stitch filename.

    This exact name is the contract with the rest of the pipeline:
    /podcast-postprocess reads it as the input for the intro mix, and the
    /autobrief-podcast orchestrator detects Stage 2 completion by it.

        <DATE>/audio_output_elevenlabs/<run>/The AI News Podcast - Episode <N> - <Month DD YYYY> - Voice Only.mp3

    The ` - Voice Only` suffix marks this as the TTS stitch *before* the canonical
    intro music is mixed in (postprocess writes the with-intro file to
    episodes/The AI News Podcast - Episode <N> - <Month DD YYYY>.mp3).
    """
    return f"The AI News Podcast - Episode {episode} - {pretty_date(episode_folder.name)} - Voice Only.mp3"


def find_script_json(folder: Path) -> Path:
    matches = list(folder.glob("podcast_script_*.json"))
    if not matches:
        sys.exit(f"ERROR: no podcast_script_*.json in {folder}")
    if len(matches) > 1:
        sys.exit(f"ERROR: multiple script JSON files in {folder} — disambiguate: {matches}")
    return matches[0]


# ──────────────────────────────────────────────────────────────────────────────
# Text utilities
# ──────────────────────────────────────────────────────────────────────────────
def split_long_text(text: str, max_chars: int = MAX_CHARS_PER_CALL) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        candidate = f"{current} {s}".strip() if current else s
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    final = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
        else:
            for i in range(0, len(c), max_chars):
                final.append(c[i:i + max_chars])
    return [c.strip() for c in final if c.strip()]


def total_char_count(segments: list) -> int:
    return sum(len(s["text"]) for s in segments)


# ──────────────────────────────────────────────────────────────────────────────
# Cost estimate (ElevenLabs: chars consumed = chars billed)
# ──────────────────────────────────────────────────────────────────────────────
def print_cost_estimate(chars: int, label: str) -> None:
    # Reference quotas: Creator ~100K chars/mo, Pro ~500K chars/mo.
    pct_creator = chars / 100_000 * 100
    pct_pro = chars / 500_000 * 100
    print(f"\nCost estimate ({label}):")
    print(f"  {chars:,} characters → {pct_creator:.1f}% of Creator tier (100K/mo)")
    print(f"                       {pct_pro:.1f}% of Pro tier (500K/mo)")


# ──────────────────────────────────────────────────────────────────────────────
# TTS synthesis
# ──────────────────────────────────────────────────────────────────────────────
def synthesize_segment(client, text: str, speaker: str, output_path: Path,
                       previous_text: Optional[str] = None,
                       next_text: Optional[str] = None) -> None:
    from elevenlabs import VoiceSettings

    voice_id = VOICE_HOST_A if speaker == "host_a" else VOICE_HOST_B
    model_id = MODEL_HOST_A if speaker == "host_a" else MODEL_HOST_B
    settings_dict = VOICE_SETTINGS_HOST_A if speaker == "host_a" else VOICE_SETTINGS_HOST_B

    kwargs = dict(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        output_format=OUTPUT_FORMAT,
        previous_text=previous_text,
        next_text=next_text,
    )
    if settings_dict is not None:
        kwargs["voice_settings"] = VoiceSettings(**settings_dict)

    audio_bytes = b"".join(client.text_to_speech.convert(**kwargs))
    output_path.write_bytes(audio_bytes)


def synthesize_all(client, segments: list, output_dir: Path,
                   indices: Optional[List[int]] = None) -> List[Path]:
    """
    Synthesize segments to MP3 files in output_dir.
    indices: 1-based segment numbers to generate (None = all).
    Returns list of generated file paths in segment order.
    """
    audio_files: List[Path] = []
    target_set = set(indices) if indices else None

    total = len(segments)
    for i, seg in enumerate(segments, start=1):
        if target_set is not None and i not in target_set:
            continue
        speaker = seg["speaker"]
        text = seg["text"].strip()
        if not text:
            continue

        prev_ctx = segments[i - 2]["text"].strip() if i >= 2 else None
        next_ctx = segments[i]["text"].strip() if i < total else None

        parts = split_long_text(text)
        for j, part in enumerate(parts, start=1):
            out_path = output_dir / f"{i:03d}_{speaker}_part{j}.mp3"
            print(f"  [{i}/{total}] {speaker} part{j} ({len(part)} chars) → {out_path.name}")

            part_prev = parts[j - 2] if j >= 2 else prev_ctx
            part_next = parts[j] if j < len(parts) else next_ctx

            synthesize_segment(
                client=client,
                text=part,
                speaker=speaker,
                output_path=out_path,
                previous_text=part_prev,
                next_text=part_next,
            )
            audio_files.append(out_path)

    return audio_files


# ──────────────────────────────────────────────────────────────────────────────
# Stitch
# ──────────────────────────────────────────────────────────────────────────────
def merge_mp3_files(input_paths: List[Path], output_path: Path,
                    pause_ms: int = PAUSE_BETWEEN_TURNS_MS) -> None:
    from pydub import AudioSegment

    if not input_paths:
        return

    segments = [AudioSegment.from_mp3(str(p)) for p in input_paths]

    if pause_ms > 0:
        ref = segments[0]
        silence = (
            AudioSegment.silent(duration=pause_ms, frame_rate=ref.frame_rate)
            .set_channels(ref.channels)
            .set_sample_width(ref.sample_width)
        )
    else:
        silence = None

    processed = []
    for i, seg in enumerate(segments):
        if i > 0:
            seg = seg.fade_in(FADE_MS)
        if i < len(segments) - 1:
            seg = seg.fade_out(FADE_MS)
        processed.append(seg)

    combined = processed[0]
    for seg in processed[1:]:
        if silence:
            combined += silence
        combined += seg

    combined.export(str(output_path), format="mp3", bitrate="128k")


def collect_existing_segments(run_dir: Path) -> List[Path]:
    """Numbered segment MP3s in run_dir, in segment order (NNN_speaker_partM.mp3).

    Matching on the `NNN_` prefix means any final stitched output (whatever it's
    named) is naturally excluded, so re-stitching never folds the final file in.
    """
    files = sorted(
        p for p in run_dir.glob("*.mp3")
        if re.match(r"\d{3}_", p.name)
    )
    return files


def find_latest_run_dir(output_dir: Path) -> Path:
    runs = sorted([p for p in output_dir.glob("*/") if p.is_dir()])
    if not runs:
        sys.exit(f"ERROR: no run folders in {output_dir}. Run test or full first.")
    return runs[-1]


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate podcast audio via ElevenLabs from a script JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("args", nargs="*", help="Positional args: [date] [mode] [N,M,...]")
    p.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR),
                   help=f"Podcast project root (default: {DEFAULT_PROJECT_DIR})")
    p.add_argument("--episode", type=int, default=None,
                   help="Episode number for the output filename. If omitted, "
                        "auto-detected as (highest existing episode-N in episodes/) + 1.")
    p.add_argument("--dry-run", action="store_true",
                   help="Show cost estimate and exit without calling the API.")
    return p.parse_args(argv)


def parse_positional(raw_args: List[str]) -> dict:
    """Parse mixed positional args: optional date, mode (test|full|regen), regen list."""
    date = None
    mode = "test"
    regen_indices: List[int] = []

    for tok in raw_args:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", tok):
            date = tok
        elif tok in ("test", "full"):
            mode = tok
        elif tok == "regen":
            mode = "regen"
        elif re.match(r"^\d+(,\d+)*$", tok):
            regen_indices = [int(x) for x in tok.split(",")]
        else:
            sys.exit(f"ERROR: unrecognized arg '{tok}'. Use: [date] [test|full|regen] [N,M,...]")

    if mode == "regen" and not regen_indices:
        sys.exit("ERROR: regen mode requires a list of segment numbers (e.g. `regen 16,23,25`).")

    return {"date": date, "mode": mode, "regen_indices": regen_indices}


def main() -> int:
    args = parse_args(sys.argv[1:])
    parsed = parse_positional(args.args)

    project_dir = Path(args.project_dir).expanduser()
    episode_folder = find_episode_folder(parsed["date"], project_dir)
    script_path = find_script_json(episode_folder)

    print(f"Episode folder: {episode_folder}")
    print(f"Script: {script_path.name}")

    script = json.loads(script_path.read_text())
    segments = script["segments"]
    episode = args.episode if args.episode is not None else autodetect_episode_number(project_dir)
    print(f"Episode title: {script['episode_title']}")
    print(f"Episode number: {episode}{'' if args.episode is not None else ' (auto-detected)'}")
    print(f"Total segments: {len(segments)}")

    output_dir = episode_folder / "audio_output_elevenlabs"
    output_dir.mkdir(exist_ok=True)

    # Mode-specific logic
    mode = parsed["mode"]

    if mode == "regen":
        # Determine which segments to regenerate; estimate cost on those only
        bad = parsed["regen_indices"]
        invalid = [n for n in bad if not (1 <= n <= len(segments))]
        if invalid:
            sys.exit(f"ERROR: segment numbers out of range: {invalid} (valid 1-{len(segments)})")
        chars = sum(len(segments[n - 1]["text"]) for n in bad)
        print_cost_estimate(chars, f"regen {len(bad)} segments")
        if args.dry_run:
            return 0
        run_dir = find_latest_run_dir(output_dir)
        print(f"\nRegenerating segments {bad} in {run_dir.name}\n")
        api_key = load_api_key(project_dir)
        client = _build_client(api_key)
        synthesize_all(client, segments, run_dir, indices=bad)
        existing = collect_existing_segments(run_dir)
        final_path = run_dir / final_mp3_name(episode_folder, episode)
        print(f"\nRe-stitching {len(existing)} segments → {final_path.name}")
        merge_mp3_files(existing, final_path)
        print(f"\nDone. {final_path}")
        return 0

    # test or full
    if mode == "test":
        segments_to_run = segments[:TEST_SEGMENT_COUNT]
        label = f"test ({TEST_SEGMENT_COUNT} segs)"
    else:
        segments_to_run = segments
        label = "full episode"

    chars = total_char_count(segments_to_run)
    print_cost_estimate(chars, label)
    if args.dry_run:
        return 0

    api_key = load_api_key(project_dir)
    client = _build_client(api_key)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", script["episode_title"]).strip("_")[:80]
    run_dir = output_dir / f"{timestamp}_{safe_title}_elevenlabs"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nOutput folder: {run_dir}")
    print(f"Generating: {label}\n")

    audio_files = synthesize_all(client, segments_to_run, run_dir)
    final_path = run_dir / final_mp3_name(episode_folder, episode)
    print(f"\nStitching {len(audio_files)} segments → {final_path.name}")
    merge_mp3_files(audio_files, final_path)

    print(f"\nDone. {final_path}")
    print(f"\nNext step: listen to {final_path.name}. If it sounds right, re-run with `full`.")
    print(f"If specific segments sound bad, run: generate_audio.py regen N,M,O")
    return 0


def _build_client(api_key: str):
    try:
        import httpx
        from elevenlabs.client import ElevenLabs
    except ImportError:
        sys.exit(
            "ERROR: missing dependencies (elevenlabs, pydub, httpx).\n"
            "Run this script with the bootstrapped venv interpreter:\n"
            "  ~/.claude/email-venv/bin/python <this script> <args>\n"
            "or run `bash ~/Code/00-autobrief-podcast/scripts/bootstrap.sh` to install them."
        )
    return ElevenLabs(api_key=api_key, httpx_client=httpx.Client(verify=False))


if __name__ == "__main__":
    sys.exit(main())
