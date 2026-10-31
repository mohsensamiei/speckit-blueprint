#!/usr/bin/env python3
"""speckit-blueprint helper: turns one blueprint into spec-kit artifacts, one epic at a time.

Standard library only, so it runs under any Python 3.9+ (including the interpreter spec-kit's
event dispatcher uses for Claude Code hooks).

Usage (from the project root; the extension installs this file under
.specify/extensions/blueprint/scripts/):

    blueprint.py status [--json | --brief]   where the project stands and the next step
    blueprint.py compile E03 [--force]       write specs/NNN-e03-<slug>/ and make it the active feature
    blueprint.py bootstrap                   constitution, CLAUDE.md block, REVIEW-CHECKLIST, DECISIONS
    blueprint.py section 14.4 [13.4 ...]     print blueprint sections by number (read less, not all)
    blueprint.py find ENT-Order [SCR-03 ...] print the blueprint definitions of IDs
    blueprint.py stale                       compiled epics whose blueprint text changed since compile
    blueprint.py accept E01 --note "…"       record that a built epic stays as built after a blueprint change
    blueprint.py refs                        per epic: IDs that compile can or cannot resolve (exit 1 if any cannot)
    blueprint.py lint                        the structural linter, then refs
    blueprint.py epics                       epic and story IDs in blueprint order
    blueprint.py hook session-start          Claude Code SessionStart: one short status block
    blueprint.py hook guard                  Claude Code PreToolUse: block hand edits of compiled files

Why a script and not the model: every build session used to search a 100-page blueprint for the
few sections its epic needs, and that search was paid for again on every call of the session.
Resolving the references once, deterministically, at compile time is cheaper and cannot miss.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

EXT_ID = "blueprint"
TRACE_FILE = ".blueprint.json"
GENERATED_MARK = "speckit-blueprint:generated"
CLAUDE_START = "<!-- speckit-blueprint:start -->"
CLAUDE_END = "<!-- speckit-blueprint:end -->"
# Managed block inside a constitution the project owns (constitution_mode: append).
RULES_START = "<!-- speckit-blueprint:rules:start -->"
RULES_END = "<!-- speckit-blueprint:rules:end -->"
# Placeholder that `specify init` leaves in its template constitution.
TEMPLATE_MARK = "[PROJECT_NAME]"
COMPILED_FILES = ("spec.md", "plan.md", "research.md", "data-model.md", "quickstart.md")

DEFAULTS = {
    "blueprint_path": "docs/BLUEPRINT.md",
    "specs_dir": "specs",
    # Sections copied into .specify/memory/constitution.md (read by tasks and implement).
    "constitution_sections": ["13.2", "13.5", "13.6", "13.7", "13.9", "13.10", "14.2", "14.3", "14.8", "12.10"],
    # Sections copied into every epic's plan.md "Technical Context".
    "plan_sections": ["12.2", "13.1", "13.3", "13.4"],
    # Second-level resolution: IDs of these types found inside resolved definitions are
    # resolved too (a flow names its copy lines, an edge case names its copy lines).
    "second_level_types": ["CP", "EC"],
    # own: bootstrap writes the whole constitution. append: it keeps the project's constitution and
    # maintains one managed block in it. auto: own for a missing or template constitution, else append.
    "constitution_mode": "auto",
    # append mode: when the managed block is added or its rules change, bump the project's constitution
    # version (minor | patch | none), set Last Amended and add a Sync Impact Report line, as Spec Kit's
    # constitution governance expects.
    "constitution_version_bump": "minor",
    "guard": True,
}

# --------------------------------------------------------------------------------------------
# IDs

ID_PATTERNS = [
    ("CP", r"CP-[A-Za-z0-9]+-\d+"),
    ("SCR", r"SCR-\d+"),
    ("ENT", r"ENT-[A-Z][A-Za-z0-9]*"),
    ("API", r"API-\d+"),
    ("INT", r"INT-[a-z0-9][a-z0-9-]*[a-z0-9]"),
    ("EC", r"EC-[A-Z0-9]+-\d+"),
    ("F", r"F-\d{2,}"),
    ("FF", r"FF-\d+"),
    ("AD", r"AD-\d+"),
    ("DR", r"DR-\d+"),
    ("OQ", r"OQ-\d+"),
    ("R", r"R-\d+"),
    ("S", r"S-\d+"),
    ("M", r"M-\d+(?:\.\d+)?"),
    ("CE", r"CE-\d+"),
    ("G", r"G\d+"),
    ("AP", r"AP\d+"),
    # P50/P75/P90/P95/P99/P999 are percentiles, not personas.
    ("P", r"P(?!(?:50|75|90|95|99|999)\b)\d{1,2}"),
]
ID_ALT = "|".join(p for _, p in ID_PATTERNS)
ID_RE = re.compile(r"(?<![A-Za-z0-9_-])(" + ID_ALT + r")(?![A-Za-z0-9_])")
BOLD_ID_RE = re.compile(r"^\*\*(" + ID_ALT + r")(?![A-Za-z0-9_])")
TYPE_RES = [(t, re.compile(r"^" + p + r"$")) for t, p in ID_PATTERNS]

# "SCR-01 to SCR-06", "CP-SCR20-1 to CP-SCR20-12", "EC-BOT-01 to 04", "CP-SCR03-1…7"
RANGE_RE = re.compile(
    r"((?:CP-[A-Za-z0-9]+|EC-[A-Z0-9]+|SCR|API|F|FF|AD|DR|OQ|R|S|CE)-)(\d+)"
    r"\s*(?:to|through|…|\.\.\.|–)\s*(?:\1)?(\d+)(?![\d.])"
)
WILDCARD_RE = re.compile(r"((?:CP-[A-Za-z0-9]+|EC-[A-Z0-9]+)-)\*")

REFS_HINT = (
    "Define each unresolved ID once, outside the Epics section, in one of three shapes: a heading that starts "
    "with it ('### F-03 — …'), a paragraph that starts with it in bold ('**ENT-Order** …'), or a table row "
    "whose first cell is it ('| CP-SCR04-2 | …'). Put it in its home section (copy in §11, entities in §12.4, "
    "edge cases in §15, critical e2e paths CE-n in §14.3, …). See references/speckit-flow.md §1."
)

EPIC_RE = re.compile(r"^## Epic (\d{2})\s*[—–-]\s*(.+?)\s*$")
STORY_RE = re.compile(r"^### (E(\d{2})-S(\d{2}))\s*[—–-]\s*(.+?)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SECTION_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s")
EPIC_FOOTER_RE = re.compile(r"^\*\*(Epic-level tests|Definition of Done|Session handoff checklist)\*\*")
TASK_LINE_RE = re.compile(r"^\s*-\s*\[( |x|X)\]\s*T\d+")
VERIFY_RE = re.compile(r"\[VERIFY-AT-BUILD\]")


def id_type(token: str) -> str | None:
    for t, rx in TYPE_RES:
        if rx.match(token):
            return t
    return None


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------------------------
# Project and config


def find_root(start: Path) -> Path:
    p = start.resolve()
    for cand in (p, *p.parents):
        if (cand / ".specify").is_dir():
            return cand
    return p


def _parse_scalar(v: str):
    v = v.strip()
    if v in ("true", "True", "yes"):
        return True
    if v in ("false", "False", "no"):
        return False
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [_parse_scalar(x) for x in inner.split(",")] if inner else []
    return v


def load_simple_yaml(path: Path) -> dict:
    """The subset this extension's config uses: top-level `key: value` and `key:` + `- item` lists."""
    out: dict = {}
    if not path.is_file():
        return out
    key = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        if not line[0].isspace() and ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            out[key] = _parse_scalar(val) if val.strip() else []
        elif key and line.strip().startswith("- "):
            if not isinstance(out.get(key), list):
                out[key] = []
            out[key].append(_parse_scalar(line.strip()[2:]))
    return out


