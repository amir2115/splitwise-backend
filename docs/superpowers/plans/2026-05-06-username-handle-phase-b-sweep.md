# UsernameHandle Phase B Sweep — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the `<UsernameHandle>` component (built in Phase A) to all 22 remaining `@username` rendering sites across 8 files in `web-new-version/src`, in a single commit, so every `@username` in the app renders bidi-correctly.

**Architecture:** Pure consumer-side migration — the component is unchanged. For each site: add the import (once per file), replace the literal `@{{ <expr> }}` text with `<UsernameHandle :username="<expr>" />` inside the same outer wrapper, preserving classes, attributes, and surrounding markup. One file (`PersonalBalancesSummary.vue`) also drops a hardcoded `→` arrow alongside the substitution to match the cleanup already done on the Balances page.

**Tech Stack:** Vue 3 SFC, Vitest + @vue/test-utils. Working directory for all commands: `/Users/amir/PycharmProjects/offline-splitwise/web-new-version`.

**Spec source:** `docs/superpowers/specs/2026-05-06-username-handle-phase-b-sweep-design.md`

---

## File Map

All paths relative to `web-new-version/`.

| File | Sites | Notes |
|---|---|---|
| `src/modules/settings/pages/SettingsPage.vue` | 1 | Simple substitution |
| `src/modules/settlements/pages/SettlementEditorPage.vue` | 4 | 2 with `?? '—'` fallback (preserve), 2 simple |
| `src/modules/groupCards/components/GroupCardsSection.vue` | 3 | Simple |
| `src/modules/expenses/pages/ExpenseEditorPage.vue` | 6 | All inside `class="user-tag"`; preserve `:title` attrs |
| `src/modules/groups/pages/GroupDashboardPage.vue` | 2 | One simple, one is two-handles + `isRtl` ternary arrow (keep ternary) |
| `src/modules/groups/pages/GroupsPage.vue` | 2 | One inside `<template v-if>` (no wrapper) |
| `src/modules/balances/components/PersonalBalancesSummary.vue` | 2 | Substitute, **and** drop the hardcoded `→` text on line 84 |
| `src/modules/members/pages/MembersPage.vue` | 2 | Simple |

Each file gets one new import line added once.

---

## Task 1: Apply all 22 substitutions in a single commit

**Files (modify):**
- `src/modules/settings/pages/SettingsPage.vue`
- `src/modules/settlements/pages/SettlementEditorPage.vue`
- `src/modules/groupCards/components/GroupCardsSection.vue`
- `src/modules/expenses/pages/ExpenseEditorPage.vue`
- `src/modules/groups/pages/GroupDashboardPage.vue`
- `src/modules/groups/pages/GroupsPage.vue`
- `src/modules/balances/components/PersonalBalancesSummary.vue`
- `src/modules/members/pages/MembersPage.vue`

The user explicitly requested a single commit. All 8 files are modified, then committed together at the end. Do NOT use `git add -A` or `git add .` — the inner repo has unrelated in-flight working-tree drift; stage exactly the 8 files listed.

### Reference snippet — the substitution pattern

For every `@{{ X }}` site, the change is:

```vue
<!-- before -->
<OuterWrapper class="...">@{{ X }}</OuterWrapper>

<!-- after -->
<OuterWrapper class="..."><UsernameHandle :username="X" /></OuterWrapper>
```

The `OuterWrapper` (with all its classes, `:title`, `v-if`, etc.) is **preserved unchanged**. Only the text node `@{{ X }}` is replaced.

For each file, also add **once** at the top of `<script setup>`:

```ts
import UsernameHandle from '@/shared/components/UsernameHandle.vue'
```

### Steps

- [ ] **Step 1: Confirm starting state**

Run from the parent repo root:

```bash
grep -rn '@{{ ' /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src --include="*.vue" | wc -l
```

Expected: `22` (the same 22 sites the spec lists).

If the count differs, **stop** and report — the spec was written against this exact state, and a different count means files have changed since.

- [ ] **Step 2: SettingsPage.vue — 1 site**

File: `src/modules/settings/pages/SettingsPage.vue`

Add `import UsernameHandle from '@/shared/components/UsernameHandle.vue'` once at the top of the existing `<script setup>` import block.

Find on or near line 85:

```vue
<span v-if="user?.username" class="muted">@{{ user.username }}</span>
```

Replace with:

```vue
<span v-if="user?.username" class="muted"><UsernameHandle :username="user.username" /></span>
```

- [ ] **Step 3: SettlementEditorPage.vue — 4 sites**

File: `src/modules/settlements/pages/SettlementEditorPage.vue`

