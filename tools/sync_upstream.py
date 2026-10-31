#!/usr/bin/env python3
"""Keep upstream/idea-to-blueprint/ an exact copy of idea-to-blueprint at a pinned commit.

Everything under upstream/ is upstream's text, never edited here. This extension's changes live in its
own files (commands/discover.md, references/speckit-flow.md, scripts/lint_blueprint.py), which read
the upstream copy and say where they differ. Updating is therefore a copy, not a merge.

Usage (from the repository root):

    python3 tools/sync_upstream.py            sync to upstream's default branch
    python3 tools/sync_upstream.py <ref>      sync to a tag, branch or commit
    python3 tools/sync_upstream.py --check    exit 1 if upstream has moved past the pinned commit
    python3 tools/sync_upstream.py --verify   exit 1 if the vendored files differ from UPSTREAM.json

After a sync, run the tests: they check that the anchors this extension relies on (SKILL.md phases,
blueprint section numbers, the linter's finding hook) still exist upstream.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO = "iniesohidham/idea-to-blueprint"
ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "upstream" / "idea-to-blueprint"
MANIFEST = ROOT / "upstream" / "UPSTREAM.json"
# The skill itself; upstream's README, examples, CI and plugin metadata stay upstream.
INCLUDE = ("SKILL.md", "LICENSE", "references", "scripts", "assets")

# What this extension relies on in upstream, checked by tests/test_upstream.py and printed after a sync.
# A missing anchor means an overlay file needs a look before release.
ANCHORS = {
    "SKILL.md": [
        "## Phase 0 — Intake",
        "## Phase 1 — Deep research and benchmarking",
        "## Phase 2 — Decision brief",
        "## Phase 3 — Write the blueprint",
        "## Phase 4 — Lint and deliver",
        "## Language convention",
        "## Guardrails that override everything else",
    ],
    "references/blueprint-template.md": [
        # Section numbers read by bootstrap and compile (config-template.yml, references/speckit-flow.md §6).
        "12.2 ", "12.10 ", "13.1 ", "13.2 ", "13.3 ", "13.4 ", "13.5 ", "13.6 ", "13.7 ", "13.9 ",
        "13.10 ", "14.2 ", "14.3 ", "14.4 ", "14.8 ",
    ],
    "scripts/lint_blueprint.py": [
        "class Findings",
        "    def warn(self, line: int | None, msg: str) -> None:",
        "def main(argv: list[str]) -> int:",
        "f_.warn(None, \"No appendix with 'Session Prompts'",
    ],
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "speckit-blueprint-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def resolve(ref: str | None) -> str:
    ref = ref or json.loads(_get(f"https://api.github.com/repos/{REPO}"))["default_branch"]
    return json.loads(_get(f"https://api.github.com/repos/{REPO}/commits/{ref}"))["sha"]


def files_of(base: Path) -> dict[str, str]:
    out = {}
    for p in sorted(base.rglob("*")):
        if p.is_file():
            out[p.relative_to(base).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def missing_anchors(base: Path) -> list[str]:
    out = []
    for rel, anchors in ANCHORS.items():
        p = base / rel
        lines = p.read_text(encoding="utf-8").splitlines() if p.is_file() else []
        for a in anchors:
            if not any(l.strip().startswith(a.strip()) for l in lines):
                out.append(f"{rel}: {a.strip()}")
    return out


def verify() -> list[str]:
    want = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    have = files_of(DEST)
    problems = [f"changed: {k}" for k in want if k in have and have[k] != want[k]]
    problems += [f"missing: {k}" for k in want if k not in have]
    problems += [f"not upstream: {k}" for k in have if k not in want]
    return problems


def sync(ref: str | None) -> int:
    commit = resolve(ref)
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {"commit": None, "files": {}}
    if old["commit"] == commit and not verify():
        print(f"Already at {commit[:7]}.")
        return 0
    data = _get(f"https://codeload.github.com/{REPO}/tar.gz/{commit}")
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            members = [m for m in tar.getmembers() if m.isfile() or m.isdir()]
            for m in members:
                if m.name.startswith("/") or ".." in Path(m.name).parts:
                    raise SystemExit(f"refusing unsafe path in archive: {m.name}")
            if hasattr(tarfile, "data_filter"):
                tar.extractall(tmp, members=members, filter="data")
            else:
                tar.extractall(tmp, members=members)
        src = next(Path(tmp).iterdir())
        if DEST.exists():
            shutil.rmtree(DEST)
        DEST.mkdir(parents=True)
        for name in INCLUDE:
            s = src / name
            if s.is_dir():
                shutil.copytree(s, DEST / name)
            elif s.is_file():
                shutil.copy2(s, DEST / name)
            else:
                print(f"note: upstream no longer has {name}")
    files = files_of(DEST)
    MANIFEST.write_text(json.dumps({
        "repository": f"https://github.com/{REPO}",
        "commit": commit,
        "synced": _dt.date.today().isoformat(),
        "include": list(INCLUDE),
        "files": files,
    }, indent=2) + "\n", encoding="utf-8")

    before = old["files"]
    print(f"Synced {REPO} {str(old['commit'])[:7]} → {commit[:7]}")
    for label, keys in (
        ("added", [k for k in files if k not in before]),
        ("removed", [k for k in before if k not in files]),
        ("changed", [k for k in files if k in before and before[k] != files[k]]),
    ):
        for k in keys:
            print(f"  {label:8} {k}")
    gone = missing_anchors(DEST)
    if gone:
        print("\nAnchors this extension relies on are gone; review the overlay before releasing:")
        for g in gone:
            print(f"  ✘ {g}")
    print(
        "\nNext: python3 -m unittest discover -s tests -v; read the upstream diff "
        "(git diff -- upstream/) against commands/discover.md and references/speckit-flow.md; "
        "update NOTICE and CHANGELOG with the new commit."
    )
    return 1 if gone else 0


def main(argv: list[str]) -> int:
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if argv[:1] == ["--verify"]:
        problems = verify() + [f"anchor gone: {a}" for a in missing_anchors(DEST)]
        print("\n".join(problems) or "upstream copy matches UPSTREAM.json")
        return 1 if problems else 0
    if argv[:1] == ["--check"]:
        pinned = json.loads(MANIFEST.read_text(encoding="utf-8"))["commit"]
        head = resolve(None)
        if head == pinned:
            print(f"up to date ({pinned[:7]})")
            return 0
        print(f"upstream moved: pinned {pinned[:7]}, {REPO} is at {head[:7]}. Run tools/sync_upstream.py.")
        return 1
    return sync(argv[0] if argv else None)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
