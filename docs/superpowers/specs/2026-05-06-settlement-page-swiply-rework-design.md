# Settlement Page — Swiply Redesign Rework

**Date:** 2026-05-06
**Scope:** `web-new-version` PWA — full rebuild of `SettlementEditorPage.vue`
**Source design:** Swiply Redesign — `SettlementScreen` component (extracted from gzipped HTML at the user-supplied design URL; cached locally as `/tmp/swiply-design-2.html`)

## Context

The current Settlement page in `web-new-version/src/modules/settlements/pages/SettlementEditorPage.vue` has two visible problems on small viewports (per user screenshots):

1. **Horizontal overflow** — the page extends beyond the viewport, requiring horizontal scroll to see the full UI. Caused by the chip rows + amount input + textarea each contributing intrinsic widths that exceed the viewport on a phone-sized screen, with no `min-width: 0` flex hygiene.
2. **Layout doesn't match the Swiply Redesign** — the design replaces the current chip-picker pattern with a slot-based picker plus an active searchable member panel.

Both problems get solved by **rebuilding the page to match the Swiply design** rather than patching the existing layout. The new layout is more compact and inherently fits viewport widths, so the overflow bug doesn't recur.

## Goal

Rebuild `SettlementEditorPage.vue` so that, in both `fa` (RTL) and `en` (LTR), it matches the Swiply Redesign Settlement screen exactly, including: step indicator, two-slot hero with swap button, active searchable picker (with search input, "recently settled with" rail, and full member list with balance hints), and a compact amount/note section at the bottom.

## Non-goals

- No data-layer changes — the form payload (`from_member_id`, `to_member_id`, `amount`, `note`) and the existing `settlementsStore.save(...)` API stay unchanged.
- No changes to suggested-amount derivation logic (`suggestedAmount` computed from `simplified_debts`) — only the visual presentation changes.
- No new translations for the Swiply Redesign UX strings (`"Recently settled with"`, `"All members"`, `"Search a member"`, etc.) beyond what's needed; we'll add them in `strings.ts`.
- No backend changes.

## High-level layout (per design)

```
┌─────────────────────────────────────────┐
│ Top bar:  ← title         [Save]        │
├─────────────────────────────────────────┤
│ Step indicator:                          │
│   [Step 1] ━━━━━●━━━━━━━━ [Step 2]      │
│   (brand color when active for that side)│
├─────────────────────────────────────────┤
│ Hero card (two slots + swap button):    │
│  ┌──────────────┐ ⇄ ┌──────────────┐   │
│  │  Avatar 56   │   │ Avatar or +  │   │
│  │  PAYER       │   │ RECEIVER     │   │
│  │  @amir2115   │   │ Tap to pick  │   │
│  └──────────────┘   └──────────────┘   │
├─────────────────────────────────────────┤
│ Active picker card:                      │
│  CHOOSE WHO PAID (or GOT PAID)          │
│  [🔍 Search a member          [count]]  │
│  RECENTLY SETTLED WITH                   │
│  [@tav][@moe][...]                       │
│  ALL MEMBERS                              │
│  ⚪ @tavakoli  owes 272,000           ›  │
│  ⚪ @sultan    is owed 136,000        ›  │
│  ⚪ @maedeh    settled                ›  │
├─────────────────────────────────────────┤
│ Amount:                                  │
│  272,000                              T │
│  ● Suggested from current balances       │
├─────────────────────────────────────────┤
│ Note:                                    │
│  [textarea]                              │
└─────────────────────────────────────────┘
```

## Architecture

### State changes

Add a single new ref:

```ts
const activeStep = ref<'from' | 'to'>('from')
```

Determines which slot the active picker panel is filling. Initial value: `'from'` for new settlements; `'to'` if `from_member_id` is already pre-filled (via route query). When the user taps the "from" slot, it becomes `'from'`. When they tap a member in the picker, the corresponding `form.from_member_id` or `form.to_member_id` updates and `activeStep` advances (`'from'` → `'to'`; `'to'` → stays `'to'` so amount/note can be entered without picker churn).

Also add:

```ts
const searchQuery = ref('')
```

