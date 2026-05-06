# UsernameHandle — Phase B App-Wide Sweep

**Date:** 2026-05-06
**Phase:** B (follows Phase A which shipped in commits `d9afaea`, `103640c`, `32c423a`, `eed2b56`)
**Scope:** `web-new-version` PWA — sweep `<UsernameHandle>` across the remaining 22 `@username` sites in 8 files

## Goal

Apply the `<UsernameHandle>` component (introduced in Phase A) to **every remaining `@username` site** in the app so that `@` always renders before the username and the handle sits at the natural start position regardless of paragraph direction (`fa` RTL or `en` LTR). Phase A proved the pattern on the Balances page; Phase B finishes the job.

## Non-goals

- No changes to the `UsernameHandle` component itself — its contract (`username: string` → `<bdi>@{{ username }}</bdi>`) and its 4 contract tests stay as they are after Phase A's final-review fixes (commit `eed2b56`).
- No fix for the `expensePayerNames` semantic issue (it returns a comma-separated list, only the first name gets `@`). Pre-existing, out of scope.
- No restyle of the `class="user-tag"` pattern in `ExpenseEditorPage` — outer styling stays on the wrapper, the leaf is just the bidi-isolated handle.
- No new component tests; the 4 contract tests added at the end of Phase A cover the substitution pattern.

## The 22 sites

Sourced from `grep -rn "@{{ " web-new-version/src --include="*.vue"`. All sites are template text-interpolations of `@{{ <expr>.username }}` (or similar). Each is replaced by `<UsernameHandle :username="<expr>.username" />` inside the same outer wrapper.

| File | Line(s) | Pattern |
|---|---|---|
| `src/modules/settings/pages/SettingsPage.vue` | 85 | `<span v-if="user?.username" class="muted">` |
| `src/modules/settlements/pages/SettlementEditorPage.vue` | 170, 183 | `<div class="direction-card__name">` with `?? '—'` fallback |
| `src/modules/settlements/pages/SettlementEditorPage.vue` | 205, 222 | `<span>` (simple) |
| `src/modules/groupCards/components/GroupCardsSection.vue` | 222, 295 | `<strong>` (simple) |
| `src/modules/groupCards/components/GroupCardsSection.vue` | 275 | `<span class="card-form__picker-label">` |
| `src/modules/expenses/pages/ExpenseEditorPage.vue` | 1161, 1180, 1254, 1288, 1516, 1725 | All inside `class="user-tag"` wrappers (some with `:title="@${m.username}"` tooltip) |
| `src/modules/groups/pages/GroupDashboardPage.vue` | 279 | `<span class="activity-row__sub">@{{ expensePayerNames(expense) }}</span>` (comma-list) |
| `src/modules/groups/pages/GroupDashboardPage.vue` | 307 | **Two-handles-plus-arrow:** `@{{ from }} {{ isRtl ? '←' : '→' }} @{{ to }}` in one span |
| `src/modules/groups/pages/GroupsPage.vue` | 327 | `<template v-if>` fragment (no wrapper) |
| `src/modules/groups/pages/GroupsPage.vue` | 368 | `<span class="muted">` |
| `src/modules/balances/components/PersonalBalancesSummary.vue` | 83 | `<strong>` (simple) |
| `src/modules/balances/components/PersonalBalancesSummary.vue` | 84 | `<span>→ @{{ ... }}</span>` — remove the hardcoded `→` text alongside the handle substitution |
| `src/modules/members/pages/MembersPage.vue` | 284, 343 | `<strong>` and `<span class="member-suggestion-option__username">` |

**Total: 22 sites in 8 files.**

## Substitution rules

For each site, the change is:

1. Add `import UsernameHandle from '@/shared/components/UsernameHandle.vue'` once at the top of `<script setup>` (only if not already imported).
2. Replace the literal `@{{ <expr> }}` text node inside its parent element with `<UsernameHandle :username="<expr>" />`. The `@` character disappears from the template — the component owns it.
3. Outer wrappers (`<strong>`, `<span class="muted">`, `<span class="user-tag">`, etc.) are **preserved unchanged**. Existing classes, attributes (`v-if`, `:title`, etc.), and surrounding content stay.

## Edge-case decisions

### `SettlementEditorPage.vue` lines 170, 183 — `?? '—'` fallback

The current code: `@{{ fromMember?.username ?? '—' }}` renders `@—` when the member is undefined. After substitution: `<UsernameHandle :username="fromMember?.username ?? '—'" />` still renders `@—` (the component just prepends `@` to whatever string it receives). **Pre-existing behavior preserved verbatim.** A nicer empty state is out of scope for this plan.

### `GroupDashboardPage.vue:279` — `expensePayerNames(expense)` comma-list

`expensePayerNames` returns a comma-separated list when there are multiple payers (e.g. `"amir, behnam"`). The component prepends `@` to the whole string: `@amir, behnam`. Only the first name gets the prefix — same as today. **Pre-existing semantic weirdness preserved** (this is a separate bug to address in a future plan if desired).

### `GroupDashboardPage.vue:307` — two handles plus arrow

Current source:
```vue
<span class="activity-row__title">@{{ memberName(settlement.from_member_id) }} {{ isRtl ? '←' : '→' }} @{{ memberName(settlement.to_member_id) }}</span>
```

