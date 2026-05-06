# Expense Detail Rework + App-wide Icon System

**Date:** 2026-05-07
**Scope:** `web-new-version` PWA — three connected changes
**Source design:** Swiply Redesign — `ExpenseDetailScreen` + `Icon` set (extracted from cached design HTML at `/tmp/swiply-design-3.html`)

## Context

Two pain points the user wants addressed in one effort:

1. **`ExpenseDetailPage.vue` doesn't match the Swiply Redesign.** It currently renders four distinct sections (HeroCard + overview card + payers list + shares list) with redundant info. The design uses a tighter pattern: one hero summary card + per-member cards (each card showing the member's role, share, paid, and net). The user wants the page to match the design exactly.

2. **Inconsistent icons across the app.** The codebase mixes emoji glyphs (`✎`, `🗑`, `✕`, `✓`) with ad-hoc inline `<svg>` markup (~91 inline SVG instances across 22 Vue files). The design ships a centralized `Icon` set with 33 stroke icons. The user wants every icon swapped to the design's set, via a single shared component.

Doing both in one plan because (a) the new `<Icon>` component is a prerequisite for the ExpenseDetailPage's new edit/trash buttons, and (b) the user explicitly asked for an app-wide sweep alongside the page rework.

## Goals

1. Rebuild `ExpenseDetailPage.vue` to match the Swiply `ExpenseDetailScreen` design — hero summary card + per-member cards, with `note` shown as a subtitle below the hero amount.
2. Introduce `<Icon>` component at `src/shared/components/Icon.vue` exposing all 33 icons from the design via a `name` prop.
3. Replace every emoji-icon glyph (5 known sites) and every inline `<svg>` icon (~91 sites across 22 files) with `<Icon name="...">`.

## Non-goals

- No data-layer changes (the `Expense`/`Member`/`Settlement` types stay as-is; `expensesStore.remove()` flow unchanged).
- No new tests beyond a couple of `Icon` component unit tests verifying `<svg>` rendering for a known name.
- No backend changes.
- No changes to inline SVGs that are NOT icons (e.g., decorative graphics, illustrations) — only icon-shaped SVGs (16–24px, monochrome stroke) get migrated.
- No new icon designs. The 33 icons listed below are the closed set; if a consumer's existing SVG doesn't match any of them, it stays inline (and the spec lists those exceptions explicitly).

## Architecture

### 1. `<Icon>` component

**Path:** `web-new-version/src/shared/components/Icon.vue`

API:

```ts
defineProps<{
  name: IconName
  size?: number  // default 18
}>()
```

Where `IconName` is a union of the 33 icon names below (exported as a named type from the same module). The component renders `<svg viewBox="0 0 24 24" :width="size" :height="size">` containing the appropriate `<path>` / `<circle>` / `<rect>` children, all using `fill="none"` + `stroke="currentColor"` + `stroke-width="1.75"` + `stroke-linecap="round"` + `stroke-linejoin="round"` (the design's stroke-icon style).

Color is inherited from the parent's `color` (via `currentColor`). Size is set via `width`/`height` HTML attributes (so it's overridable from CSS).

### 2. The 33 icon paths