For filtering the picker's member list.

### Computed

```ts
const filteredMembers = computed(() => {
  const otherSlot = activeStep.value === 'from' ? form.to_member_id : form.from_member_id
  const query = searchQuery.value.trim().toLowerCase()
  return members.value
    .filter((m) => m.id !== otherSlot)
    .filter((m) => !query || m.username.toLowerCase().includes(query))
})

const recentMembers = computed(() => {
  const otherSlot = activeStep.value === 'from' ? form.to_member_id : form.from_member_id
  const recents = new Map<string, number>()
  ;(settlementsByGroupId.value[groupId] ?? [])
    .slice()
    .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
    .forEach((s) => {
      const counterpart = activeStep.value === 'from' ? s.from_member_id : s.to_member_id
      if (counterpart === otherSlot || counterpart === '') return
      if (!recents.has(counterpart)) recents.set(counterpart, recents.size)
    })
  return Array.from(recents.keys())
    .map((id) => members.value.find((m) => m.id === id))
    .filter((m): m is NonNullable<typeof m> => Boolean(m))
    .slice(0, 4)
})

const balanceHintFor = (memberId: string) => {
  const balance = balanceResponse.value?.balances.find((b) => b.member_id === memberId)
  if (!balance || balance.net_balance === 0) return { kind: 'settled' as const, amount: 0 }
  if (balance.net_balance > 0) return { kind: 'owed' as const, amount: balance.net_balance }   // member is creditor
  return { kind: 'owes' as const, amount: Math.abs(balance.net_balance) }                       // member is debtor
}
```

### Template structure (top → bottom)

