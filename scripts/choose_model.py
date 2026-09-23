"""Find a Gemini model that is responding for YOUR API key and switch all agents to it.

Run from the ADK_Disaster_Assistant folder with the venv active:
    python scripts\\choose_model.py            (test models and switch to the best working one)
    python scripts\\choose_model.py --dry-run  (only test, change nothing)

The API key is read from agents/disaster_recovery_assistant/.env and is never printed.
"""
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "agents" / "disaster_recovery_assistant"
load_dotenv(APP / ".env")

SKIP = ("image", "tts", "audio", "live", "embedding", "native", "robotics", "computer-use", "veo", "imagen", "learnlm", "gemma")


def version_key(name: str):
    nums = re.findall(r"\d+(?:\.\d+)?", name)
    v = float(nums[0]) if nums else 0.0
    return (-v, "lite" in name, "preview" in name or "exp" in name, name)


def main():
    dry_run = "--dry-run" in sys.argv
    client = genai.Client()

    candidates = []
    for m in client.models.list():
        name = m.name.replace("models/", "")
        actions = getattr(m, "supported_actions", None) or []
        if "gemini" not in name or "flash" not in name:
            continue
        if actions and "generateContent" not in actions:
            continue
        if any(s in name for s in SKIP):
            continue
        candidates.append(name)
    candidates = sorted(set(candidates), key=version_key)
    print(f"Found {len(candidates)} Gemini flash models for this key. Testing each one...\n")

    working = []
    for name in candidates:
        ok, note = False, ""
        for attempt in range(2):
            try:
                reply = client.models.generate_content(model=name, contents="Reply with the single word OK.")
                ok, note = True, (reply.text or "").strip()[:20]
                break
            except Exception as exc:  # noqa: BLE001
                code = getattr(exc, "code", "") or type(exc).__name__
                note = f"{code}"
                time.sleep(2)
        print(f"  {'WORKS ' if ok else 'failed'}  {name:45s} {note}")
        if ok:
            working.append(name)

    if not working:
        print("\nNo model answered right now. Wait 10-15 minutes and run this script again.")
        return

    # Prefer a full 'flash' model (better at following long instructions and tool calls),
    # fall back to 'flash-lite' if that is all that responds.
    full = [w for w in working if "lite" not in w]
    chosen = (full or working)[0]
    print(f"\nChosen model: {chosen}")

    if dry_run:
        print("Dry run: no files changed.")
        return

    changed = 0
    for f in sorted(APP.glob("*.yaml")):
        text = f.read_text(encoding="utf-8")
        new = re.sub(r"^model: .+$", f"model: {chosen}", text, flags=re.M)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed += 1
    print(f"Updated {changed} agent files to 'model: {chosen}'.")
    print("Now restart ADK Web (Ctrl+C, then: adk web agents) and click New Session.")


if __name__ == "__main__":
    main()
