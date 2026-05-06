# Balances Page Redesign — Swiply Parity

**Date:** 2026-05-06
**Scope:** `web-new-version` PWA — Balances screen
**Source design:** Swiply Redesign — `BalancesScreen` component

## Goal

Bring `BalancesPage.vue` to visual + functional parity with the Swiply Redesign mock. Three explicit defects to resolve:

1. The "حالت پرداخت بهینه" (Optimal Payment Mode) toggle card is shown above the suggested-payments list. The design has no such toggle — suggested payments are unconditional. **Remove it.**
2. Per-member rows are flat and use muted gray for the role label. The design uses **state-tinted role labels and an expandable breakdown** (chevron, tap-to-expand, per-pair list with a "Pay" pill).
3. Arrow direction is handled via inline `v-if="isRtl"` SVG branches and a hardcoded `→` character in meta text. Replace with **a systematic CSS-driven approach** using the existing `.suggested-arrow` rule in `app.css`.

## Non-goals

- No data layer changes. `deriveGroupBalances` and the `GroupBalanceResponse` shape stay as-is.
- No new pairwise debt computation — breakdowns are projected from the existing `simplified_debts` array.
- No changes to settlement editor routing — the "پرداخت" pill reuses `goToSuggestedSettlement`.
- No styling changes outside the Balances page (other than the same arrow fix in the shared `SuggestedPaymentCard.vue`).

## Affected files

| File | Change |
|---|---|
| `src/modules/balances/pages/BalancesPage.vue` | Primary changes — remove toggle, restyle rows, add expand/collapse, fix arrows |
| `src/shared/components/SuggestedPaymentCard.vue` | Fix the same hardcoded-`→` issue (component is shared with other pages) |
| `src/shared/i18n/strings.ts` | Add three new keys: `tapForBreakdown`, `breakdownOwedByTitle`, `breakdownOwesToTitle` |

## Architecture

### Removal: Optimal Payment Mode toggle

Delete from `BalancesPage.vue`:
- The `simplify` ref (line 34)
- The `<template #actions>` slot in `<PageTopBar>` (lines 77–84) — it shows a brand chip advertising the same feature
- The `<div class="surface-card switch-field">` block (lines 94–102)
- The `<template v-if="simplify">` wrapper around the suggested chain (line 105) — suggested payments are now always rendered
- The `EmptyStateCard` already inside that wrapper stays, just unwrapped

### Breakdown derivation (no new data layer)

For each member in `balanceResponse.balances`:

| Member state (`net_balance`) | Breakdown source | Section title key |
|---|---|---|
| `> 0` (creditor) | `simplified_debts.filter(d => d.to_member_id === member.member_id)` | `breakdownOwedByTitle` |
| `< 0` (debtor) | `simplified_debts.filter(d => d.from_member_id === member.member_id)` | `breakdownOwesToTitle` |
| `= 0` (settled) | none — chevron hidden, row not interactive | — |

Each breakdown entry shows: avatar (28px) + `@username` + role-relative sub-line + amount (state-colored) + "Pay" pill that calls `goToSuggestedSettlement` with the matching transfer.

This means breakdowns are **consistent with the suggested payment chain at the top** — you can read the chain top-down or member-by-member and see the same plan from two angles.

### Expand/collapse state

A single ref:

```ts
const expandedMemberId = ref<string | null>(null)
```

Click handler toggles between the clicked id and `null`. Only one row expanded at a time (matches the design preview behavior).

Members with empty breakdown (settled) are rendered as a non-interactive `<div>` (no chevron, no click target). All others are `<button>`s with `aria-expanded`.

### Systematic arrow handling

The Swiply theme's `app.css` already defines:

```css
:root[dir='rtl'] .suggested-arrow,
:root[dir='rtl'] .toolbar-arrow {
  transform: scaleX(-1);
}
```

This is the single source of truth for directional arrows. Replace all `v-if="isRtl"` SVG branches with a single `→` arrow (SVG or character) wrapped in `<span class="suggested-arrow">`. Both the inter-avatar arrow and the meta-text arrow get the same treatment. CSS handles the rest.