After substitution:
```vue
<span class="activity-row__title">
  <UsernameHandle :username="memberName(settlement.from_member_id)" />
  {{ isRtl ? '←' : '→' }}
  <UsernameHandle :username="memberName(settlement.to_member_id)" />
</span>
```

**Keep the `isRtl ? '←' : '→'` ternary as-is** — it's already direction-aware. Each handle is independently bidi-isolated by `<bdi>`, so they compose correctly with the arrow text node between them. **Risk: the manual visual gate at the end of Phase B must specifically verify this row in both `fa` and `en`** — this is the case the final Phase A reviewer specifically flagged.

### `PersonalBalancesSummary.vue:84` — remove hardcoded `→`

Current source:
```vue
<span>→ @{{ memberName(row.item.to_member_id) }}</span>
```

After substitution AND arrow removal:
```vue
<span><UsernameHandle :username="memberName(row.item.to_member_id)" /></span>
```

The hardcoded `→` is dropped to match the cleanup already done on the Balances page suggested-row meta text in Round 1. The previous line (`row.item.from_member_id` at line 83) is the "from" handle; together they form a from→to pair where the visual sequence (from above, to below) communicates direction. The textual `→` is redundant with the visual layout.

### `ExpenseEditorPage.vue` — preserve `:title` tooltip attributes

Some sites have e.g. `:title="`@${m.username}`"` attributes for hover tooltips:
```vue
<span class="share-row__name user-tag" :title="`@${m.username}`">@{{ m.username }}</span>
```

Becomes:
```vue
<span class="share-row__name user-tag" :title="`@${m.username}`">
  <UsernameHandle :username="m.username" />
</span>
```

UA tooltips don't have RTL/bidi rendering issues (they're rendered in chrome, not page DOM), so the title attribute is left exactly as-is — `@${m.username}` template literal stays.

### `GroupsPage.vue:327` — template-fragment substitution

```vue
<template v-if="user && user.username">@{{ user.username }}</template>
```

Becomes:
```vue
<template v-if="user && user.username"><UsernameHandle :username="user.username" /></template>
```

`<template>` with `v-if` and only inline content child works fine; no wrapper element needed.

## Commit strategy

**One commit** for all 22 sites across 8 files (per user's explicit request — "do it with one commit"). Commit message:

```
refactor: use UsernameHandle for all @username rendering across the app
```

The diff will be larger than per-file commits but easier for the user to review as a single logical change ("everywhere is now using the component"). This commit will inevitably absorb pre-existing in-flight working-tree drift in any of the 8 touched files (consistent with prior commits in this session); the user has accepted that throughout.

## Affected files (final list)

| File | Number of substitutions | Other changes |
|---|---|---|
| `src/modules/balances/components/PersonalBalancesSummary.vue` | 2 | Drop hardcoded `→` text |
| `src/modules/expenses/pages/ExpenseEditorPage.vue` | 6 | None |
| `src/modules/groupCards/components/GroupCardsSection.vue` | 3 | None |
| `src/modules/groups/pages/GroupDashboardPage.vue` | 2 | None (keep `isRtl` ternary) |
| `src/modules/groups/pages/GroupsPage.vue` | 2 | None |
| `src/modules/members/pages/MembersPage.vue` | 2 | None |
| `src/modules/settings/pages/SettingsPage.vue` | 1 | None |
| `src/modules/settlements/pages/SettlementEditorPage.vue` | 4 | None |

Each file gets one new import line plus its substitutions.

## Verification

1. `cd web-new-version && npm run build` — clean.
2. `cd web-new-version && npm test -- username-handle group-balances` — 4 + 5 = 9 pass.
3. **Manual visual gate** in `npm run dev`, **`fa` (RTL)**:
   - Settings page: `@username` next to "Signed in as" label (right edge).
   - Settlement editor: `@username` in the from/to direction cards; `@—` when no member chosen; `@username` in the picker rows.
   - Group cards section: `@username` in card list and picker.
   - Expense editor: `@username` in payer summary, avatar strip, share rows (both equal-split and exact-split branches), and the share-amount detail row.
   - Group dashboard activity row (the flagged risk): expense rows show `@payer-name(s)`; settlement rows show `@from {{ direction-arrow }} @to` reading right-to-left correctly.
   - Groups page: `@username` next to current user identity at top; `@inviter-username` in invite rows.
   - Personal balances summary: `@from-username` (strong, top); `@to-username` (muted, below) with NO leading `→` arrow.
   - Members page: `@username` in member rows and suggestion options.
4. Switch to **`en` (LTR)**: spot-check the Group Dashboard activity row + Expense Editor share rows for no regression.
5. Final grep sanity check from the repo root:
   ```bash
   grep -rn '@{{ ' web-new-version/src --include="*.vue" | wc -l
   ```
   Expected: `0` (or only counts that are new since this plan was written, e.g. inside non-username contexts that happen to start with `@`).

## Out of scope (followup ideas)

- Fix the `expensePayerNames` comma-list issue so multi-payer rows show `@a, @b` instead of `@a, b`.
- Audit `<input>` placeholder strings or other non-template `@username` references for the same bidi behavior (placeholders use the OS chrome's bidi rules; usually fine).
- Consider a thin `<UserHandle as="strong">` API in a later iteration if the boilerplate `<strong><UsernameHandle/></strong>` repetition becomes annoying. Phase A's final reviewer recommended against adding presentation props now — defer.