def load_config(root: Path) -> dict:
    cfg = dict(DEFAULTS)
    ext_dir = root / ".specify" / "extensions" / EXT_ID
    for name in (f"{EXT_ID}-config.yml", f"{EXT_ID}-config.local.yml"):
        cfg.update({k: v for k, v in load_simple_yaml(ext_dir / name).items() if v != []})
    env_path = os.environ.get("SPECKIT_BLUEPRINT_BLUEPRINT_PATH")
    if env_path:
        cfg["blueprint_path"] = env_path
    return cfg


# --------------------------------------------------------------------------------------------
# Blueprint model


class Heading:
    def __init__(self, idx: int, level: int, text: str):
        self.idx, self.level, self.text = idx, level, text
        self.end = idx  # exclusive, set later
        m = SECTION_NUM_RE.match(text)
        self.number = m.group(1) if m else None


class Unit:
    """A span of blueprint text that defines one or more IDs."""

    def __init__(self, kind: str, start: int, end: int, header: tuple[int, int] | None = None):
        self.kind, self.start, self.end, self.header = kind, start, end, header

    def text(self, lines: list[str]) -> str:
        return "\n".join(lines[self.start : self.end]).rstrip()

    def contains(self, other: "Unit") -> bool:
        return self.start <= other.start and other.end <= self.end and self is not other


class Blueprint:
    def __init__(self, path: Path):
        self.path = path
        self.raw = path.read_text(encoding="utf-8")
        self.lines = self.raw.split("\n")
        self.sha = sha(self.raw)
        self.headings: list[Heading] = []
        self._scan_headings()
        self.epics = self._scan_epics()
        self.defs: dict[str, list[Unit]] = {}
        self._index_definitions()

    # -- structure

    def _scan_headings(self) -> None:
        fenced = False
        for i, line in enumerate(self.lines):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            m = HEADING_RE.match(line)
            if m:
                self.headings.append(Heading(i, len(m.group(1)), m.group(2)))
        for k, h in enumerate(self.headings):
            h.end = len(self.lines)
            for nxt in self.headings[k + 1 :]:
                if nxt.level <= h.level:
                    h.end = nxt.idx
                    break

    def title(self) -> str:
        for h in self.headings:
            if h.level == 1:
                return re.split(r"\s+[—–-]\s+", h.text)[0].strip()
        return self.path.stem

    def section(self, key: str) -> Heading | None:
        key = key.strip().rstrip(".")
        for h in self.headings:
            if h.number == key:
                return h
        low = key.lower()
        for h in self.headings:
            if h.level <= 3 and (f"({low})" in h.text.lower() or h.text.lower().endswith(low)):
                return h
        return None

    def section_text(self, key: str) -> str | None:
        h = self.section(key)
        return "\n".join(self.lines[h.idx : h.end]).rstrip() if h else None

    def epics_zone(self) -> tuple[int, int]:
        """Line span of the Epics section (§17), where IDs are used rather than defined."""
        starts = [h for h in self.headings if h.level == 2 and EPIC_RE.match(self.lines[h.idx])]
        if not starts:
            return (0, 0)
        first = starts[0].idx
        sec = self.section("Epics")
        if sec and sec.idx < first:
            first = sec.idx
        end = len(self.lines)
        for h in self.headings:
            if h.level == 2 and h.idx > starts[-1].idx and not EPIC_RE.match(self.lines[h.idx]):
                end = h.idx
                break
        return (first, end)

    def _scan_epics(self) -> list[dict]:
        epics = []
        for h in self.headings:
            m = EPIC_RE.match(self.lines[h.idx]) if h.level == 2 else None
            if not m:
                continue
            start, end = h.idx, h.end
            stories = []
            story_heads = [s for s in self.headings if s.level == 3 and start < s.idx < end]
            footer = end
            first_story = next((s.idx for s in story_heads if STORY_RE.match(self.lines[s.idx])), None)
            if first_story is not None:
                for i in range(first_story + 1, end):
                    if EPIC_FOOTER_RE.match(self.lines[i]):
                        footer = i
                        break
            for s in story_heads:
                sm = STORY_RE.match(self.lines[s.idx])
                if not sm:
                    continue
                s_end = min(s.end, footer) if s.idx < footer else s.end
                stories.append({"id": sm.group(1), "title": sm.group(4), "start": s.idx, "end": s_end})
            header_end = stories[0]["start"] if stories else end
            epics.append(
                {
                    "id": f"E{m.group(1)}",
                    "num": int(m.group(1)),
                    "title": m.group(2),
                    "start": start,
                    "end": end,
                    "header": (start + 1, header_end),
                    "footer": (footer, end) if stories else (end, end),
                    "stories": stories,
                }
            )
        return epics

    def epic(self, key: str) -> dict | None:
        m = re.match(r"^[Ee]?(\d{1,2})$", key.strip())
        if not m:
            return None
        num = int(m.group(1))
        return next((e for e in self.epics if e["num"] == num), None)

    def epic_text(self, epic: dict) -> str:
        return "\n".join(self.lines[epic["start"] : epic["end"]])

    # -- definitions

    def _add(self, ident: str, unit: Unit) -> None:
        self.defs.setdefault(ident, []).append(unit)

    def _index_definitions(self) -> None:
        z0, z1 = self.epics_zone()
        in_zone = lambda i: z0 <= i < z1  # noqa: E731
        appendix = next((h.idx for h in self.headings if h.level == 2 and h.text.lower().startswith("appendix")), None)

        # a) headings whose title starts with an ID ("#### DR-01 — …", "### 11.1 SCR-01 Welcome")
        for h in self.headings:
            if in_zone(h.idx) or (appendix is not None and h.idx >= appendix) or h.level < 3:
                continue
            title = SECTION_NUM_RE.sub("", h.text, count=1) if h.number else h.text
            m = ID_RE.match(title.strip())
            if m:
                self._add(m.group(1), Unit("heading", h.idx, h.end))

        # b) bold-led blocks ("**ENT-Order** (`order`, owner …)", "**INT-sms — …**")
        bold_id = BOLD_ID_RE
        heading_idx = {h.idx for h in self.headings}
        i = 0
        fenced = False
        while i < len(self.lines):
            line = self.lines[i]
            if line.lstrip().startswith("```"):
                fenced = not fenced
            if fenced or in_zone(i) or (appendix is not None and i >= appendix):
                i += 1
                continue
            m = bold_id.match(line)
            if m:
                j = i + 1
                while j < len(self.lines) and j not in heading_idx and not bold_id.match(self.lines[j]):
                    j += 1
                self._add(m.group(1), Unit("block", i, j))
            i += 1

        # c) table rows whose first cell is an ID
        header = None
        for i, line in enumerate(self.lines):
            s = line.strip()
            if not s.startswith("|"):
                header = None
                continue
            if i + 1 < len(self.lines) and re.match(r"^\|\s*:?-{2,}", self.lines[i + 1].strip()):
                header = (i, i + 2)
                continue
            if header is None or in_zone(i) or (appendix is not None and i >= appendix):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            first = re.sub(r"[*`]", "", cells[0]).strip() if cells else ""
            # "EC-BOT-10" or "EC-BOT-10 (new)": the cell starts with exactly one ID
            m = ID_RE.match(first)
            if m and (len(first) == m.end() or first[m.end()] in " ("):
                self._add(m.group(1), Unit("row", i, i + 1, header))

    def resolve(self, ids: list[str]) -> list[tuple[str, Unit]]:
        out = []
        for ident in ids:
            for u in self.defs.get(ident, []):
                out.append((ident, u))
        return out


