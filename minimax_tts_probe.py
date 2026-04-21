from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib import error, request


API_URL = "https://api.minimaxi.com/v1/t2a_v2"
DEFAULT_MODEL = "speech-2.8-hd"
DEFAULT_TEXT = "你好，这是一段 MiniMax TTS 测试音频。"
DEFAULT_VOICES = [
    "Chinese (Mandarin)_Radio_Host",
    "Chinese (Mandarin)_Sweet_Lady",
]


def synthesize(api_key: str, voice_id: str, text: str, model: str) -> bytes:
    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1,
            "vol": 1,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        API_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    with request.urlopen(req, timeout=120) as resp:
        raw = resp.read()

    response_data = json.loads(raw.decode("utf-8"))
    base_resp = response_data.get("base_resp", {})
    if base_resp.get("status_code") not in (None, 0):
        raise RuntimeError(f"MiniMax API error: {base_resp.get('status_code')} {base_resp.get('status_msg')}")

    audio_hex = None
    data_section = response_data.get("data")
    if isinstance(data_section, dict):
        audio_hex = data_section.get("audio")

    if not audio_hex:
        raise RuntimeError(f"No audio payload returned: {response_data}")

    return bytes.fromhex(audio_hex)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe MiniMax TTS voices")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Text to synthesize")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="MiniMax speech model")
    parser.add_argument(
        "--voice",
        action="append",
        dest="voices",
        help="Voice ID to test. Can be passed multiple times.",
    )
    parser.add_argument("--output-dir", default="output/minimax_probe", help="Directory to write mp3 files")
    args = parser.parse_args()

    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("Missing MINIMAX_API_KEY environment variable")

    voices = args.voices or DEFAULT_VOICES
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for voice_id in voices:
        print(f"Testing voice: {voice_id}")
        audio_bytes = synthesize(api_key, voice_id, args.text, args.model)
        safe_name = voice_id.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "")
        output_path = output_dir / f"{safe_name}.mp3"
        output_path.write_bytes(audio_bytes)
        print(f"Saved: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
