#!/usr/bin/env python3
"""
Flatten the skill into one file for agents that cannot read a directory
(ChatGPT custom GPTs, Gemini Gems, system prompts, project instructions).

Usage:
    python3 scripts/bundle.py [--out dist/store-ready-prompt.md]
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDER = [
    "references/apple-app-store.md",
    "references/google-play.md",
    "references/privacy-and-data.md",
    "references/assets-and-metadata.md",
    "references/rejections.md",
    "references/alternative-stores.md",
]

HEADER = """# store-ready — single-file agent instructions

You are assisting a developer preparing a mobile app for store submission.
Follow the workflow below. The reference sections that follow the workflow are
your knowledge base; consult the ones relevant to the current task.

The automated pre-flight script referenced in the workflow is not available in
this environment. Perform those checks by reading the project files yourself,
or ask the user to paste the relevant manifests.

---

"""


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/store-ready-prompt.md")
    args = ap.parse_args()

    parts = [HEADER, strip_frontmatter((ROOT / "SKILL.md").read_text(encoding="utf-8"))]
    for rel in ORDER:
        path = ROOT / rel
        if path.exists():
            parts.append("\n\n---\n\n" + path.read_text(encoding="utf-8"))

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(parts)
    out.write_text(content, encoding="utf-8")

    words = len(content.split())
    print(f"wrote {out.relative_to(ROOT)}  ({len(content):,} chars, ~{words:,} words)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