def extract_ids(text: str, known: dict[str, list[Unit]] | None = None) -> list[str]:
    found: list[str] = []
    seen = set()

    def add(x: str) -> None:
        if x not in seen:
            seen.add(x)
            found.append(x)

    for m in RANGE_RE.finditer(text):
        prefix, a, b = m.group(1), m.group(2), m.group(3)
        width = len(a)
        lo, hi = int(a), int(b)
        if 0 <= hi - lo <= 200:
            for n in range(lo, hi + 1):
                add(f"{prefix}{str(n).zfill(width)}")
    if known:
        for m in WILDCARD_RE.finditer(text):
            for k in known:
                if k.startswith(m.group(1)):
                    add(k)
    for m in ID_RE.finditer(text):
        add(m.group(1))
    return found


# --------------------------------------------------------------------------------------------
# Rendering helpers


def render_units(bp: Blueprint, pairs: list[tuple[str, Unit]]) -> str:
    """Render definition units, merging table rows that share a header and dropping nested spans."""
    units: list[Unit] = []
    seen_spans = set()
    for _, u in pairs:
        if (u.start, u.end) not in seen_spans:
            seen_spans.add((u.start, u.end))
            units.append(u)
    units = [u for u in units if not any(o.contains(u) for o in units)]
    units.sort(key=lambda u: u.start)
    chunks: list[str] = []
    last_header = None
    for u in units:
        if u.kind == "row":
            if u.header != last_header:
                hs, he = u.header
                chunks.append("\n".join(bp.lines[hs:he]))
                last_header = u.header
            chunks[-1] += "\n" + u.text(bp.lines)
        else:
            last_header = None
            chunks.append(demote(u.text(bp.lines), 4))
    return "\n\n".join(chunks)


def demote(text: str, min_level: int) -> str:
    """Shift headings so the shallowest becomes `min_level` (keeps nesting, avoids clashes)."""
    levels = [len(m.group(1)) for m in re.finditer(r"^(#{1,6})\s", text, re.M)]
    if not levels:
        return text
    shift = max(0, min_level - min(levels))
    return re.sub(r"^(#{1,6})(\s)", lambda m: "#" * min(6, len(m.group(1)) + shift) + m.group(2), text, flags=re.M)


def strip_label_block(text: str, label: str) -> str:
    """Remove a `**Label**` block (until the next bold label at line start) from a story."""
    out, skip = [], False
    for line in text.split("\n"):
        if re.match(r"^\*\*[A-Z][^*]*\*\*", line):
            skip = line.startswith(f"**{label}**")
        if not skip:
            out.append(line)
    return "\n".join(out)


def label_block(text: str, label: str) -> str:
    out, keep = [], False
    for line in text.split("\n"):
        if re.match(r"^\*\*[A-Z][^*]*\*\*", line):
            keep = line.startswith(f"**{label}**")
        if keep:
            out.append(line)
    return "\n".join(out).strip()


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return "-".join(s.split("-")[:5]) or "epic"


def gen_header(rel_blueprint: str, bp_sha: str, what: str) -> str:
    return (
        f"<!-- {GENERATED_MARK} — {what} compiled from {rel_blueprint} (sha {bp_sha}). "
        "Do not edit by hand: change the blueprint through /speckit-blueprint-amend and recompile. -->"
    )


# --------------------------------------------------------------------------------------------
# Compile


def find_feature_dir(root: Path, cfg: dict, epic_id: str) -> Path | None:
    specs = root / cfg["specs_dir"]
    if not specs.is_dir():
        return None
    for d in sorted(specs.iterdir()):
        t = d / TRACE_FILE
        if t.is_file():
            try:
                if json.loads(t.read_text(encoding="utf-8")).get("epic") == epic_id:
                    return d
            except (OSError, ValueError):
                continue
    return None


def next_feature_number(root: Path, cfg: dict) -> int:
    specs = root / cfg["specs_dir"]
    hi = 0
    if specs.is_dir():
        for d in specs.iterdir():
            m = re.match(r"^(\d{3,})-", d.name)
            if m and not re.match(r"^\d{8}-\d{6}-", d.name):
                hi = max(hi, int(m.group(1)))
    return hi + 1


def group(pairs: list[tuple[str, Unit]], types: set[str]) -> list[tuple[str, Unit]]:
    return [(i, u) for i, u in pairs if id_type(i) in types]


def epic_refs(bp: Blueprint, epic: dict, cfg: dict) -> tuple[list[str], list[tuple[str, Unit]], list[str]]:
    """IDs an epic uses, their definition units (two levels deep for some types), and the unresolved ones."""
    ids = [i for i in extract_ids(bp.epic_text(epic), bp.defs) if id_type(i)]
    level1 = bp.resolve(ids)
    second_types = set(cfg.get("second_level_types") or [])
    extra: list[str] = []
    if second_types:
        for ident, u in level1:
            if id_type(ident) in {"F", "SCR", "EC"}:
                for x in extract_ids(u.text(bp.lines), bp.defs):
                    if id_type(x) in second_types and x not in ids and x not in extra:
                        extra.append(x)
    pairs = level1 + bp.resolve(extra)
    # Goals (G1…) are often defined in prose; their absence is not worth a defect.
    unresolved = sorted({i for i in ids if i not in bp.defs and id_type(i) != "G"})
    return ids, pairs, unresolved