This removes the `isRtl` computed from `BalancesPage.vue` entirely (it is no longer needed in the template). Same change in `SuggestedPaymentCard.vue` removes its local `isRtl` computed too.

### Per-member row visual changes

| Element | Current | Target |
|---|---|---|
| Container | static `<div class="member-balance-row">` | `<button class="member-row" :aria-expanded>` (or `<div>` when settled and no breakdown) |
| Label color | `.muted` (gray) | tone class: `--pos` for creditor, `--neg` for debtor, `--fg-subtle` for settled |
| Amount font | `var(--t-body)` / weight 600 | 15px / weight 700 |
| Amount prefix | none | `+` for credit, `−` for debit, `—` for settled |
| Chevron | absent | 24px circular pill with chevron-down, rotates 180° when expanded |
| Expanded background | n/a | `--surface-sunk` |
| Container border | bottom-divider per row | wrapped in a single bordered card (`--surface` background, divider between rows) |

The container becoming a single bordered card (instead of free-flowing rows) matches the design — the per-member list visually sits inside one rounded card just like the suggested-payment list.

### Strings

Three new keys, both `fa` and `en`:

```ts
tapForBreakdown:        'برای جزئیات بزن'           / 'Tap for breakdown'
breakdownOwedByTitle:   'طلبکار از این افراد'        / 'Owed by these people'
breakdownOwesToTitle:   'بدهکار به این افراد'        / 'Owes these people'
```

The "پرداخت" / "Settle up" pill reuses existing `dashboardSettleUpAction`.

The eyebrow row above the per-member list shows `memberBalanceTitle` on the start side and `tapForBreakdown` on the end side (matching the design header row).

## Component flow

```
BalancesPage
├── PageTopBar (no actions slot now)
├── header text (suggestedPaymentsTitle eyebrow + optimizePaymentsSubtitle headline)
├── suggested chain card
│   └── for each transfer in simplified_debts:
│       └── button row { from-avatar, .suggested-arrow, to-avatar, meta(@from / .suggested-arrow + @to), amount }
│       (or EmptyStateCard if no transfers)
├── eyebrow row (memberBalanceTitle ← → tapForBreakdown)
└── member list card
    └── for each balance:
        ├── trigger row (button | div) { avatar, @username, role-label-tinted, amount±prefix, chevron? }
        └── if expandedMemberId === balance.member_id and breakdown.length > 0:
            └── breakdown panel
                ├── eyebrow (breakdownOwedByTitle | breakdownOwesToTitle)
                └── inner card
                    └── for each pair in breakdown:
                        └── row { mini-avatar, @other, sub-line, ±amount, "پرداخت" pill }
```

## Edge cases

- **Empty `simplified_debts`** (everyone settled): `EmptyStateCard` renders in the suggested-payments slot (existing behavior, just unwrapped from the simplify branch).
- **Member with `net_balance === 0`**: row is non-interactive, no chevron, amount is `—`.
- **Member with non-zero net but empty breakdown projection** (defensive — shouldn't happen if `simplified_debts` is consistent with `balances`): treat as no breakdown, render as static row. No crash.
- **Tapping the "پرداخت" pill** inside an expanded breakdown: stops propagation, calls `goToSuggestedSettlement` with the matching transfer, navigates to settlement editor.
- **Direction switching at runtime** (settings page → balances): CSS `[dir='rtl']` selector reacts immediately, no Vue re-render required for arrows.

## Testing

- Existing `tests/group-balances.test.ts` covers `deriveGroupBalances` — no changes.
- No new unit tests planned; the changes are presentational and the breakdown projection is a thin filter over existing data.
- Manual verification:
  1. `fa` mode: every arrow points from payer to receiver. The meta-text `→ @to` reads correctly in RTL.
  2. `en` mode: same correctness.
  3. Tap a creditor row → breakdown shows "Owed by these people" + each debtor + "Pay" pill.
  4. Tap a debtor row → breakdown shows "Owes these people" + each creditor + "Pay" pill.
  5. Tap a settled row → nothing happens (no chevron, not interactive).
  6. Tap "پرداخت" inside a breakdown → settlement editor opens pre-filled.
  7. Reload page after toggling language → no leftover toggle card visible.