All icons use `viewBox="0 0 24 24"` and the stroke style above. The element list per icon (taken verbatim from the design's `Icon` component in `/tmp/swiply-design-3.html`):

| Name | Element(s) |
|---|---|
| `plus` | `<path d="M12 5v14M5 12h14"/>` |
| `arrow-right` | `<path d="M5 12h14M13 6l6 6-6 6"/>` |
| `arrow-left` | `<path d="M19 12H5M11 18l-6-6 6-6"/>` |
| `chevron-right` | `<path d="M9 6l6 6-6 6"/>` |
| `chevron-left` | `<path d="M15 6l-6 6 6 6"/>` |
| `chevron-down` | `<path d="M6 9l6 6 6-6"/>` |
| `close` | `<path d="M6 6l12 12M18 6l-12 12"/>` |
| `check` | `<path d="M5 12.5l4.5 4.5L19 7.5"/>` |
| `search` | `<circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/>` |
| `users` | `<circle cx="9" cy="8" r="3.5"/><path d="M3 20c0-3 2.5-5 6-5s6 2 6 5M16 10.5a3 3 0 1 0 0-6M21 20c0-2.4-1.6-4.4-4-4.9"/>` |
| `wallet` | `<path d="M4 7c0-1.7 1.3-3 3-3h10a3 3 0 0 1 3 3M4 7v10a3 3 0 0 0 3 3h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2H4"/><circle cx="17" cy="13" r="1.25"/>` |
| `scale` | `<path d="M12 4v16M6 20h12M5 10l2.5-5L10 10M14 10l2.5-5L19 10"/><path d="M4 10h7M13 10h7M4 10c0 2 1.3 3.5 3.5 3.5S11 12 11 10M13 10c0 2 1.3 3.5 3.5 3.5S20 12 20 10"/>` |
| `settings` | `<circle cx="12" cy="12" r="3"/><path d="M19.4 14.6a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V20a2 2 0 0 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H4a2 2 0 0 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H10a1.6 1.6 0 0 0 1-1.5V4a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V10a1.6 1.6 0 0 0 1.5 1H20a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>` |
| `home` | `<path d="M4 11l8-7 8 7v8a2 2 0 0 1-2 2h-4v-6h-4v6H6a2 2 0 0 1-2-2z"/>` |
| `swap` | `<path d="M7 7h13M17 4l3 3-3 3M17 17H4M7 14l-3 3 3 3"/>` |
| `card` | `<rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10h18M7 15h4"/>` |
| `copy` | `<rect x="9" y="9" width="11" height="11" rx="2.5"/><path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1"/>` |
| `edit` | `<path d="M4 20h4l10-10-4-4L4 16zM14 6l4 4"/>` |
| `trash` | `<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/>` |
| `dot` | `<circle cx="12" cy="12" r="4" fill="currentColor"/>` (note: `fill: currentColor`, no stroke) |
| `eye` | `<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>` |
| `download` | `<path d="M12 4v12M7 11l5 5 5-5M4 20h16"/>` |
| `sparkle` | `<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>` |
| `wifi` | `<path d="M3 9a14 14 0 0 1 18 0M6 13a9 9 0 0 1 12 0M9 17a4 4 0 0 1 6 0"/><circle cx="12" cy="20" r="1" fill="currentColor"/>` |
| `phone` | `<rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="M10 18h4"/>` |
| `moon` | `<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>` |
| `sun` | `<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/>` |
| `lock` | `<rect x="4.5" y="10" width="15" height="11" rx="2.5"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>` |
| `mail` | `<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3 7l9 7 9-7"/>` |
| `shield` | `<path d="M12 3l8 3v6c0 4.5-3.3 8.5-8 9-4.7-.5-8-4.5-8-9V6z"/><path d="M9 12.5l2 2 4-4"/>` |
| `user-plus` | `<circle cx="9" cy="8" r="3.5"/><path d="M3 20c0-3 2.5-5 6-5s6 2 6 5M18 9v6M15 12h6"/>` |
| `message` | `<path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H10l-4 4v-4H6a2 2 0 0 1-2-2z"/>` |
| `refresh` | `<path d="M4 12a8 8 0 0 1 13.7-5.7L20 9M20 4v5h-5M20 12a8 8 0 0 1-13.7 5.7L4 15M4 20v-5h5"/>` |

For all elements except `dot` and the inner `circle` of `wifi` (which use `fill="currentColor"` instead): the element gets the `stroke` set + `fill="none"`.

### 3. ExpenseDetailPage rebuild

**Path:** `web-new-version/src/modules/expenses/pages/ExpenseDetailPage.vue`

Full rewrite. Layout:

```
┌──────────────────────────────────────────────┐
│ ← Title (expense title)            [✎] [🗑] │  ← top bar with circular icon buttons
├──────────────────────────────────────────────┤
│ ┌──────────────────────────────────────┐    │
│ │ [Expense summary]                     │    │  ← brand-soft pill
│ │                                       │    │
│ │ {totalAmount} {currency}              │    │  ← 44px bold
│ │                                       │    │
│ │ {note if non-empty}                   │    │  ← decision (B): subtitle
│ │                                       │    │
│ │ Split method      Date                │    │  ← 2-col meta grid
│ │ Exact amounts     Apr 18, 2026        │    │
│ └──────────────────────────────────────┘    │
│                                              │
│ MEMBERS & PAYERS                             │  ← uppercase eyebrow
│                                              │
│ ┌──────────────────────────────────────┐    │
│ │ ⓐ @amir2115    Gets back  [+amount]  │    │  ← per-member card (creditors first)
│ │ SHARE              PAID               │    │
│ │ {amount} T         {amount} T         │    │
│ └──────────────────────────────────────┘    │
│ ┌──────────────────────────────────────┐    │
│ │ ⓣ @tavakoli      Owes      [-amount] │    │
│ │ SHARE              PAID               │    │
│ │ {amount} T         0 T                │    │
│ └──────────────────────────────────────┘    │
│ ... (one per participant, ordered: credit > debit > settled) │
└──────────────────────────────────────────────┘
```

### Member-card structure (per participant)

```vue
<article class="participant-card">
  <header class="participant-card__header">
    <Avatar :name :size="36" :tone="row.net > 0 ? 'pos' : 'brand'" />
    <div class="participant-card__meta">
      <strong class="participant-card__name"><UsernameHandle :username /></strong>
      <span class="participant-card__role" :class="{ 'is-credit': row.net > 0, 'is-debit': row.net < 0 }">
        {{ row.net > 0 ? strings.expenseGetsBackLabel : (row.net < 0 ? strings.expenseOwesLabel : strings.settledLabel) }}
      </span>
    </div>
    <span class="participant-card__net" :class="{ 'is-credit': row.net > 0, 'is-debit': row.net < 0 }">
      {{ row.net > 0 ? '+' : (row.net < 0 ? '−' : '') }}
      <AmountText :amount="row.netAbsolute" :language ... />
    </span>
  </header>
  <div class="participant-card__stats">
    <div class="participant-stat">
      <span class="participant-stat__label">{{ strings.expenseShareLabel }}</span>
      <AmountText :amount="row.owed" ... />
    </div>
    <div class="participant-stat" :class="{ 'is-paid': row.paid > 0 }">
      <span class="participant-stat__label">{{ strings.expensePaidLabel }}</span>
      <AmountText :amount="row.paid" ... :tone="row.paid > 0 ? 'primary' : 'default'" />
    </div>
  </div>
</article>
```

### Member ordering

Sort `participantRows` by `net` descending (creditors first → debtors → settled at bottom):

```ts
const participantRows = computed(() => {
  // ...existing computation...
  return rows.sort((a, b) => b.net - a.net)
})
```

### Top-bar icon buttons

Replace the current emoji buttons with circular `<button class="topbar-icon-button">` containing `<Icon name="edit" :size="14"/>` and `<Icon name="trash" :size="14"/>`. The trash button gets `is-danger` class (color: `var(--neg)`).

### Note handling (decision B)

If `expense.note` is non-empty, render it as a subtitle inside the hero summary card, BELOW the big amount and ABOVE the meta grid. Style: `font-size: 13px; color: var(--fg-muted); line-height: 1.5;`. If empty, the meta grid sits directly below the amount with a small top margin.

### Removed sections

- `<HeroCard>` — gone (replaced by inline hero summary card).
- "Payers" section — gone (paid amount is in each member card).
- "Shares" section — gone (share amount is in each member card).
- "Expense overview" `surface-card` — gone (collapsed into the new hero).

### New i18n strings

```ts
expenseSummaryPill: string             // 'خلاصه خرج' / 'Expense summary'
expenseGetsBackLabel: string           // 'پس‌گرفت' / 'Gets back'
expenseOwesLabel: string               // 'بدهی' / 'Owes'
expenseShareLabel: string              // 'سهم' / 'Share'
expensePaidLabel: string               // 'پرداخت' / 'Paid'
```

5 new keys.

### 4. App-wide icon sweep

After the component is built and used on `ExpenseDetailPage`, sweep the rest of the app.

#### Phase 1 — Emoji glyphs (5 sites)

| File | Line | Current | Replace with |
|---|---|---|---|
| `src/shared/components/BaseModal.vue` | 16 | `✕` button text content | `<Icon name="close" :size="14" />` |
| `src/shared/components/CalculatorAmountInput.vue` | 263 | `✕` button text content | `<Icon name="close" :size="14" />` |
| `src/modules/balances/pages/BalancesPage.vue` | 126 | `<EmptyStateCard ... icon="✓"/>` | Either pass `<Icon name="check"/>` if EmptyStateCard supports a node, or use the new icon as a string mapping. **Decision:** keep `icon="check"` as a string and update `EmptyStateCard.vue` to render `<Icon name="check"/>` when icon prop is a known icon name; falls back to text when not. |

The `ExpenseDetailPage.vue` ✎/🗑 buttons are handled in the page rebuild itself, not in this sweep.

#### Phase 2 — Inline SVG sweep (22 files, ~91 SVG instances)

For each file in this list, audit every inline `<svg>` block and replace each one with `<Icon name="...">`. The mapping is **shape-based**: identify the SVG by its path data and choose the matching design icon name. If a particular SVG doesn't have a clean equivalent in the design's 33-icon set, **leave it inline** and note it as an exception in the implementation plan.

Files to audit:

```
src/app/App.vue
src/shared/components/CalculatorAmountInput.vue
src/shared/components/TransferFlow.vue
src/shared/components/AmountField.vue
src/shared/components/SuggestedPaymentCard.vue
src/shared/components/PageTopBar.vue
src/modules/settings/pages/SettingsPage.vue
src/modules/settings/pages/AppDownloadPage.vue
src/modules/auth/pages/RegisterPage.vue
src/modules/auth/pages/LoginPage.vue
src/modules/auth/pages/ChangePasswordPage.vue
src/modules/auth/pages/AuthPage.vue
src/modules/auth/pages/PhoneVerificationPage.vue
src/modules/settlements/pages/SettlementEditorPage.vue
src/modules/expenses/pages/ExpenseEditorPage.vue
src/modules/groupCards/components/GroupCardsSection.vue
src/modules/groups/components/SwipeableGroupRow.vue
src/modules/groups/pages/GroupDashboardPage.vue
src/modules/groups/pages/GroupsPage.vue
src/modules/balances/components/PersonalBalancesSummary.vue
src/modules/balances/pages/BalancesPage.vue
src/modules/members/pages/MembersPage.vue
```

Common shape → icon-name mapping:
- Search magnifier (`circle cx=11 cy=11 r=...` + `M21 21-4.3-4.3` or similar) → `search`
- Plus sign (`M12 5v14M5 12h14`) → `plus`
- Right-arrow with arrowhead (`M5 12h14M13 6l6 6-6 6`) → `arrow-right`
- Left-arrow with arrowhead (`M19 12H5M11 18l-6-6 6-6`) → `arrow-left`
- Right chevron only (`M9 6l6 6-6 6` or `m9 18 6-6-6-6`) → `chevron-right`
- Left chevron (`M15 6l-6 6 6 6`) → `chevron-left`
- Down chevron (`M6 9l6 6 6-6`) → `chevron-down`
- X / close (`M6 6l12 12M18 6l-12 12`) → `close`
- Check (`M5 12.5l4.5 4.5L19 7.5` or simpler `M20 6 9 17l-5-5`) → `check`
- Pencil/edit → `edit`
- Trash → `trash`
- Cog/settings → `settings`
- Eye / show password → `eye`
- Lock → `lock`
- Phone → `phone`
- Sparkle / star burst → `sparkle`
- Swap (two arrows) → `swap`
- Sun → `sun`, Moon → `moon`
- WiFi → `wifi`
- House → `home`
- Mail → `mail`
- Shield → `shield`
- Refresh / circular arrow → `refresh`
- Download → `download`
- Speech bubble → `message`
- User → `users`
- Card → `card`

Direction-aware swaps (e.g., `<template v-if="isRtl"><path .../></template><template v-else><path .../></template>` patterns where one branch has a right-arrow and the other a left-arrow): replace with `<Icon :name="isRtl ? 'arrow-left' : 'arrow-right'" />` (or chevron variants), preserving the existing direction semantics.

Some inline SVGs may not match any of the 33 design icons (e.g., the home navigation icon in App.vue is path `M4 11l8-7 8 7v8a2 2 0 0 1-2 2h-4v-6h-4v6H6a2 2 0 0 1-2-2z` — that **is** the design's `home` icon, so it gets replaced). Settings cog in App.vue → `settings`. The svg pulse / loader animations in CalculatorAmountInput, AmountField — leave these inline (animated visual effects, not flat icons).

#### Phase 3 — `HeroCard :icon="..."` audit

Existing `<HeroCard :icon="..."/>` consumers pass single-character glyphs (e.g., `icon="◧"`, `icon="✓"`). After Phase 1's `EmptyStateCard` change, audit the remaining `<HeroCard>` consumers and either:
- Pass an `<Icon name="...">` Vue node where the prop accepts a default-slot fallback; or
- Switch the prop's contract to accept an icon name string (with HeroCard internally rendering `<Icon name="...">`).

Recommendation: change `HeroCard.vue`'s `icon` prop to render `<Icon name="...">` when the value matches a known icon name; preserve the text-fallback path for emoji glyphs that have no design equivalent.

### Single-commit vs multi-commit

The user previously requested single-commit sweeps. The Phase 2 sweep across 22 files is large; structure as **per-file group** commits to make per-task review tractable, while keeping the overall plan a single coherent rollout. If the user prefers one commit, the plan can collapse Phase 2's per-file commits into one.

## Files affected

| File | Type | Change |
|---|---|---|
| `src/shared/components/Icon.vue` | **create** | New component with all 33 icons + named type |
| `tests/icon.test.ts` | **create** | Two contract tests verifying SVG render for known/unknown names |
| `src/shared/i18n/strings.ts` | modify | Add 5 new keys |
| `src/modules/expenses/pages/ExpenseDetailPage.vue` | modify | **Full rewrite** — script + template + scoped CSS |
| `src/shared/components/BaseModal.vue` | modify | Replace `✕` emoji with `<Icon name="close">` |
| `src/shared/components/CalculatorAmountInput.vue` | modify | Replace `✕` emoji with `<Icon name="close">` (keep animated SVGs as-is) |
| `src/shared/components/EmptyStateCard.vue` | modify | Render `<Icon name="...">` when prop matches a known icon name |
| `src/shared/components/HeroCard.vue` | modify | Same icon-name prop handling as `EmptyStateCard` |
| Phase-2 SVG-sweep files (22 total — listed above) | modify | Per-file SVG → `<Icon name="...">` audit |

## Edge cases

- **Icon name not in the registry.** The component renders nothing (or a small visual indicator in dev). TypeScript prevents most cases via the `IconName` union.
- **`size` undefined.** Defaults to 18 (matches design's default).
- **RTL direction-aware icons.** The component itself does not auto-flip — consumers pass `:name="isRtl ? 'arrow-left' : 'arrow-right'"` (or `chevron-left/right`) explicitly. This matches the design's pattern and the existing `isRtl` ternaries already in the codebase.
- **SVGs that are not flat icons** (e.g., loader spinners, animated check marks in `CalculatorAmountInput`/`AmountField`, decorative graphics) — left inline, NOT migrated. The plan's per-file audit explicitly excludes them.
- **Decorative SVG without an exact design equivalent** — left inline. The plan documents these as exceptions per file.
- **`HeroCard`/`EmptyStateCard` icon prop with text/emoji fallback** — components must continue to accept text values gracefully (no breakage if a stale consumer passes a glyph). The `<Icon>` rendering branch only activates for known names.

## Testing

- **Component tests** for `Icon`:
  - `it('renders an <svg> for a known name')` — mount with `name="edit"`, assert `<svg>` exists with non-empty `<path>` child.
  - `it('renders nothing for an unknown name')` — mount with a TypeScript-cast invalid name, assert no `<svg>` element.
  - (Optional) `it('respects the size prop')` — mount with `size=24`, assert `width="24"` `height="24"` on the SVG.
- **Existing tests** continue to pass (`group-balances`, `username-handle`, etc.) — Icon migration is presentational, no logic changes.
- **Manual visual gate** is the final contract: walk every modified page in `fa` and `en`, confirm icons render at the expected size + position with consistent stroke style.

## Out of scope (followup)

- Icon size variants beyond a `size: number` prop (e.g., `size="sm" | "md" | "lg"`). The design uses raw pixel sizes; we do the same.
- Icon color variants beyond `currentColor` inheritance. Consumers set color on the parent.
- Animation icons (shake, spin) — deferred until a real consumer needs them.
- A storybook / icon-gallery page for browsing the registry — could be added later.
- Icons that the design doesn't include (e.g., a "drag handle" / hamburger / share icon) — add them ad-hoc when a consumer needs them, not preemptively.