def compile_epic(root: Path, cfg: dict, bp: Blueprint, epic_key: str, force: bool = False) -> dict:
    epic = bp.epic(epic_key)
    if not epic:
        raise SystemExit(f"error: no '## Epic {epic_key}' in {bp.path}")
    rel_bp = os.path.relpath(bp.path, root)
    eid, etitle = epic["id"], epic["title"]
    lines = bp.lines

    feature = find_feature_dir(root, cfg, eid)
    if feature is None:
        # E00 → 001, E01 → 002 … when that prefix is free, so folders sort like the blueprint.
        num = epic["num"] + 1
        specs = root / cfg["specs_dir"]
        if specs.is_dir() and any(d.name.startswith(f"{num:03d}-") for d in specs.iterdir()):
            num = next_feature_number(root, cfg)
        feature = root / cfg["specs_dir"] / f"{num:03d}-{eid.lower()}-{slugify(etitle)}"
    trace_path = feature / TRACE_FILE
    if trace_path.is_file() and (feature / "tasks.md").is_file() and not force:
        tasks = (feature / "tasks.md").read_text(encoding="utf-8")
        if re.search(r"^\s*-\s*\[[xX]\]", tasks, re.M):
            raise SystemExit(
                f"error: {feature.relative_to(root)} already has completed tasks. Recompiling would "
                "change the spec under finished work. Pass --force only if that is intended "
                "(then regenerate tasks.md with /speckit-tasks)."
            )

    epic_text = bp.epic_text(epic)
    ids, pairs, unresolved = epic_refs(bp, epic, cfg)

    header_text = "\n".join(lines[epic["header"][0] : epic["header"][1]]).strip()
    footer_text = "\n".join(lines[epic["footer"][0] : epic["footer"][1]]).strip()
    today = _dt.date.today().isoformat()
    branch = feature.name

    # ---- spec.md
    spec = [
        gen_header(rel_bp, bp.sha, "spec.md"),
        f"# Feature Specification: {eid} — {etitle}",
        "",
        f"**Feature Branch**: `{branch}`",
        "",
        f"**Created**: {today}",
        "",
        f"**Status**: Compiled from blueprint ({eid})",
        "",
        f"**Input**: {rel_bp} — Epic {eid[1:]}. Acceptance criteria, copy IDs and edge cases below are binding verbatim.",
        "",
        "## Epic Context",
        "",
        header_text,
        "",
        "## User Scenarios & Testing *(mandatory)*",
        "",
        "Priorities follow the blueprint's story order, which is its dependency order: P1 is built first.",
        "",
    ]
    for n, st in enumerate(epic["stories"], 1):
        body = "\n".join(lines[st["start"] + 1 : st["end"]]).strip()
        body = strip_label_block(body, "Tasks")
        spec += [
            f"### User Story {n} - {st['title']} (Priority: P{n})",
            "",
            f"**Blueprint ID**: {st['id']}",
            "",
            body.replace("**Acceptance Criteria**", "**Acceptance Scenarios** (Acceptance Criteria)", 1),
            "",
            f"**Independent Test**: the **Tests** block of {st['id']} above.",
            "",
        ]
    ec = group(pairs, {"EC"})
    spec += ["### Edge Cases", "", render_units(bp, ec) if ec else "Story-level edge cases above; no register entries referenced.", ""]
    spec += [
        "## Requirements *(mandatory)*",
        "",
        "### Functional Requirements",
        "",
        "Every acceptance criterion above (`<story> AC-n`) is a functional requirement. Copy is used by ID "
        "(`CP-…`) exactly as defined under Product Context; no improvised strings.",
        "",
    ]
    ents = [i for i in ids if id_type(i) == "ENT"]
    if ents:
        spec += ["### Key Entities", ""] + [f"- **{e}** — see data-model.md" for e in ents] + [""]
    spec += ["## Success Criteria *(mandatory)*", "", footer_text or "See each story's **Story DoD**.", ""]
    ctx_groups = [
        ("Personas", {"P", "AP"}),
        ("Flows", {"F"}),
        ("Screens and copy", {"SCR", "CP"}),
        ("Goals and metrics", {"G", "M", "CE"}),
    ]
    ctx = [(title, group(pairs, t)) for title, t in ctx_groups]
    if any(g for _, g in ctx):
        spec += ["## Product Context (resolved from the blueprint)", ""]
        for title, g in ctx:
            if g:
                spec += [f"### {title}", "", render_units(bp, g), ""]
    oq = group(pairs, {"OQ"})
    spec += ["## Assumptions", "", "Open questions that touch this epic, with the default to use if still unanswered:", ""]
    spec += [render_units(bp, oq) if oq else "None referenced.", ""]

    # ---- plan.md
    plan = [
        gen_header(rel_bp, bp.sha, "plan.md"),
        f"# Implementation Plan: {eid} — {etitle}",
        "",
        f"**Branch**: `{branch}` | **Date**: {today} | **Spec**: [spec.md](spec.md)",
        "",
        f"**Input**: compiled from {rel_bp}. Architecture, stack and conventions are already decided there; "
        "this plan does not reopen them.",
        "",
        "## Summary",
        "",
        label_block(header_text, "Goal") or etitle,
        "",
        "## Technical Context",
        "",
    ]
    for key in cfg.get("plan_sections") or []:
        t = bp.section_text(str(key))
        if t:
            plan += [demote(t, 3), ""]
    plan += [
        "## Constitution Check",
        "",
        "The constitution (`.specify/memory/constitution.md`) holds the project's principles and the rules "
        "bootstrap compiled from the same blueprint; this plan complies with both. No violations are planned; any deviation needs a DR in `docs/DECISIONS.md` and, if it changes "
        "behaviour, an amendment through `/speckit-blueprint-amend`.",
        "",
        "## Project Structure",
        "",
        "### Documentation (this feature)",
        "",
        "```text",
        f"{cfg['specs_dir']}/{branch}/",
        "├── spec.md          # stories, ACs, edge cases, copy (compiled)",
        "├── plan.md          # this file (compiled)",
        "├── research.md      # decisions, drivers, sources, open questions (compiled)",
        "├── data-model.md    # entities this epic touches (compiled)",
        "├── quickstart.md    # how to verify the epic (compiled)",
        "├── contracts/       # API rows and integration cards (compiled)",
        "├── tasks.md         # /speckit-tasks output",
        "└── review.md        # /speckit-blueprint-review output (handoff)",
        "```",
        "",
        "### Source Code (repository root)",
        "",
        "Use the repository layout and module map in Technical Context above; do not invent new top-level folders.",
        "",
        "## Blueprint Task Seeds",
        "",
        "Instructions for `/speckit-tasks`: build one phase per user story in the order below. Keep each "
        "blueprint task ID in its task description (for example `- [ ] T007 [US2] E01-S02-T3 …`), keep their "
        "order, and put the story's tests (its **Tests** block in spec.md) before its implementation tasks. "
        "Add setup or foundational tasks only when the epic's preconditions need them.",
        "",
    ]
    for n, st in enumerate(epic["stories"], 1):
        body = "\n".join(lines[st["start"] + 1 : st["end"]])
        tasks = label_block(body, "Tasks")
        tasks = "\n".join(tasks.split("\n")[1:]).strip() if tasks else "- (no blueprint tasks; derive from the ACs)"
        plan += [f"### US{n} — {st['id']} {st['title']}", "", tasks, ""]
    verify = sorted({ln.strip() for ln in epic_text.split("\n") if VERIFY_RE.search(ln)})
    plan += [
        "## Preconditions and VERIFY-AT-BUILD",
        "",
        label_block(header_text, "Preconditions for the session") or "None stated.",
        "",
    ]
    if verify:
        plan += ["Lines in this epic that carry `[VERIFY-AT-BUILD]` (re-check before building on them):", ""]
        plan += [f"- {v.lstrip('- ')[:600]}" for v in verify] + [""]
    risks = group(pairs, {"R"})
    if risks:
        plan += ["## Risks", "", render_units(bp, risks), ""]
    plan += ["## Complexity Tracking", "", "None — complexity decisions are recorded as DRs in research.md.", ""]

    # ---- research.md
    research = [gen_header(rel_bp, bp.sha, "research.md"), f"# Research: {eid} — {etitle}", ""]
    for title, types in [
        ("Decisions", {"DR"}),
        ("Architecture drivers", {"AD"}),
        ("Fitness functions", {"FF"}),
        ("Sources", {"S"}),
    ]:
        g = group(pairs, types)
        if g:
            research += [f"## {title}", "", render_units(bp, g), ""]
    if len(research) == 3:
        research += ["No decisions, drivers or sources are referenced by this epic.", ""]

    # ---- data-model.md
    ent = group(pairs, {"ENT"})
    data_model = None
    if ent:
        data_model = [gen_header(rel_bp, bp.sha, "data-model.md"), f"# Data Model: {eid} — {etitle}", ""]
        dm = bp.section("12.4")
        if dm:
            pre = []
            for ln in lines[dm.idx + 1 : dm.end]:
                if ln.startswith("**ENT-") or ln.startswith("|") or HEADING_RE.match(ln):
                    break
                pre.append(ln)
            if "".join(pre).strip():
                data_model += ["## Conventions", "", "\n".join(pre).strip(), ""]
        data_model += ["## Entities", "", render_units(bp, ent), ""]

    # ---- contracts/
    contracts = {}
    api = group(pairs, {"API"})
    if api:
        body = [gen_header(rel_bp, bp.sha, "contracts/api.md"), f"# API Contracts: {eid}", ""]
        sec = bp.section("12.5")
        if sec:
            pre = []
            for ln in lines[sec.idx + 1 : sec.end]:
                if ln.startswith("|") or HEADING_RE.match(ln):
                    break
                pre.append(ln)
            if "".join(pre).strip():
                body += ["\n".join(pre).strip(), ""]
        body += [render_units(bp, api), ""]
        contracts["api.md"] = body
    ints = group(pairs, {"INT"})
    if ints:
        contracts["integrations.md"] = [
            gen_header(rel_bp, bp.sha, "contracts/integrations.md"),
            f"# Integrations: {eid}",
            "",
            render_units(bp, ints),
            "",
        ]

    # ---- quickstart.md
    manual = []
    for st in epic["stories"]:
        for ln in lines[st["start"] : st["end"]]:
            if re.match(r"^\s*-\s*Manual\b", ln):
                manual.append(f"- {st['id']}: {ln.strip().lstrip('- ').strip()}")
    quick = [
        gen_header(rel_bp, bp.sha, "quickstart.md"),
        f"# Quickstart: verify {eid} — {etitle}",
        "",
        "## Epic-level verification",
        "",
        label_block(footer_text, "Epic-level tests") or "Run the full `check` and every story's tests.",
        "",
        "## Manual checks",
        "",
        "\n".join(manual) if manual else "None beyond the Definition of Done in spec.md.",
        "",
    ]

    # ---- write
    feature.mkdir(parents=True, exist_ok=True)
    written = {}

    def write(rel: str, parts: list[str]) -> None:
        p = feature / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(parts).rstrip() + "\n"
        p.write_text(text, encoding="utf-8")
        written[rel] = len(text.encode("utf-8"))

    write("spec.md", spec)
    write("plan.md", plan)
    write("research.md", research)
    write("quickstart.md", quick)
    if data_model:
        write("data-model.md", data_model)
    elif (feature / "data-model.md").is_file():
        (feature / "data-model.md").unlink()
    for name, parts in contracts.items():
        write(f"contracts/{name}", parts)

    unit_hashes = {}
    for ident, u in pairs:
        unit_hashes.setdefault(ident, sha(u.text(lines)))
    trace = {
        "epic": eid,
        "title": etitle,
        "blueprint": rel_bp,
        "blueprint_sha": bp.sha,
        "epic_sha": sha(epic_text),
        "units": unit_hashes,
        "unresolved": unresolved,
        "compiled_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "files": written,
    }
    trace_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rel_feature = feature.relative_to(root).as_posix()
    (root / ".specify").mkdir(exist_ok=True)
    (root / ".specify" / "feature.json").write_text(
        json.dumps({"feature_directory": rel_feature}) + "\n", encoding="utf-8"
    )
    return {
        "epic": eid,
        "title": etitle,
        "feature_directory": rel_feature,
        "files": written,
        "total_bytes": sum(written.values()),
        "blueprint_bytes": len(bp.raw.encode("utf-8")),
        "resolved_ids": len(unit_hashes),
        "unresolved_ids": unresolved,
    }


