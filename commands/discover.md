---
description: "Turn an idea into an evidence-backed build blueprint (intake, research, decisions, epics)"
---

# Idea → Build Blueprint

Turn a raw idea (even 2–3 lines) into a single markdown document complete enough to build the product epic
by epic without guessing: research, competitor benchmark, architecture drivers and shape, a verified and
pinned stack, the quality gate, personas, flows, screens, UX copy, edge cases, and epics → stories →
Given/When/Then acceptance criteria → tests → Definition of Done.

This is the expensive, deliberate part of the workflow, and it is worth it: every later build session
works from what this document decides. Build sessions never read the whole blueprint; `/speckit-blueprint-compile`
hands each epic exactly the parts it needs. So be complete here, not brief.

Run on the strongest model at the highest effort the harness offers. If you cannot tell whether that is the
case, say so once at the start and continue.

Reference files live in `.specify/extensions/blueprint/references/` (written `references/…` below).
Read each one when its phase starts, not all up front.

## User Input

```text
$ARGUMENTS
```

## Modes

- **New product** — no `docs/BLUEPRINT.md` (or the configured `blueprint_path`) yet: run phases 0–4.
- **Incremental** — a blueprint exists and the input adds scope (a new capability, a new persona, a new
  integration): run phases 0–4 scoped to the addition. Read only the sections you must stay consistent
  with (`blueprint.py section <n>`, `blueprint.py find <ID>`), continue every ID series from its highest
  existing number, add new epics after the last one, add rows to the Amendments log, and do not rewrite
  decided sections unless the addition forces it (then that is an amendment: `/speckit-blueprint-amend`).

## Why this document has to be different

A build session has two sources of truth: the repo and what compile gives it from this blueprint. Whatever
is missing, vague or wrong here becomes a guess in code. Three habits:

1. **Evidence or silence.** Every claim about the outside world (a library, a version, a competitor, a
   regulation, a market figure, a service's availability in a country) carries an evidence tag:
   `[VERIFIED — <source>, <date>]`, `[ASSUMED — <why>]`, or `[UNKNOWN → OQ-nn]` (routed to Open Questions).
   Never fill a gap with a plausible guess: the reader cannot tell your guess from a fact.
2. **Decide, don't hedge.** "Use X or Y" pushes the decision onto an agent with less context than you have.
   Make the call, record the alternatives and why they lost.
3. **Write for zero context, with IDs.** No "as discussed". Every persona, flow, screen, copy line, entity,
   endpoint, integration, edge case, story and criterion has a unique ID, and is *defined* in its own
   section. Compile finds definitions by ID: a definition that only exists inside an epic is invisible to it.

## Workflow

| Phase | What happens | Reference |
|---|---|---|
| 0. Intake | Parse the idea, 2–5 warm-up searches, ONE batch of questions with defaults, wait | `references/intake-questions.md` |
| 1. Deep research | Domain, competitors, architecture drivers and shape, stack for agentic engineering, quality tooling, integrations and locale realities, UX benchmarks | `references/research-protocol.md`, `references/architecture-decisions.md`, `references/code-quality-and-review.md` |
| 2. Decision brief | Interpretation, personas, positioning, drivers, shape, stack, gate, epic list, open questions — in chat; get a go/correct | (below) |
| 3. Write | Section by section into `docs/BLUEPRINT.md` | `references/blueprint-template.md`, `references/speckit-flow.md` and the topic references |
| 4. Lint and hand over | Lint, resolve references, bootstrap the project | (below) |

Do not skip phases 0 and 2, and do not run phases out of order. Talk to the user in the language they wrote
in; machine-facing text in the document is English (see Language convention).

## Phase 0 — Intake

Read `references/intake-questions.md` first. The rules that matter most:

- **Warm up first.** 2–5 quick searches so the questions are concrete ("I see three products in this space —
  A, B, C — which is closest?") instead of generic.
- **One batch, defaults on every question.** Group them, put a sensible default next to each, and say that
  "defaults" or skipping is fine. Never ask in dribs and drabs.
- **Never ask what is already answered or inferable.** Language, currency, city names, local services,
  `.ir` domains, Jalali dates, "کاربر ایرانی" → users are probably Iranian: confirm in one line.
- **Ask only what changes the architecture, the personas or the scope.** ~10–15 questions for a product,
  3–6 for a feature. Use the AskUserQuestion tool for closed questions; open questions in prose after it.

Unanswered items become `[ASSUMED — …]` rows; they become the Assumptions section.

## Phase 1 — Deep research and benchmarking

Read `references/research-protocol.md` and follow its seven tracks **in order**:

- **A. Understand the idea** — domain concepts, vocabulary (→ Glossary), how the job is done today,
  adjacent regulation to flag (never legal advice).
- **B. Benchmark** — 5–10 direct and indirect competitors (global, plus local ones for a specific market),
  a feature matrix, best-in-class behaviour per key flow, common complaints (paraphrased, never quoted),
  the gap, a positioning statement.
- **C. Architecture drivers and shape** (`references/architecture-decisions.md`) — ranked, *measurable*
  quality-attribute drivers from personas, scale ceiling, failure cost and hosting reality; explicit
  non-drivers; 2–3 candidate styles scored; the shape, module boundaries and exit triggers.
- **D. Stack for agentic engineering** — weighted criteria in the protocol (mainstream and documented,
  strict static typing, one-command deterministic `check`, fast tests, LTS, few dependencies, hosting fit)
  **and** the drivers from C. Verify current stable versions, deprecations and licenses; pin them.
- **E. Quality bar and tooling** (`references/code-quality-and-review.md`) — verify the tools that make the
  gate real for the chosen stack, the style guide, CI capability, the security baseline for the category.
- **F. Integrations and locale realities** — payments, SMS/OTP, email, maps, push, stores, hosting/CDN.
  For Iran, availability of foreign services changes with sanctions and filtering: verify today's status
  and record the date.
- **G. UX benchmarks** — onboarding, empty states, error handling, accessibility norms.

C before D: choosing the framework first and writing drivers that happen to justify it is the most common
silent failure in a document like this.

Log every source (URL, title, access date) as you go; Sources is built from this log. Expect 20–60 searches
for a whole product; post a one-line progress note every few searches. If web tools are unavailable, stop and
tell the user: either they enable web access, or every external fact is marked `[UNVERIFIED]` with a warning
on the cover. Parallel research subagents are fine for independent tracks (B, F, G); give each a narrow
brief and require sources with dates in their report.

## Phase 2 — Decision brief (checkpoint)

Post this in chat, about one screen, in the user's language:

```
## Decision brief — <product name>
**How I read the idea:** 2–3 sentences. What it is, for whom, the single outcome it delivers.
**Users are:** <market/country>, <B2C/B2B>, <language(s)>. (confirmed / assumed)
**Personas:** P1 <name> — one line. P2 … (3–5 max, plus anti-personas if useful)
**Benchmark in one paragraph:** who exists, what the best of them do, the gap we take.
**Architecture drivers (top 3):** AD-1 … (target), AD-2 …, AD-3 … — and what we are NOT optimising for.
**Shape (locked unless you object):** <style> — why it beat <runner-up>, and the trigger to revisit it.
**Stack (locked unless you object):** language · framework · DB · hosting · testing — deciding reason and
what the runner-up would have bought, one line each.
**Quality gate:** `check` = … (expected runtime …); critical e2e paths: …; what we will measure: …
**Design direction:** reference-based (<their reference>) or chosen (<system/style>) — one line.
**Epics in order:** E00 Foundation, E01 …, E02 … (titles only, 6–14 typical)
**Needs your answer before I write:** only genuinely blocking questions, OQ-01…
**Everything else I will assume** as written in the Assumptions table.
Reply "go" to write the full blueprint, or correct any line.
```

If the user pre-authorised ("don't stop to ask"), post the brief and continue. Otherwise wait.

## Phase 3 — Write the blueprint

Read `references/blueprint-template.md` and keep it open: section skeleton, depth targets, table formats,
ID schemes. Then read `references/speckit-flow.md`: it overrides the template where the build process
differs (section 18, the appendices, Epic 00, and the definition rules compile relies on). Before the
relevant sections, read:

- Personas, flows, screens, design direction → `references/design-minimal.md`
- UX writing and copy tables → `references/ux-writing-guide.md` (its Persian pack for Iranian users)
- Drivers, style, module boundaries, fitness functions, decision records → `references/architecture-decisions.md`
- Gate, review checklist, test quality, metrics → `references/code-quality-and-review.md`
- Edge-case register and per-story edge cases → `references/edge-case-catalog.md`
- Stories, ACs, tests, DoD → `references/stories-ac-tests.md`

Mechanics:

- Save to `docs/BLUEPRINT.md` (or the configured `blueprint_path`). **Write in chunks**: cover and TOC
  first, then one major section per write, in the order in the template's §5. A hundred-page document
  written in one output gets truncated or rushed.
- **IDs everywhere**, defined once in their home section (template §2). After each chunk, re-check the IDs
  you referenced against what exists.
- **Machine-facing text in English, human-facing prose in the user's language.** Every heading carries an
  English anchor.
- **Depth beats brevity.** The right length leaves no story, screen, copy line or edge case unspecified.
- **Every decision names its losers and its price.** **Decide the shape before the tools.** **Quality is
  specified, not assumed**: the gate, the review checklist and the metrics go in with commands and thresholds.

## Phase 4 — Lint and hand over

1. Lint, and check that compile can resolve every ID each epic uses; fix every error and unresolved ID
   (warnings: fix or justify), until it exits 0:

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py lint
   ```

2. Human pass: read the Executive summary, one persona, one flow and one epic as a stranger. Anything you
   had to infer, fix in the document.
3. Run `/speckit-blueprint-bootstrap` (constitution, review checklist, decisions log, CLAUDE.md block).
   In incremental mode, run it only if constitution sections changed.
4. Wrap up in 5–10 lines: point at the Assumptions table and the Open Questions, name the two or three
   things you are least sure about, and say the next step: a fresh session, then "continue" (or
   `/speckit-blueprint-compile E00`). Do not re-summarise the document. Do not commit unless the user asks.

## Language convention

- **Chat and human-facing prose** (summary, research narrative, personas, rationale, risks): the user's language.
- **Machine-facing text**: English — epic titles, stories, ACs, edge cases, tests, tasks, DoD, architecture,
  data model, API contracts, conventions, file names, IDs.
- **Product copy**: the product's language(s), with an English gloss column. Iranian users → Persian copy
  following the Persian pack.
- **Headings**: bilingual when prose is not English, e.g. `## 11. راهنمای UX Writing (UX Writing)`.

## Detecting the market

Language of the message, currency words (تومان، ریال، IRR), Iranian cities, Iranian services (Snapp,
Digikala, Shaparak, Bale, Eitaa, Rubika, Zarinpal, Kavenegar…), `.ir` domains, Jalali dates, کد ملی, or
explicit "کاربر ایرانی" → working hypothesis "users are in Iran": confirm in intake, then load the
Iran-specific parts of the research protocol, the UX writing guide and the edge-case catalog. Same logic for
any other specific market.

## Design reference handling

With a reference (Figma, URL, screenshots, brand kit): extract tokens and patterns and document them, noting
deviations for usability or RTL. Without one: choose a direction (mobile-first, minimal, a well-documented
design system verified by search) and say so in the brief. Never leave design "to be decided later".

## Guardrails that override everything else

- Strangers interacting, user-generated media, minors, payments, health or money advice: baseline safety
  (report/block/rate-limit, consent, audit) ships in the same epic as the core loop.
- Legal, tax and regulatory matters are Open Questions for a professional, never answered.
- Moderation and abuse prevention are specified as *what the system does*; never bypass logic or word lists.
- Never fabricate a source, a version, a competitor feature or a metric. `[UNKNOWN]` is always acceptable;
  a confident wrong answer never is.