Add the import once.

**Site 3a (around line 170, "from" direction card):**

```vue
<!-- before -->
<div class="direction-card__name">@{{ fromMember?.username ?? '—' }}</div>

<!-- after -->
<div class="direction-card__name"><UsernameHandle :username="fromMember?.username ?? '—'" /></div>
```

**Site 3b (around line 183, "to" direction card):**

```vue
<!-- before -->
<div class="direction-card__name">@{{ toMember?.username ?? '—' }}</div>

<!-- after -->
<div class="direction-card__name"><UsernameHandle :username="toMember?.username ?? '—'" /></div>
```

**Sites 3c and 3d (around lines 205 and 222 — both look like `<span>@{{ member.username }}</span>`).**

These two lines are textually identical, so use surrounding context to disambiguate. If using the `Edit` tool, you can use `replace_all: true` for this exact pair since both substitutions are identical:

```vue
<!-- before (occurs twice) -->
<span>@{{ member.username }}</span>

<!-- after -->
<span><UsernameHandle :username="member.username" /></span>
```

- [ ] **Step 4: GroupCardsSection.vue — 3 sites**

File: `src/modules/groupCards/components/GroupCardsSection.vue`

Add the import once.

**Site 4a (around line 222):**

```vue
<!-- before -->
<strong>@{{ memberName(row.card.member_id) }}</strong>

<!-- after -->
<strong><UsernameHandle :username="memberName(row.card.member_id)" /></strong>
```

**Site 4b (around line 275):**

```vue
<!-- before -->
<span v-if="selectedMember()" class="card-form__picker-label">@{{ selectedMember()?.username }}</span>

<!-- after -->
<span v-if="selectedMember()" class="card-form__picker-label"><UsernameHandle :username="selectedMember()?.username ?? ''" /></span>
```

(Note: `selectedMember()?.username` is `string | undefined`. The component requires a `string`. Coalesce to `''` to satisfy the type — when `selectedMember()` is falsy the parent `v-if` hides this whole span anyway, so the empty-string fallback is unreachable in practice but keeps TypeScript happy.)

**Site 4c (around line 295):**

```vue
<!-- before -->
<strong>@{{ member.username }}</strong>

<!-- after -->
<strong><UsernameHandle :username="member.username" /></strong>
```

- [ ] **Step 5: ExpenseEditorPage.vue — 6 sites (all inside `class="user-tag"`)**

File: `src/modules/expenses/pages/ExpenseEditorPage.vue`

Add the import once.

**Site 5a (around line 1161, payer summary single-payer branch):**

```vue
<!-- before -->
<template v-else-if="!isMultiplePayers"><span class="user-tag">@{{ activePayers[0]?.username }}</span></template>

<!-- after -->
<template v-else-if="!isMultiplePayers"><span class="user-tag"><UsernameHandle :username="activePayers[0]?.username ?? ''" /></span></template>
```

(Same TypeScript-coalesce note as Site 4b: `activePayers[0]?.username` is `string | undefined`, coalesce to empty string.)

**Site 5b (around line 1180, avatar-strip name):**

```vue
<!-- before -->
<span class="avatar-strip__name user-tag">@{{ m.username }}</span>

<!-- after -->
<span class="avatar-strip__name user-tag"><UsernameHandle :username="m.username" /></span>
```

**Site 5c (around line 1254, share-row name — equal-split branch):**

```vue
<!-- before -->
<span class="share-row__name user-tag" :title="`@${m.username}`">@{{ m.username }}</span>

<!-- after -->
<span class="share-row__name user-tag" :title="`@${m.username}`"><UsernameHandle :username="m.username" /></span>
```