# --------------------------------------------------------------------------------------------
# Status


def accept_change(root: Path, cfg: dict, bp: "Blueprint", epic_key: str, note: str) -> dict:
    """Mark the blueprint changes under a compiled epic as reviewed: the epic stays as built.

    The trace's hashes move to the current blueprint text, so status stops reporting the change; the
    compiled files are left as they were, and the decision is kept in the trace's `accepted` list.
    """
    eid = epic_key.upper() if epic_key.upper().startswith("E") else f"E{int(epic_key):02d}"
    d = find_feature_dir(root, cfg, eid)
    if d is None:
        raise SystemExit(f"error: {eid} has no compiled feature folder")
    tpath = d / TRACE_FILE
    trace = json.loads(tpath.read_text(encoding="utf-8"))
    changed = stale_units(bp, trace)
    if not changed:
        return {"epic": eid, "accepted": [], "note": "nothing changed since compile"}
    epic = bp.epic(eid[1:])
    if epic is None:
        raise SystemExit(f"error: {eid} is no longer in the blueprint")
    trace["epic_sha"] = sha(bp.epic_text(epic))
    for ident in list((trace.get("units") or {}).keys()):
        units = bp.defs.get(ident)
        if units:
            trace["units"][ident] = sha(units[0].text(bp.lines))
    trace.setdefault("accepted", []).append({
        "date": _dt.date.today().isoformat(), "blueprint_sha": bp.sha, "changed": changed, "note": note,
    })
    tpath.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"epic": eid, "feature_directory": d.relative_to(root).as_posix(), "accepted": changed, "note": note}


def task_counts(tasks: Path) -> tuple[int, int]:
    if not tasks.is_file():
        return (0, 0)
    total = done = 0
    for ln in tasks.read_text(encoding="utf-8").split("\n"):
        m = TASK_LINE_RE.match(ln)
        if m:
            total += 1
            done += m.group(1) in "xX"
    return (total, done)


def review_status(review: Path) -> str | None:
    if not review.is_file():
        return None
    m = re.search(r"Status:\s*\**\s*(DONE|IN PROGRESS)", review.read_text(encoding="utf-8"))
    return m.group(1) if m else "UNKNOWN"


def stale_units(bp: Blueprint, trace: dict) -> list[str]:
    changed = []
    epic = bp.epic(trace.get("epic", "")[1:] if trace.get("epic") else "")
    if epic is None:
        return ["<epic removed>"]
    if sha(bp.epic_text(epic)) != trace.get("epic_sha"):
        changed.append(trace["epic"])
    for ident, h in (trace.get("units") or {}).items():
        units = bp.defs.get(ident)
        if not units or sha(units[0].text(bp.lines)) != h:
            changed.append(ident)
    return changed


def constitution_state(root: Path) -> str:
    c = root / ".specify" / "memory" / "constitution.md"
    if not c.is_file():
        return "missing"
    text = c.read_text(encoding="utf-8")
    if RULES_START in text:
        return "appended"
    return "compiled" if GENERATED_MARK in text else "not-from-blueprint"


def rules_span(text: str) -> tuple[int, int] | None:
    """Character span of the managed rules block in a project-owned constitution, markers included."""
    i = text.find(RULES_START)
    j = text.find(RULES_END, i + 1) if i >= 0 else -1
    return (i, j + len(RULES_END)) if i >= 0 and j >= 0 else None


