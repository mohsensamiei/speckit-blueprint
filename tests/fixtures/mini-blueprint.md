# Tally — Build Blueprint

## 0. How to use this document (How to use)

Fixture for the speckit-blueprint tests. Not a real product.

## 5. Personas

### P1 — Sara, shop owner (primary)

Runs a small shop; uses the app on a mid-range Android phone.

### P2 — Reza, accountant

Reads monthly totals.

## 7. User flows (Flows)

### F-01 — Record a sale (P1)

1. SCR-01 shows CP-SCR01-1. 2. On error shows CP-SCR01-3 (EC-INPUT-02).

## 8. Screen inventory and navigation (Screens)

| ID | Screen | Purpose |
|---|---|---|
| SCR-01 | New sale | Enter an amount |
| SCR-02 | Totals | Show the month |

## 11. Copy tables (Copy)

### 11.1 SCR-01 New sale

| ID | Element | Copy (fa) | English gloss |
|---|---|---|---|
| CP-SCR01-1 | Title | فروش جدید | New sale |
| CP-SCR01-2 | Button | ثبت | Save |
| CP-SCR01-3 | Error | مبلغ نامعتبر است | Invalid amount |

### 11.2 SCR-02 Totals

| ID | Element | Copy (fa) | English gloss |
|---|---|---|---|
| CP-SCR02-1 | Title | جمع ماه | Month total |

## 12. Architecture

### 12.0 Architecture drivers

| ID | Driver | Measurable target |
|---|---|---|
| AD-1 | Correctness of money | 0 rounding errors in 10k fixtures |

### 12.2 Module map and boundaries

Modules: `sales`, `reports`. `reports` may import `sales`; never the reverse.

### 12.4 Data model

Conventions: amounts are integer rials.

**ENT-Sale** (`sale`, owner `sales`)

| Field | Type |
|---|---|
| id | uuid |
| amount_rial | bigint |

**ENT-Shop** (`shop`, owner `sales`): `id` uuid PK · `name` text

### 12.5 API contracts

All responses use the error envelope `{ "error": { "code": … } }`.

| ID | Method path | Purpose |
|---|---|---|
| API-01 | POST `/sales` | Record a sale |
| API-02 | GET `/totals` | Month totals |

### 12.7 Integrations

**INT-sms — Kavenegar**
- Timeout 5 s, no retry.

### 12.10 Fitness functions

| ID | Rule | Check |
|---|---|---|
| FF-01 | `sales` never imports `reports` | dependency-cruiser |

## 13. Tech stack and engineering conventions (Tech Stack)

### 13.1 Stack decision and stack table

| Layer | Technology | Pinned version |
|---|---|---|
| Runtime | Node.js | 24.1.0 |

### 13.2 Forbidden choices

No ORMs.

### 13.3 Repository layout

`src/modules/<module>/`

### 13.4 The `check` command

`npm run check`

### 13.5 Formatting, lint and type strictness

Strict TypeScript.

### 13.6 Testing conventions

Vitest.

### 13.7 Git conventions

Conventional commits with story IDs.

### 13.9 Error handling, logging and configuration conventions

pino.

### 13.10 Dependency policy and version drift

A new dependency needs a DR.

## 14. Quality strategy, review and metrics (Quality)

### 14.2 The gate

`check` runs format, lint, types, tests.

### 14.3 Test strategy

Tests first.

### 14.4 Review checklist

- [ ] Every AC has a test.
- [ ] No improvised copy.

### 14.8 Definition of green, definition of done, manual verification

Green means `check` passes.

## 15. Edge-case register (Edge Cases)

| ID | Case | Expected behaviour |
|---|---|---|
| EC-INPUT-01 | Empty amount | Disable save |
| EC-INPUT-02 (new) | Non-numeric amount | Show CP-SCR01-3 |
| EC-NET-01 | Offline | Queue the sale |

## 4. Assumptions and decision records (Assumptions & Decisions)

#### DR-01 — Integer rials
**Status** Accepted — 2026-10-01
**Decision** Store money as integer rials.

## 17. Epics and stories (Epics)

## Epic 00 — Foundation

**Goal** — Repo, `check`, CI.
**Personas served** P1
**Preconditions for the session** — none.

### E00-S01 — Bootstrap the repository

**Story** — As **P1 (Sara)**, I want a working repo, so that features can land.
**Acceptance Criteria**
- AC-1 Given a clean clone, When `npm run check` runs, Then it passes (FF-01, DR-01).
**Edge cases** — none.
**Tests**
- Unit: `src/smoke.test.ts` — covers AC-1.
- Manual: `npm ci` on a clean machine.
**Tasks**
- E00-S01-T1 Init the repo.
**Story DoD** — Default.

**Epic-level tests** — `npm run check` green.
**Definition of Done**
- All stories DONE.
**Session handoff checklist** — summary.

## Epic 01 — Record sales

**Goal** — Sara records a sale in under 10 seconds.
**Personas served** P1
**Depends on** E00
**Preconditions for the session** — E00 done. SMS sandbox reachable [VERIFY-AT-BUILD].
**Flows and screens implemented** F-01; SCR-01 to SCR-02.
**Data and API touched** ENT-Sale, API-01; INT-sms.
**Risks specific to this epic** R-01.

### E01-S01 — Enter and save a sale

**Story** — As **P1 (Sara)**, I want to type an amount and save it, so that the day's total is right.
**Context** — AD-1; OQ-01 default applies.
**Acceptance Criteria**
- AC-1 Given SCR-01, When 1200 is saved, Then API-01 stores `amount_rial = 1200` and CP-SCR01-1 stays visible.
- AC-2 Given SCR-01, When "abc" is entered, Then CP-SCR01-3 is shown (EC-INPUT-01 to 02).
**Edge cases** — EC-NET-01.
**Tests**
- Integration: `test/sale.int.test.ts` — covers AC-1, AC-2.
**Tasks**
- E01-S01-T1 ENT-Sale migration.
- E01-S01-T2 API-01 handler.
**Story DoD** — Default.

### E01-S02 — Undo the last sale

**Story** — As **P1 (Sara)**, I want to undo a mistaken sale, so that totals stay right.
**Acceptance Criteria**
- AC-1 Given a sale saved less than 30 s ago, When undo is tapped, Then it is deleted.
**Edge cases** — none.
**Tests**
- Unit: `src/undo.test.ts` — covers AC-1.
**Tasks**
- E01-S02-T1 Undo endpoint.
**Story DoD** — Default.

**Epic-level tests** — Record and undo end to end.
**Definition of Done**
- All stories DONE; `check` green.
**Session handoff checklist** — summary.

## 18. Session protocol (Session Protocol)

### 18.7 Amendments log

| A-nn | Date | Epic/story | What changed | Why | Approved by |
|---|---|---|---|---|---|

## 19. Risks and mitigations (Risks)

| ID | Risk | Mitigation |
|---|---|---|
| R-01 | SMS provider blocked | Fall back to in-app notice |

## 20. Open questions (Open Questions)

| ID | Question | Proposed default |
|---|---|---|
| OQ-01 | Tax on sales? | Ignore in v1 |

## 22. Sources

| ID | Title | URL |
|---|---|---|
| S-01 | Kavenegar docs | https://kavenegar.com/rest.html |