1. **`<PageTopBar>`** (existing) — title + Save button via `#actions` slot. Save button is `filled-button--sm` brand-colored when both `from_member_id` and `to_member_id` are set, otherwise `outline-button` style (per design's `variant={fromUser && toUser ? "primary" : "ghost"}`).
2. **Inline error alert** (existing `InlineAlert` — preserved as-is).
3. **`<div class="step-indicator">`** — flex row with "Step 1" label, progress bar (1-px-tall pill), "Step 2" label. Progress bar's filled portion is 50% if `activeStep === 'from'`, 100% if `activeStep === 'to'`. Labels color-coded: brand for active step, subtle for inactive.
4. **`<div class="settlement-hero">`** — two `<button class="settlement-slot">` siblings + a centered `<button class="settlement-swap">` swap button. Each slot has:
   - Avatar (56px) — tone `brand` for from, `accent` for to. When empty, an inline-styled circle with a `+` icon.
   - Role label (uppercase: PAYER / RECEIVER) — brand color for from, accent color for to.
   - Username (`@username`) when filled, "Tap to pick" placeholder when empty.
   - Border: 1.5px solid brand/accent when active; 1px solid `--border` when filled-but-not-active; 1px dashed `--border-strong` when empty.
   - Background: `brand-soft` / `accent-soft` when active; transparent otherwise.
5. **`<div class="picker-panel">`** — bordered card with three subsections:
   - **Picker header** with role label ("Choose who paid" / "Choose who got paid") + search input. Search input is a flex row with a search SVG icon, an `<input v-model="searchQuery">`, and a small count badge showing filtered member count.
   - **Recently settled rail** — horizontal scroll of small chips (32px avatar + truncated username). Hidden if no recents.
   - **All members list** — vertical list of member rows. Each row: 38px avatar, `<UsernameHandle>`, balance hint sub-line ("owes X / is owed X / settled" with corresponding color), chevron icon. Click sets the matching `form` field and advances `activeStep`.
6. **`<div class="amount-block">`** — bordered card with `Amount` label, the formatted amount (32px font), currency suffix. If `suggestedAmount > 0`, a sub-line with a small brand dot and "Suggested: <amount> Toman" — clicking the sub-line fills the amount.
7. **`<div class="form-field">`** — Note textarea (existing `text-area` class).
8. **Delete button** (when `isEdit`) — preserved as-is.

### Components

Decision: **inline everything in `SettlementEditorPage.vue` rather than extracting sub-components.** The page after rebuild is ~400 lines of template + scoped CSS. That's at the upper end of "comfortable single-file Vue SFC" but breaking it into 4–5 sub-components (slot, picker, amount block, etc.) would scatter the template across files for a feature that's used in exactly one place.

**Reusable bits already in the codebase that we'll continue to use:**
- `<Avatar>` (existing)
- `<UsernameHandle>` (existing — covers `@username` rendering with bidi correctness)
- `<AmountText>` (existing — for the amount preview)
- `<PageTopBar>` (existing)
- `<InlineAlert>` (existing)
- `formatAmountInput`, `digitsOnly`, `parseAmountInput`, `isAmountOverflow` (existing utilities)
- `useMembersStore`, `useSettlementsStore`, `useBalancesStore`, `useSettingsStore`, `useSnackbarStore` (existing stores)
- Existing CSS tokens (`--surface`, `--border`, `--brand`, `--accent`, `--brand-soft`, etc.)

**No new components.** No new shared utilities.

### CSS approach

All styles in the page's `<style scoped>` block. New class names:
- `.settlement-step-indicator`, `.settlement-step-indicator__progress`, `.settlement-step-indicator__progress-fill`
- `.settlement-hero`, `.settlement-slot`, `.settlement-slot.is-active`, `.settlement-slot.is-empty`, `.settlement-slot__avatar-empty`, `.settlement-slot__role`, `.settlement-slot__name`, `.settlement-swap`
- `.picker-panel`, `.picker-panel__header`, `.picker-panel__role`, `.picker-search`, `.picker-search__count`, `.picker-recent`, `.picker-recent__chip`, `.picker-section-label`, `.picker-list`, `.picker-row`, `.picker-row__balance` (with `.is-pos`/`.is-neg`/`.is-settled` modifiers)
- `.amount-block`, `.amount-block__label`, `.amount-block__value`, `.amount-block__suffix`, `.amount-block__hint`, `.amount-block__hint-dot`

The existing `.settlement-page` `padding-top: 2px;` rule stays; everything else in the existing scoped CSS block is **deleted** and replaced.

### Behavior

- **Initial state.** On mount: load members/settlements/balances. If editing: pre-fill all 4 form fields from `settlement`; `activeStep` defaults to `'from'`. If new: `from_member_id` defaults to route-query `from` or first member; `to_member_id` defaults to route-query `to` or second member; `activeStep` defaults to `'from'` unless route-query has `to` already pre-set, in which case start at `'to'`. (This preserves the existing behavior where a "settle this debt" button on the Balances page deep-links into the settlement editor with from/to/amount pre-filled.)
- **Tapping a slot.** Sets `activeStep` to that slot's role. Doesn't clear the slot's value. Picker panel updates its title and content immediately.
- **Tapping a member in the picker.** Updates the matching `form` field. Auto-advances: if `activeStep` was `'from'`, advance to `'to'`; if `'to'` and `from_member_id` is empty, switch to `'from'`; otherwise stay on `'to'` (so the user can switch focus to the amount).
- **Swap button.** Swaps `from_member_id` ↔ `to_member_id`. Doesn't change `activeStep`.
- **Search input.** Filters the visible member list with case-insensitive substring match on username. Doesn't filter the recent rail (recents stay in their own section).
- **Recent rail.** Shows up to 4 distinct counterparts from the user's settlement history with the active slot's role. Clicking a recent chip behaves identically to clicking the same member in the all-members list.
- **Amount block.** Same input flow as today but visual is compact (32px font on the value, currency suffix). The suggested-amount affordance is now a small hint line below the value with a brand dot, not a separate large pill button.
- **Save flow.** Unchanged. The existing `submit()` validation and `settlementsStore.save(...)` call stay.

### Strings to add

In `web-new-version/src/shared/i18n/strings.ts`, add (interface + fa + en):

```ts
settlementStep1: string                  // 'مرحله ۱' / 'Step 1'
settlementStep2: string                  // 'مرحله ۲' / 'Step 2'
settlementChoosePayer: string            // 'انتخاب پرداخت‌کننده' / 'Choose who paid'
settlementChooseReceiver: string         // 'انتخاب دریافت‌کننده' / 'Choose who got paid'
settlementSearchMember: string           // 'جست‌وجوی عضو' / 'Search a member'
settlementRecentLabel: string            // 'آخرین تسویه‌ها' / 'Recently settled with'
settlementAllMembersLabel: string        // 'همه اعضا' / 'All members'
settlementSwapLabel: string              // 'جابه‌جایی' / 'Swap'
settlementTapToPick: string              // 'انتخاب کن' / 'Tap to choose'
settlementMemberOwesLabel: string        // 'بدهکار {amount}' / 'owes {amount}'
settlementMemberOwedLabel: string        // 'طلبکار {amount}' / 'is owed {amount}'
settlementMemberSettledLabel: string     // 'تسویه' / 'settled'
settlementSuggestedAmountHint: string    // 'مبلغ پیشنهادی از مانده‌های فعلی' / 'Suggested from current balances'
```

(13 new keys.)

## Edge cases

- **Member list with only 2 members.** Search input still renders (degenerate but consistent). Recent rail renders empty / hidden. Filter still excludes the other slot's selection.
- **Editing a settlement when the original counterparts left the group.** `members.value.find()` returns undefined → empty avatar (`'?'` fallback) + "—" name. Slot still tappable to choose a real current member.
- **No prior settlements (recents empty).** Recent rail is hidden (no header, no rail).
- **`from_member_id` and `to_member_id` both unset.** Slots both empty (dashed border + plus icon). Save button shown but in `outline-button` style; submit() still validates with the existing `SETTLEMENT_SELECT_TWO_MEMBERS` message.
- **Amount input on small phones.** Compact amount block sits in a bordered card; the value uses `flex: 1` with `min-width: 0` so the currency suffix never causes overflow.

## Testing

- **Unit tests:** none planned. The behavior changes are presentational + interaction; the data and validation flows are unchanged. Existing `tests/group-balances.test.ts` remains untouched. No new component tests follow the codebase's existing pattern (which is sparse on Vue component tests).
- **Type-check:** `npm run build` passes (the implementation must satisfy TypeScript with the existing `Member`, `Settlement`, `GroupBalanceResponse` types).
- **Manual verification:** primary gate. Walk the page in `fa` and `en`:
  1. New settlement (no deep link): Step 1 active, both slots empty, picker shows "Choose who paid".
  2. Pick a payer → step indicator advances to Step 2, picker swaps to "Choose who got paid", from-slot now filled.
  3. Pick a receiver → both slots filled, save button becomes filled-style.
  4. Tap swap → slot contents swap.
  5. Tap from-slot → activeStep returns to `'from'`, picker re-opens for from.
  6. Type in search → list filters live.
  7. Recent rail shows 1–4 most recent counterparts (or hidden if none).
  8. Each member row shows the right balance hint with the right color.
  9. Amount block — tap the suggested-amount hint, it fills the input.
  10. RTL: layout reads right-to-left, swap icon flips appropriately, member rows align text to the right.
  11. **Critical:** entire page fits within a 360px-wide viewport. No horizontal scroll.
  12. Save flow unchanged; deep link from Balances page (?from=A&to=B&amount=N) still pre-fills.

## File map

| File | Type | Change |
|---|---|---|
| `web-new-version/src/modules/settlements/pages/SettlementEditorPage.vue` | modify | **Full rewrite** — keep `<script>` data wiring, replace template + scoped CSS to match the Swiply design; add new state (`activeStep`, `searchQuery`, computed helpers, `swap()` function) |
| `web-new-version/src/shared/i18n/strings.ts` | modify | Add 13 new keys (interface + fa + en values) |

No new files created. No files deleted. No utility helpers extracted (everything stays inline in the page until/unless reuse is needed).

## Out of scope

- Sticky save bar at the bottom of long forms.
- Picker animations (active step transitions, picker fade in/out).
- Multi-select / split settlements.
- Empty-state illustration when there are no members in the group.
- Migrating other settlement-adjacent surfaces (settlement detail page, settlement history list) to match the redesign — this plan covers `SettlementEditorPage.vue` only.