def project_status(root: Path, cfg: dict) -> dict:
    bp_path = root / cfg["blueprint_path"]
    st: dict = {"root": str(root), "blueprint": cfg["blueprint_path"]}
    if not bp_path.is_file():
        st.update(state="no-blueprint", next={"command": "speckit-blueprint-discover", "why": "No blueprint yet: start product discovery."})
        return st
    bp = Blueprint(bp_path)
    st["product"] = bp.title()
    st["constitution"] = constitution_state(root)
    active = None
    fj = root / ".specify" / "feature.json"
    if fj.is_file():
        try:
            active = json.loads(fj.read_text(encoding="utf-8")).get("feature_directory")
        except ValueError:
            active = None
    st["active_feature"] = active
    epics = []
    for e in bp.epics:
        d = find_feature_dir(root, cfg, e["id"])
        row = {"epic": e["id"], "title": e["title"], "stories": len(e["stories"])}
        if d is None:
            row["state"] = "not-compiled"
        else:
            row["feature_directory"] = d.relative_to(root).as_posix()
            total, done = task_counts(d / "tasks.md")
            rv = review_status(d / "review.md")
            try:
                trace = json.loads((d / TRACE_FILE).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                trace = {}
            changed = stale_units(bp, trace)
            row.update(tasks_total=total, tasks_done=done, review=rv)
            if rv == "DONE":
                row["state"] = "done"
            elif total and done == total:
                row["state"] = "implemented"
            elif done:
                row["state"] = "in-progress"
            elif total:
                row["state"] = "tasked"
            else:
                row["state"] = "compiled"
            if changed and row["state"] in ("compiled", "tasked"):
                row["state"] = "stale"
            if changed:
                row["changed_since_compile"] = changed[:20]
        epics.append(row)
    st["epics"] = epics
    st["state"] = "building"

    def nxt(cmd: str, why: str, epic: str | None = None, new_session: bool = False) -> dict:
        d = {"command": cmd, "why": why, "new_session": new_session}
        if epic:
            d["epic"] = epic
        return d

    if st["constitution"] not in ("compiled", "appended"):
        st["next"] = nxt("speckit-blueprint-bootstrap", "Blueprint exists but the constitution and project files are not compiled from it yet.")
        return st
    for row in epics:
        s = row["state"]
        if s == "done":
            continue
        if s in ("not-compiled", "stale"):
            why = "Blueprint changed after this epic was compiled; recompile it." if s == "stale" else f"Next epic: {row['epic']} — {row['title']}."
            st["next"] = nxt("speckit-blueprint-compile", why, row["epic"])
        elif s == "compiled":
            st["next"] = nxt("speckit-tasks", "Feature compiled; generate tasks.md, then run /speckit-analyze.", row["epic"])
        elif s in ("tasked", "in-progress"):
            st["next"] = nxt(
                "speckit-implement",
                f"{row['tasks_done']}/{row['tasks_total']} tasks done; continue implementation (start a fresh session if the current one is long).",
                row["epic"],
                new_session=(s == "tasked"),
            )
        elif s == "implemented":
            st["next"] = nxt("speckit-blueprint-review", "All tasks are checked; run the self-review and handoff.", row["epic"])
        if row.get("feature_directory") and row["feature_directory"] != active and st["next"]["command"] != "speckit-blueprint-compile":
            st["next"]["activate"] = row["feature_directory"]
        return st
    st["state"] = "all-done"
    st["next"] = nxt("speckit-blueprint-discover", "Every epic in the blueprint is done. New scope starts with discover in incremental mode.")
    return st


def brief(st: dict) -> str:
    if st.get("state") == "no-blueprint":
        return f"[speckit-blueprint] No blueprint at {st['blueprint']}. Next: /speckit-blueprint-discover with the idea."
    done = sum(1 for e in st.get("epics", []) if e["state"] == "done")
    total = len(st.get("epics", []))
    lines = [f"[speckit-blueprint] {st.get('product')}: {done}/{total} epics done. Blueprint: {st['blueprint']}."]
    cur = next((e for e in st.get("epics", []) if e["state"] != "done"), None)
    if cur:
        extra = ""
        if cur.get("tasks_total"):
            extra = f", tasks {cur['tasks_done']}/{cur['tasks_total']}"
        lines.append(f"Current: {cur['epic']} {cur['title']} — {cur['state']}{extra}.")
    n = st.get("next") or {}
    if n:
        tgt = f" {n['epic']}" if n.get("epic") and n["command"] == "speckit-blueprint-compile" else ""
        lines.append(f"Next: /{n['command']}{tgt} — {n['why']}")
    stale = [e["epic"] for e in st.get("epics", []) if e.get("changed_since_compile")]
    if stale:
        lines.append(f"Blueprint changed since compile for: {', '.join(stale)}.")
    lines.append("Workflow rules: use the speckit-blueprint-flow skill; never hand-edit compiled spec files.")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------
# Bootstrap


FIXED_PRINCIPLES = """### {n}I. The blueprint is the source of truth
`{bp}` decides what is built. {scope} are compiled from it and are never edited by hand.
When reality disagrees with the blueprint, the blueprint changes first, through `/speckit-blueprint-amend`
(an `A-nn` entry in its Amendments log), and affected epics are recompiled. No silent deviation.

### {n}II. Evidence or silence
Every claim about the outside world (library, version, service, regulation) is verified or tagged
`[ASSUMED]` / `[UNKNOWN → OQ-nn]`. Items tagged `[VERIFY-AT-BUILD]` are re-checked before code depends on them.

### {n}III. Tests first, gate always green
Each story's tests are written from its acceptance criteria and fail before the implementation exists.
`check` stays green after every task. The gate is never weakened to make a change pass; if it must change,
that is a decision record.

### {n}IV. Copy by ID, decisions by record
User-facing text comes from the blueprint's copy tables by `CP-` ID, never improvised. Any decision the
blueprint does not cover is recorded as `DR-nn` in `docs/DECISIONS.md` in the same commit.

### {n}V. Review before done
An epic is done only after `/speckit-blueprint-review` walked `docs/REVIEW-CHECKLIST.md` over its diff and
wrote `review.md` with `Status: DONE`."""


def bump_version(old: str | None) -> str:
    if not old:
        return "1.0.0"
    parts = (old.split(".") + ["0", "0", "0"])[:3]
    try:
        return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
    except ValueError:
        return "1.0.0"


def own_constitution(old: str, rel_bp: str, bp: "Blueprint", content_sha: str, body: list[str], cfg: dict, today: str) -> str:
    """The whole constitution, compiled from the blueprint (a new project)."""
    ver_m = re.search(r"\*\*Version\*\*:\s*([0-9.]+)", old) if GENERATED_MARK in old else None
    rat_m = re.search(r"\*\*Ratified\*\*:\s*([0-9-]+)", old) if GENERATED_MARK in old else None
    old_sha = re.search(r"content-sha ([0-9a-f]+)", old)
    if ver_m and old_sha and old_sha.group(1) == content_sha:
        version = ver_m.group(1)
    else:
        version = bump_version(ver_m.group(1) if ver_m else None)
    scope = f"Specs under `{cfg['specs_dir']}/`"
    return "\n".join([
        f"<!-- {GENERATED_MARK} — constitution compiled from {rel_bp} (sha {bp.sha}, content-sha {content_sha}). "
        "Do not edit by hand: change the blueprint, then run /speckit-blueprint-bootstrap. -->",
        f"# {bp.title()} Constitution",
        "",
        "## Core Principles",
        "",
        FIXED_PRINCIPLES.format(n="", bp=rel_bp, scope=scope),
        "",
        "## Engineering Rules (from the blueprint)",
        "",
        *body,
        "## Governance",
        "",
        f"This constitution supersedes other practice in this repository. It is regenerated from {rel_bp}; "
        "amend the blueprint, never this file. Plans and tasks must comply; a justified exception is a DR in "
        "`docs/DECISIONS.md`.",
        "",
        f"**Version**: {version} | **Ratified**: {rat_m.group(1) if rat_m else today} | **Last Amended**: {today}",
        "",
    ])


def append_rules(old: str, rel_bp: str, bp_sha: str, content_sha: str, body: list[str], cfg: dict) -> str:
    """A project-owned constitution with one managed block of blueprint rules; the rest is left alone."""
    scope = f"Feature folders under `{cfg['specs_dir']}/` that contain `{TRACE_FILE}`"
    block = "\n".join([
        RULES_START,
        f"<!-- Compiled from {rel_bp} (sha {bp_sha}, content-sha {content_sha}) by /speckit-blueprint-bootstrap. "
        "Edit the blueprint, not this block; the rest of this file belongs to the project. -->",
        "## Blueprint Rules (speckit-blueprint)",
        "",
        f"These rules apply only to features compiled from `{rel_bp}` (their folder contains `{TRACE_FILE}`). "
        "Every other feature follows this project's own workflow. They add to the principles above and never "
        "override them: where the two conflict, the principles above win.",
        "",
        FIXED_PRINCIPLES.format(n="B-", bp=rel_bp, scope=scope),
        "",
        "### Engineering rules from the blueprint",
        "",
        *body,
        RULES_END,
    ])
    span = rules_span(old)
    if span:
        return old[: span[0]] + block + old[span[1]:]
    m = re.search(r"^## Governance\b", old, re.M)
    if m:
        return old[: m.start()] + block + "\n\n" + old[m.start():]
    return old.rstrip() + "\n\n" + block + "\n"


VERSION_RE = re.compile(r"(\*\*Version\*\*:\s*)(\d+)\.(\d+)\.(\d+)")
LAST_AMENDED_RE = re.compile(r"(\*\*Last Amended\*\*:\s*)([0-9-]+)")


def block_content_sha(text: str) -> str | None:
    span = rules_span(text)
    m = re.search(r"content-sha ([0-9a-f]+)", text[span[0]:span[1]]) if span else None
    return m.group(1) if m else None


def record_amendment(text: str, change: str, bump: str, rel_bp: str, today: str) -> tuple[str, str | None]:
    """Follow the project's governance for a change to the managed block: bump the version, set Last
    Amended, add a Sync Impact Report line. Returns the text and the version change ("1.1.0 → 1.2.0")."""
    m = VERSION_RE.search(text)
    if bump == "none" or not m:
        return text, None
    major, minor, patch = int(m.group(2)), int(m.group(3)), int(m.group(4))
    new = f"{major}.{minor + 1}.0" if bump == "minor" else f"{major}.{minor}.{patch + 1}"
    old = f"{major}.{minor}.{patch}"
    text = text[: m.start()] + m.group(1) + new + text[m.end():]
    text = LAST_AMENDED_RE.sub(lambda x: x.group(1) + today, text, count=1)
    line = f"- Version change: {old} → {new} ({today}): Blueprint Rules block {change} by speckit-blueprint from {rel_bp}"
    rep_m = re.search(r"<!--\s*\n?\s*Sync Impact Report[^\n]*\n", text)
    if rep_m:
        text = text[: rep_m.end()] + line + "\n" + text[rep_m.end():]
    else:
        text = f"<!--\nSync Impact Report\n{line}\n-->\n" + text
    return text, f"{old} → {new}"


def bootstrap(root: Path, cfg: dict, bp: Blueprint) -> dict:
    rel_bp = os.path.relpath(bp.path, root)
    today = _dt.date.today().isoformat()
    report = {}

    # constitution
    cpath = root / ".specify" / "memory" / "constitution.md"
    old = cpath.read_text(encoding="utf-8") if cpath.is_file() else ""
    body = []
    missing = []
    for key in cfg.get("constitution_sections") or []:
        t = bp.section_text(str(key))
        if t:
            body += [demote(t, 3), ""]
        else:
            missing.append(str(key))
    content_sha = sha("\n".join(body))
    mode = cfg.get("constitution_mode") or "auto"
    if mode == "auto":
        owned = not old.strip() or TEMPLATE_MARK in old or (GENERATED_MARK in old and RULES_START not in old)
        mode = "own" if owned else "append"
    if mode == "append":
        before = block_content_sha(old)
        change = "added" if before is None else ("updated" if before != content_sha else None)
        text = append_rules(old, rel_bp, bp.sha, content_sha, body, cfg)
        version = None
        if change:
            text, version = record_amendment(text, change, str(cfg.get("constitution_version_bump") or "minor"), rel_bp, today)
        report["constitution"] = {
            "path": ".specify/memory/constitution.md", "mode": "append", "bytes": len(text.encode()),
            "block": change or "unchanged",
            "version": version or "unchanged",
            "missing_sections": missing,
        }
    else:
        text = own_constitution(old, rel_bp, bp, content_sha, body, cfg, today)
        version = re.search(r"\*\*Version\*\*:\s*([0-9.]+)", text).group(1)
        report["constitution"] = {"path": ".specify/memory/constitution.md", "mode": "own", "bytes": len(text.encode()), "version": version, "missing_sections": missing}
    cpath.parent.mkdir(parents=True, exist_ok=True)
    cpath.write_text(text, encoding="utf-8")

    # review checklist
    rc = bp.section_text("14.4") or bp.section_text("Review checklist")
    p = root / "docs" / "REVIEW-CHECKLIST.md"
    if p.is_file() and GENERATED_MARK not in p.read_text(encoding="utf-8"):
        report["review_checklist"] = "docs/REVIEW-CHECKLIST.md exists and is not generated; left unchanged"
    elif rc:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(gen_header(rel_bp, bp.sha, "REVIEW-CHECKLIST.md") + "\n" + demote(rc, 1) + "\n", encoding="utf-8")
        report["review_checklist"] = "docs/REVIEW-CHECKLIST.md"
    else:
        report["review_checklist"] = "missing §14.4 in blueprint"

    # decisions log (created once; sessions append to it)
    dpath = root / "docs" / "DECISIONS.md"
    if not dpath.is_file():
        rows = []
        for ident in sorted((k for k in bp.defs if id_type(k) == "DR"), key=lambda x: int(x[3:])):
            u = bp.defs[ident][0]
            first = bp.lines[u.start]
            title = re.sub(r"^#+\s*|^\*\*|\*\*$", "", first).strip()
            title = re.sub(r"^" + re.escape(ident) + r"\s*[—–:-]*\s*", "", title)
            status = "active"
            m = re.search(r"\*\*Status\*\*\s*([A-Za-z]+)", u.text(bp.lines))
            if m:
                status = m.group(1).lower()
            rows.append(f"| {ident} | {title[:90]} | blueprint | {status} |")
        tpl = (Path(__file__).resolve().parent.parent / "templates" / "DECISIONS.md").read_text(encoding="utf-8")
        dpath.write_text(
            tpl.replace("{{PRODUCT}}", bp.title()).replace("{{BLUEPRINT}}", rel_bp).replace("{{ROWS}}", "\n".join(rows)),
            encoding="utf-8",
        )
        report["decisions"] = f"created docs/DECISIONS.md with {len(rows)} blueprint DRs indexed"
    else:
        report["decisions"] = "docs/DECISIONS.md exists; left unchanged"

    # CLAUDE.md managed block
    block_tpl = (Path(__file__).resolve().parent.parent / "templates" / "claude-block.md").read_text(encoding="utf-8")
    block = block_tpl.replace("{{PRODUCT}}", bp.title()).replace("{{BLUEPRINT}}", rel_bp).replace("{{SPECS}}", cfg["specs_dir"])
    block = f"{CLAUDE_START}\n{block.strip()}\n{CLAUDE_END}"
    cm = root / "CLAUDE.md"
    if cm.is_file():
        cur = cm.read_text(encoding="utf-8")
        if CLAUDE_START in cur and CLAUDE_END in cur:
            pre, rest = cur.split(CLAUDE_START, 1)
            post = rest.split(CLAUDE_END, 1)[1]
            new = pre + block + post
        else:
            new = cur.rstrip() + "\n\n" + block + "\n"
    else:
        new = block + "\n"
    cm.write_text(new, encoding="utf-8")
    report["claude_md"] = "CLAUDE.md managed block updated"
    return report


# --------------------------------------------------------------------------------------------
# Claude Code hooks


def fresh_project(root: Path, cfg: dict) -> bool:
    """No feature folders yet and no constitution beyond the `specify init` template."""
    specs = root / cfg["specs_dir"]
    if specs.is_dir() and any(d.is_dir() for d in specs.iterdir()):
        return False
    c = root / ".specify" / "memory" / "constitution.md"
    return not c.is_file() or TEMPLATE_MARK in c.read_text(encoding="utf-8")


def touches_rules(ti: dict, text: str, span: tuple[int, int]) -> bool:
    """Whether an Edit/MultiEdit/Write would change the managed rules block of the constitution."""
    if "content" in ti:
        new = ti.get("content") or ""
        ns = rules_span(new)
        return ns is None or new[ns[0]:ns[1]] != text[span[0]:span[1]]
    olds = [ti.get("old_string")] + [e.get("old_string") for e in ti.get("edits") or []]
    for o in olds:
        if not o:
            continue
        i = text.find(o)
        while i >= 0:
            if i < span[1] and i + len(o) > span[0]:
                return True
            i = text.find(o, i + 1)
    return False


def hook_session_start(root: Path, cfg: dict) -> int:
    try:
        sys.stdin.read()
    except OSError:
        pass
    if not (root / cfg["blueprint_path"]).is_file():
        # Without a blueprint, speak only in a fresh project; an existing Spec Kit project keeps its own flow.
        if not (root / ".specify" / "extensions" / EXT_ID).is_dir() or not fresh_project(root, cfg):
            return 0
    try:
        print(brief(project_status(root, cfg)))
    except Exception as exc:  # a status failure must never block a session
        print(f"[speckit-blueprint] status unavailable: {exc}")
    return 0


def hook_guard(root: Path, cfg: dict) -> int:
    if not cfg.get("guard", True):
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("tool_name") not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return 0
    ti = payload.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("notebook_path")
    if not fp:
        return 0
    try:
        rel = (root / fp).resolve().relative_to(root.resolve())
    except ValueError:
        return 0
    parts = rel.parts
    blocked = None
    if rel.as_posix() == ".specify/memory/constitution.md":
        c = root / rel
        text = c.read_text(encoding="utf-8") if c.is_file() else ""
        span = rules_span(text)
        if span:
            if touches_rules(ti, text, span):
                blocked = "its Blueprint Rules block is compiled from the blueprint (/speckit-blueprint-bootstrap); the rest of the file is yours"
        elif GENERATED_MARK in text:
            blocked = "the constitution is compiled from the blueprint (/speckit-blueprint-bootstrap)"
    elif len(parts) >= 3 and parts[0] == cfg["specs_dir"] and (root / parts[0] / parts[1] / TRACE_FILE).is_file():
        inner = Path(*parts[2:]).as_posix()
        if inner in COMPILED_FILES or inner.startswith("contracts/"):
            blocked = f"{inner} is compiled from the blueprint (/speckit-blueprint-compile)"
    if blocked:
        sys.stderr.write(
            f"speckit-blueprint guard: {rel.as_posix()} — {blocked}. Change docs/BLUEPRINT.md through "
            "/speckit-blueprint-amend and recompile instead. tasks.md and review.md stay editable. "
            "(Disable with `guard: false` in .specify/extensions/blueprint/blueprint-config.yml.)\n"
        )
        return 2
    return 0


# --------------------------------------------------------------------------------------------
# CLI


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    root = find_root(Path.cwd())
    cfg = load_config(root)
    cmd, args = argv[0], argv[1:]

    if cmd == "hook":
        if args[:1] == ["session-start"]:
            return hook_session_start(root, cfg)
        if args[:1] == ["guard"]:
            return hook_guard(root, cfg)
        print("usage: blueprint.py hook session-start|guard", file=sys.stderr)
        return 1

    if cmd == "status":
        st = project_status(root, cfg)
        print(brief(st) if "--brief" in args else json.dumps(st, indent=2, ensure_ascii=False))
        return 0

    bp_path = root / cfg["blueprint_path"]
    if not bp_path.is_file():
        print(f"error: blueprint not found at {cfg['blueprint_path']} (set blueprint_path in the extension config)", file=sys.stderr)
        return 1
    bp = Blueprint(bp_path)

    if cmd == "compile":
        keys = [a for a in args if not a.startswith("--")]
        if not keys:
            print("usage: blueprint.py compile E03 [--force]", file=sys.stderr)
            return 1
        print(json.dumps(compile_epic(root, cfg, bp, keys[0], force="--force" in args), indent=2, ensure_ascii=False))
        return 0
    if cmd == "bootstrap":
        print(json.dumps(bootstrap(root, cfg, bp), indent=2, ensure_ascii=False))
        return 0
    if cmd == "section":
        rc = 0
        for key in args:
            t = bp.section_text(key)
            if t is None:
                print(f"error: no section '{key}'", file=sys.stderr)
                rc = 1
            else:
                print(t + "\n")
        return rc
    if cmd == "find":
        rc = 0
        for ident in args:
            units = bp.defs.get(ident)
            if not units:
                print(f"error: {ident} is not defined outside the epics", file=sys.stderr)
                rc = 1
                continue
            print(f"<!-- {ident} -->\n" + render_units(bp, [(ident, u) for u in units]) + "\n")
        return rc
    if cmd == "accept":
        keys = [a for a in args if not a.startswith("--")]
        note = args[args.index("--note") + 1] if "--note" in args and args.index("--note") + 1 < len(args) else ""
        if not keys or not note:
            print('usage: blueprint.py accept E01 --note "why the built epic stays as it is"', file=sys.stderr)
            return 1
        keys = [k for k in keys if k != note]
        print(json.dumps(accept_change(root, cfg, bp, keys[0], note), indent=2, ensure_ascii=False))
        return 0
    if cmd == "stale":
        out = []
        for e in bp.epics:
            d = find_feature_dir(root, cfg, e["id"])
            if d:
                trace = json.loads((d / TRACE_FILE).read_text(encoding="utf-8"))
                changed = stale_units(bp, trace)
                if changed:
                    total, done = task_counts(d / "tasks.md")
                    out.append({"epic": e["id"], "feature_directory": d.relative_to(root).as_posix(), "changed": changed, "tasks_done": done, "tasks_total": total})
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    if cmd in ("refs", "lint"):
        rc = 0
        if cmd == "lint":
            linter = Path(__file__).resolve().parent / "lint_blueprint.py"
            import subprocess

            rc = subprocess.run([sys.executable, str(linter), str(bp_path), *args]).returncode
            print("\nReference resolution (blueprint.py refs):")
        out = {}
        for e in bp.epics:
            _, pairs, unresolved = epic_refs(bp, e, cfg)
            out[e["id"]] = {"resolved": len({i for i, _ in pairs}), "unresolved": unresolved}
        if any(v["unresolved"] for v in out.values()):
            out["how_to_define"] = REFS_HINT
            rc = rc or 1
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return rc
    if cmd == "epics":
        print(json.dumps([{"epic": e["id"], "title": e["title"], "stories": [s["id"] for s in e["stories"]]} for e in bp.epics], indent=2, ensure_ascii=False))
        return 0
    print(f"unknown command: {cmd}\n\n{__doc__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