(Preserve the `:title` template-literal attribute exactly — don't substitute the component there.)

**Site 5d (around line 1288, share-row name — exact-split branch):**

Same pattern as 5c, identical strings:

```vue
<!-- before -->
<span class="share-row__name user-tag" :title="`@${m.username}`">@{{ m.username }}</span>

<!-- after -->
<span class="share-row__name user-tag" :title="`@${m.username}`"><UsernameHandle :username="m.username" /></span>
```

If using the `Edit` tool with `replace_all: true`, sites 5c and 5d can be done in one edit because they're textually identical.

**Site 5e (around line 1516, payer detail row):**

```vue
<!-- before -->
<strong class="user-tag">@{{ m.username }}</strong>

<!-- after -->
<strong class="user-tag"><UsernameHandle :username="m.username" /></strong>
```

**Site 5f (around line 1725, share-amount detail row):**

```vue
<!-- before -->
<span class="user-tag">@{{ member.username }}</span>

<!-- after -->
<span class="user-tag"><UsernameHandle :username="member.username" /></span>
```

- [ ] **Step 6: GroupDashboardPage.vue — 2 sites (one tricky)**

File: `src/modules/groups/pages/GroupDashboardPage.vue`

Add the import once.

**Site 6a (around line 279, activity row sub-line for expense rows):**

```vue
<!-- before -->
<span class="activity-row__sub">@{{ expensePayerNames(expense) }}</span>

<!-- after -->
<span class="activity-row__sub"><UsernameHandle :username="expensePayerNames(expense)" /></span>
```

(Note: `expensePayerNames` may return a comma-separated list like `"amir, behnam"`. The component prepends a single `@` to the whole string — same as today's behavior. Pre-existing semantic weirdness preserved deliberately.)

**Site 6b (around line 307, activity row title for settlement rows — TWO handles + RTL-aware arrow):**

```vue
<!-- before -->
<span class="activity-row__title">@{{ memberName(settlement.from_member_id) }} {{ isRtl ? '←' : '→' }} @{{ memberName(settlement.to_member_id) }}</span>

<!-- after -->
<span class="activity-row__title"><UsernameHandle :username="memberName(settlement.from_member_id)" /> {{ isRtl ? '←' : '→' }} <UsernameHandle :username="memberName(settlement.to_member_id)" /></span>
```

Keep the `{{ isRtl ? '←' : '→' }}` ternary verbatim — it's already direction-aware. The two `<bdi>` elements (rendered by `<UsernameHandle>`) compose correctly with the arrow text node between them. **This is the site the Phase A final reviewer specifically flagged for verification — Task 2 will visually check it.**

- [ ] **Step 7: GroupsPage.vue — 2 sites**

File: `src/modules/groups/pages/GroupsPage.vue`

Add the import once.

**Site 7a (around line 327, current user identity inside `<template v-if>`):**

```vue
<!-- before -->
<template v-if="user && user.username">@{{ user.username }}</template>

<!-- after -->
<template v-if="user && user.username"><UsernameHandle :username="user.username" /></template>
```

(The `<template v-if>` fragment with no wrapper element works fine — `<UsernameHandle>` is a single inline element.)

**Site 7b (around line 368, invite row):**

```vue
<!-- before -->
<span class="muted">@{{ invite.inviter_username }}</span>

<!-- after -->
<span class="muted"><UsernameHandle :username="invite.inviter_username" /></span>
```

- [ ] **Step 8: PersonalBalancesSummary.vue — 2 sites + arrow cleanup**

File: `src/modules/balances/components/PersonalBalancesSummary.vue`

Add the import once.

**Site 8a (around line 83, "from" name):**

```vue
<!-- before -->
<strong>@{{ memberName(row.item.from_member_id) }}</strong>

<!-- after -->
<strong><UsernameHandle :username="memberName(row.item.from_member_id)" /></strong>
```

**Site 8b (around line 84, "to" name — also drop the leading `→`):**

```vue
<!-- before -->
<span>→ @{{ memberName(row.item.to_member_id) }}</span>

<!-- after -->
<span><UsernameHandle :username="memberName(row.item.to_member_id)" /></span>
```

The `→ ` (arrow + space) is removed entirely — match the cleanup done on Balances page suggested-row meta text. The visual hierarchy (from above, to below) communicates direction without textual help.

- [ ] **Step 9: MembersPage.vue — 2 sites**

File: `src/modules/members/pages/MembersPage.vue`

Add the import once.

**Site 9a (around line 284, member row name):**

```vue
<!-- before -->
<strong class="member-row__name">@{{ member.username }}</strong>

<!-- after -->
<strong class="member-row__name"><UsernameHandle :username="member.username" /></strong>
```

**Site 9b (around line 343, suggestion option):**

```vue
<!-- before -->
<span class="member-suggestion-option__username">@{{ suggestion.username }}</span>

<!-- after -->
<span class="member-suggestion-option__username"><UsernameHandle :username="suggestion.username" /></span>
```

- [ ] **Step 10: Verify all 22 sites replaced**

Run:

```bash
grep -rn '@{{ ' /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src --include="*.vue"
```

Expected: empty output (or only matches in non-username contexts that happen to start with `@` followed by `{{` — for context, scan the result and confirm none reference `.username`, `member_name`, or similar).

Then verify each file has its import added exactly once:

```bash
grep -c "import UsernameHandle" /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/settings/pages/SettingsPage.vue \
  /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/settlements/pages/SettlementEditorPage.vue \
  /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/groupCards/components/GroupCardsSection.vue \
  /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/expenses/pages/ExpenseEditorPage.vue \
  /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/groups/pages/GroupDashboardPage.vue \
  /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/groups/pages/GroupsPage.vue \
  /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/balances/components/PersonalBalancesSummary.vue \
  /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/modules/members/pages/MembersPage.vue
```

Expected: each file shows `:1` (exactly one import line per file).

- [ ] **Step 11: Type-check + build**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
```

Expected: build succeeds with no TypeScript errors.

If the build fails on a `Type 'string | undefined' is not assignable to type 'string'` error around `selectedMember()?.username` (Site 4b) or `activePayers[0]?.username` (Site 5a), confirm those sites have the `?? ''` coalesce — those props don't accept `undefined`.

- [ ] **Step 12: Run tests**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- username-handle group-balances
```

Expected: 4 + 5 = 9 pass.

(The full suite still has the 2 pre-existing unrelated failures from the user's earlier in-flight work; running the targeted suites avoids that noise.)

- [ ] **Step 13: Single commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add \
  src/modules/settings/pages/SettingsPage.vue \
  src/modules/settlements/pages/SettlementEditorPage.vue \
  src/modules/groupCards/components/GroupCardsSection.vue \
  src/modules/expenses/pages/ExpenseEditorPage.vue \
  src/modules/groups/pages/GroupDashboardPage.vue \
  src/modules/groups/pages/GroupsPage.vue \
  src/modules/balances/components/PersonalBalancesSummary.vue \
  src/modules/members/pages/MembersPage.vue

git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "refactor: use UsernameHandle for all @username rendering across the app"
```

(Note: each of these files has months of pre-existing unrelated in-flight working-tree drift in the inner `web-new-version/` repo; the commit will inevitably absorb that drift alongside the substitutions. The user has explicitly accepted this throughout this session. Stage only the listed 8 files — never use `git add .` or `-A`.)

---

## Task 2: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Confirm one new commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version log --oneline -2
```

Expected: HEAD is the Phase B commit; HEAD~1 is the Phase A final-review-fixes commit `eed2b56` (`fix(username-handle): drop tabular-nums and tighten contract tests`).

- [ ] **Step 2: Sanity-check the diff scope**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version show --stat HEAD
```

Expected: 8 files changed. (Number of insertions/deletions will be larger than the substitution count because of the in-flight working-tree drift the commit absorbs — that's expected.)

- [ ] **Step 3: Manual visual gate (`fa` RTL)**

Run:

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run dev
```

Navigate through each page in the app (language `fa`) and verify:

1. **Settings** — "Signed in as" identity row shows `@username` flush at the RTL start.
2. **Settlement editor** — both direction cards show `@username` (or `@—` if no member chosen); the picker rows show `@username`.
3. **Group cards section** — card list rows show `@username`; the picker label shows `@username` when a member is selected.
4. **Expense editor** — payer summary, avatar strip, share rows (both equal-split and exact-split branches), payer detail row, and share-amount detail row all show `@username` correctly.
5. **Group dashboard** — activity row for expenses shows `@payer-name(s)`; **the activity row for settlements shows `@from {arrow} @to`** with the arrow direction matching the language. Visually verify both directions of the arrow render correctly in RTL — the two `<bdi>` elements should sit at the natural positions on either side of the arrow text node.
6. **Groups page** — top identity shows `@username`; invite rows show `@inviter-username`.
7. **Personal balances summary** (visible inside the group dashboard or wherever the component is mounted) — `@from-name` (strong) on top line, `@to-name` (muted) on bottom line, **with NO leading `→` text**.
8. **Members page** — every member row shows `@username`; the suggestion options in the search list show `@username`.

In all cases: `@` appears BEFORE the name; the handle text sits at the natural start (right edge in RTL); no leftward drift.

- [ ] **Step 4: Manual visual gate (`en` LTR)**

Switch language to English in Settings, then revisit:
- Group dashboard activity row (settlement type) — arrow direction should swap; both handles stay correct.
- Expense editor share rows — verify no regression.
- Members page — verify no regression.

- [ ] **Step 5: Done — no commit needed**

This task only verifies. If anything is off, return to Task 1 Step matching the affected file and address.

---

## Out of scope

- Fixing the `expensePayerNames` comma-list semantic issue (only first name gets `@`).
- Adding presentation props to `<UsernameHandle>` (`tone`, `weight`, `muted`) — Phase A's final reviewer recommended against this.
- Any changes to the component itself (e.g., new tests). The 4 contract tests added at the end of Phase A continue to cover the substitution pattern.
