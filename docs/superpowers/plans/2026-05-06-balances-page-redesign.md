# Balances Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `web-new-version`'s Balances page to visual + functional parity with the Swiply Redesign mock (remove Optimal-Payment-Mode toggle, add expandable per-member breakdowns, fix RTL/LTR arrow handling systematically).

**Architecture:** UI-only changes in two `.vue` files plus three new i18n keys. One small pure helper added to `groupBalances.ts` (with unit tests) projects per-member breakdowns from existing `simplified_debts`. Arrow direction handled by the existing `:root[dir='rtl'] .suggested-arrow { transform: scaleX(-1) }` rule in `app.css` — replace `v-if="isRtl"` SVG branches with a single arrow + class.

**Tech Stack:** Vue 3 (composition API + `<script setup>`), Pinia, TypeScript, Vitest, Vite. Working directory for all commands is `web-new-version/`.

**Spec:** `docs/superpowers/specs/2026-05-06-balances-page-redesign-design.md`

---

## File Map

| File | Change |
|---|---|
| `web-new-version/src/modules/balances/groupBalances.ts` | **Modify** — add `projectMemberBreakdown` helper + `MemberBreakdownEntry` type |
| `web-new-version/tests/group-balances.test.ts` | **Modify** — add tests for the new helper |
| `web-new-version/src/shared/i18n/strings.ts` | **Modify** — add 3 new keys (interface + fa + en) |
| `web-new-version/src/shared/components/SuggestedPaymentCard.vue` | **Modify** — replace conditional SVG arrows with `.suggested-arrow` class |
| `web-new-version/src/modules/balances/pages/BalancesPage.vue` | **Modify** — remove toggle, fix arrows, restyle member rows, add expand + breakdown |

---

## Task 1: Add `projectMemberBreakdown` helper (TDD)

**Files:**
- Modify: `web-new-version/src/modules/balances/groupBalances.ts`
- Modify: `web-new-version/tests/group-balances.test.ts`

This pure-function seam keeps the breakdown filter testable. The component will import and call it.

- [ ] **Step 1: Add the failing tests at the bottom of `tests/group-balances.test.ts`**

Append (do not replace existing tests):

```ts
import { projectMemberBreakdown } from '@/modules/balances/groupBalances'

describe('projectMemberBreakdown', () => {
  const transfers = [
    { from_member_id: 'sultan', to_member_id: 'amir', amount: 272000 },
    { from_member_id: 'moein', to_member_id: 'amir', amount: 136000 },
    { from_member_id: 'sultan', to_member_id: 'feri', amount: 50000 },
  ]

  it('returns incoming entries for a creditor (net > 0)', () => {
    const entries = projectMemberBreakdown('amir', 408000, transfers)
    expect(entries).toEqual([
      { transfer: transfers[0], other_member_id: 'sultan', kind: 'incoming' },
      { transfer: transfers[1], other_member_id: 'moein', kind: 'incoming' },
    ])
  })

  it('returns outgoing entries for a debtor (net < 0)', () => {
    const entries = projectMemberBreakdown('sultan', -322000, transfers)
    expect(entries).toEqual([
      { transfer: transfers[0], other_member_id: 'amir', kind: 'outgoing' },
      { transfer: transfers[2], other_member_id: 'feri', kind: 'outgoing' },
    ])
  })

  it('returns an empty list for a settled member (net === 0)', () => {
    const entries = projectMemberBreakdown('amir', 0, transfers)
    expect(entries).toEqual([])
  })

  it('returns an empty list when there are no transfers', () => {
    const entries = projectMemberBreakdown('amir', 100, [])
    expect(entries).toEqual([])
  })
})
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
cd web-new-version && npm test -- group-balances
```

Expected: 4 new tests fail with "projectMemberBreakdown is not a function" (or similar import error). The existing `deriveGroupBalances` tests should still pass.

- [ ] **Step 3: Implement the helper in `groupBalances.ts`**

Append at the end of `web-new-version/src/modules/balances/groupBalances.ts` (after `deriveGroupBalances`):

```ts
export interface MemberBreakdownEntry {
  transfer: GroupBalanceResponse['simplified_debts'][number]
  other_member_id: string
  kind: 'incoming' | 'outgoing'
}

export function projectMemberBreakdown(
  memberId: string,
  netBalance: number,
  simplifiedDebts: GroupBalanceResponse['simplified_debts'],
): MemberBreakdownEntry[] {
  if (netBalance === 0) return []
  if (netBalance > 0) {
    return simplifiedDebts
      .filter((transfer) => transfer.to_member_id === memberId)
      .map((transfer) => ({ transfer, other_member_id: transfer.from_member_id, kind: 'incoming' as const }))
  }
  return simplifiedDebts
    .filter((transfer) => transfer.from_member_id === memberId)
    .map((transfer) => ({ transfer, other_member_id: transfer.to_member_id, kind: 'outgoing' as const }))
}
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
cd web-new-version && npm test -- group-balances
```

Expected: all `projectMemberBreakdown` and existing `deriveGroupBalances` tests pass.

- [ ] **Step 5: Commit**

```bash
git add web-new-version/src/modules/balances/groupBalances.ts web-new-version/tests/group-balances.test.ts
git commit -m "feat(balances): add projectMemberBreakdown helper for per-member breakdown view"
```

---

## Task 2: Add new i18n strings

**Files:**
- Modify: `web-new-version/src/shared/i18n/strings.ts`

- [ ] **Step 1: Add three keys to the `AppStrings` interface**

In `web-new-version/src/shared/i18n/strings.ts`, find the line `memberBalanceTitle: string` (around line 249) and add three new lines immediately after it:

```ts
  memberBalanceTitle: string
  tapForBreakdown: string
  breakdownOwedByTitle: string
  breakdownOwesToTitle: string
  suggestedPaymentsTitle: string
```

- [ ] **Step 2: Add Persian (`fa`) values**

In the `fa` object, find `memberBalanceTitle: 'مانده هر نفر',` (around line 580) and add three lines after it:

```ts
  memberBalanceTitle: 'مانده هر نفر',
  tapForBreakdown: 'برای جزئیات بزن',
  breakdownOwedByTitle: 'طلبکار از این افراد',
  breakdownOwesToTitle: 'بدهکار به این افراد',
  suggestedPaymentsTitle: 'پرداخت‌های پیشنهادی',
```

- [ ] **Step 3: Add English (`en`) values**

In the `en` object, find `memberBalanceTitle: 'Member balances',` (around line 911) and add three lines after it:

```ts
  memberBalanceTitle: 'Member balances',
  tapForBreakdown: 'Tap for breakdown',
  breakdownOwedByTitle: 'Owed by these people',
  breakdownOwesToTitle: 'Owes these people',
  suggestedPaymentsTitle: 'Suggested payments',
```

- [ ] **Step 4: Verify type-check passes**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add web-new-version/src/shared/i18n/strings.ts
git commit -m "feat(i18n): add tapForBreakdown and breakdown title strings for balances page"
```

---

## Task 3: Fix arrow handling in `SuggestedPaymentCard.vue`

**Files:**
- Modify: `web-new-version/src/shared/components/SuggestedPaymentCard.vue`

This component is shared with other pages (e.g., dashboard's next-best-action). Fix it first so its consumers benefit too.

- [ ] **Step 1: Replace the entire `<script setup>` block**

Replace lines 1–26 of `SuggestedPaymentCard.vue` with:

```vue
<script setup lang="ts">
import AmountText from '@/shared/components/AmountText.vue'
import Avatar from '@/shared/components/Avatar.vue'
import type { AppLanguage } from '@/shared/api/types'

const props = withDefaults(
  defineProps<{
    from: string
    to: string
    amount: number
    language: AppLanguage
    icon?: string
    tone?: 'default' | 'success' | 'danger'
  }>(),
  {
    icon: '',
    tone: 'default',
  },
)

void props.tone
</script>
```

(The `useSettingsStore` import and `isRtl` computed are no longer needed — direction is handled by CSS via `.suggested-arrow`.)

- [ ] **Step 2: Replace the avatar/arrow markup**

In the same file, replace the `<span class="suggested-card__arrow">` block (the one with `<template v-if="isRtl">` and `<template v-else>`) with:

```vue
        <span class="suggested-card__arrow suggested-arrow" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14" />
            <path d="M13 6l6 6-6 6" />
          </svg>
        </span>
```

(One arrow that always points `→`. The `.suggested-arrow` class — defined in `app.css` — flips it via `transform: scaleX(-1)` when `[dir='rtl']`.)

- [ ] **Step 3: Replace the hardcoded `→` in the meta subtitle**

In the same file, find:

```vue
    <span class="suggested-card__sub">→ {{ to }}</span>
```

Replace with:

```vue
    <span class="suggested-card__sub">
      <span class="suggested-arrow" aria-hidden="true">→</span>
      {{ to }}
    </span>
```

- [ ] **Step 4: Verify type-check + build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web-new-version/src/shared/components/SuggestedPaymentCard.vue
git commit -m "fix(suggested-payment-card): drive arrow direction from CSS instead of v-if isRtl"
```

---

## Task 4: Remove toggle + chip from `BalancesPage.vue`

**Files:**
- Modify: `web-new-version/src/modules/balances/pages/BalancesPage.vue`

- [ ] **Step 1: Remove the `simplify` ref**

In `BalancesPage.vue`, delete this line (around line 34):

```ts
const simplify = ref(true)
```

- [ ] **Step 2: Remove the unused `ref` import if no longer needed**

Check the top of `<script setup>`. Line 2 imports `ref`. After Task 6 we'll add it back for `expandedMemberId`, but for now leave the import in place even if unused — Task 6 will use it. (Vue's `unused import` lint won't block the build.)

- [ ] **Step 3: Delete the `<template #actions>` slot in `<PageTopBar>`**

Delete lines 77–84 of the original file (the entire `<template #actions>` block):

```vue
      <template #actions>
        <span v-if="simplify" class="chip chip--brand">
          <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>
          </svg>
          {{ strings.optimizePaymentsTitle }}
        </span>
      </template>
```

The `<PageTopBar>` opening tag becomes self-contained:

```vue
    <PageTopBar :title="`${strings.balancesPrefix} ${group?.name ?? ''}`" can-go-back sticky @back="router.back()" />
```

- [ ] **Step 4: Delete the switch-field block**

Delete the entire `<!-- Toggle simplify -->` comment and its `<div class="surface-card switch-field">` block (lines 93–102 of the original):

```vue
    <!-- Toggle simplify -->
    <div class="surface-card switch-field" style="align-items: center;">
      <div class="switch-field__content">
        <strong class="switch-field__title">{{ strings.optimizePaymentsTitle }}</strong>
        <div class="muted">{{ strings.optimizePaymentsSubtitle }}</div>
      </div>
      <label class="switch-button" :class="{ 'is-on': simplify }">
        <input v-model="simplify" class="switch-button__input" type="checkbox" />
      </label>
    </div>
```

- [ ] **Step 5: Unwrap the `<template v-if="simplify">` around the suggested chain**

Find the `<!-- Suggested chain -->` comment (around line 104). Replace:

```vue
    <!-- Suggested chain -->
    <template v-if="simplify">
      <div class="suggested-stack">
        ...
      </div>
    </template>
```

…with the inner `<div class="suggested-stack">` only (no `<template v-if>` wrapper). Suggested payments are now always shown.

- [ ] **Step 6: Verify build passes**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds. The page should now have no toggle and no top-bar chip.

- [ ] **Step 7: Commit**

```bash
git add web-new-version/src/modules/balances/pages/BalancesPage.vue
git commit -m "feat(balances): remove optimal-payment-mode toggle and top-bar chip"
```

---

## Task 5: Fix arrow handling in `BalancesPage.vue` suggested rows

**Files:**
- Modify: `web-new-version/src/modules/balances/pages/BalancesPage.vue`

- [ ] **Step 1: Replace the conditional SVG arrow inside the suggested row**

Find this block in `BalancesPage.vue` (inside the `<button class="suggested-row">`):

```vue
          <span class="suggested-row__arrow">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
              <template v-if="isRtl"><path d="M19 12H5"/><path d="M11 18l-6-6 6-6"/></template>
              <template v-else><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></template>
            </svg>
          </span>
```

Replace with:

```vue
          <span class="suggested-row__arrow suggested-arrow" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
              <path d="M5 12h14" />
              <path d="M13 6l6 6-6 6" />
            </svg>
          </span>
```

- [ ] **Step 2: Replace the hardcoded `→` in the meta subtitle**

Find:

```vue
            <span class="muted">→ @{{ memberName(transfer.to_member_id) }}</span>
```

Replace with:

```vue
            <span class="muted">
              <span class="suggested-arrow" aria-hidden="true">→</span>
              @{{ memberName(transfer.to_member_id) }}
            </span>
```

- [ ] **Step 3: Remove the now-unused `isRtl` computed**

In `<script setup>`, delete this line (the only consumer was the conditional SVG just removed):

```ts
const isRtl = computed(() => settingsStore.direction === 'rtl')
```

- [ ] **Step 4: Verify build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds. If it fails complaining about unused `computed` import, leave it — Task 6 will use it.

- [ ] **Step 5: Commit**

```bash
git add web-new-version/src/modules/balances/pages/BalancesPage.vue
git commit -m "fix(balances): drive suggested-row arrow direction from CSS instead of isRtl branches"
```

---

## Task 6: Add expandable per-member rows with breakdown

**Files:**
- Modify: `web-new-version/src/modules/balances/pages/BalancesPage.vue`

This task replaces the entire per-member section (template + new `<style scoped>` rules) and the surrounding `<script setup>` plumbing.

- [ ] **Step 1: Add imports + state in `<script setup>`**

Near the top of `<script setup>`, ensure these imports exist (add `projectMemberBreakdown` and `MemberBreakdownEntry`):

```ts
import { computed, onMounted, ref } from 'vue'
import { deriveGroupBalances, projectMemberBreakdown, type MemberBreakdownEntry } from '@/modules/balances/groupBalances'
```

Add the expanded-row state below `simplify` (which was deleted in Task 4 — add this in its place if not already present):

```ts
const expandedMemberId = ref<string | null>(null)

function toggleExpanded(memberId: string) {
  expandedMemberId.value = expandedMemberId.value === memberId ? null : memberId
}

function breakdownFor(memberId: string, netBalance: number): MemberBreakdownEntry[] {
  return projectMemberBreakdown(memberId, netBalance, balanceResponse.value?.simplified_debts ?? [])
}

function payBreakdownEntry(entry: MemberBreakdownEntry, event: Event) {
  event.stopPropagation()
  goToSuggestedSettlement(entry.transfer)
}
```

- [ ] **Step 2: Replace the eyebrow + per-member section in the template**

Find this block (around line 140 of the original):

```vue
    <!-- Per member -->
    <h3 class="eyebrow">{{ strings.memberBalanceTitle }}</h3>
    <div class="member-list">
      <div
        v-for="balance in balanceResponse?.balances ?? []"
        :key="balance.member_id"
        class="member-balance-row"
      >
        ...all existing member-row markup...
      </div>
    </div>
```

Replace the entire block (eyebrow + `member-list` div) with:

```vue
    <!-- Per member -->
    <div class="member-list-eyebrow">
      <h3 class="eyebrow">{{ strings.memberBalanceTitle }}</h3>
      <span class="member-list-eyebrow__hint">{{ strings.tapForBreakdown }}</span>
    </div>
    <div class="member-list-card">
      <template v-for="balance in balanceResponse?.balances ?? []" :key="balance.member_id">
        <component
          :is="balance.net_balance === 0 ? 'div' : 'button'"
          :type="balance.net_balance === 0 ? undefined : 'button'"
          class="member-row"
          :class="{ 'is-expanded': expandedMemberId === balance.member_id }"
          :aria-expanded="balance.net_balance === 0 ? undefined : (expandedMemberId === balance.member_id)"
          @click="balance.net_balance === 0 ? null : toggleExpanded(balance.member_id)"
        >
          <Avatar
            :name="balance.member_name"
            :tone="balance.net_balance > 0 ? 'brand' : balance.net_balance < 0 ? 'accent' : 'settled'"
            :size="36"
          />
          <div class="member-row__body">
            <strong>@{{ balance.member_name }}</strong>
            <span
              class="member-row__label"
              :class="{
                'is-pos': balance.net_balance > 0,
                'is-neg': balance.net_balance < 0,
                'is-settled': balance.net_balance === 0,
              }"
            >
              {{
                balance.net_balance > 0
                  ? strings.creditorLabel
                  : balance.net_balance < 0
                    ? strings.debtorLabel
                    : strings.settledLabel
              }}
            </span>
          </div>
          <div
            class="member-row__amount num"
            :class="{
              'is-pos': balance.net_balance > 0,
              'is-neg': balance.net_balance < 0,
              'is-settled': balance.net_balance === 0,
            }"
          >
            <span v-if="balance.net_balance === 0">—</span>
            <template v-else>
              <span class="member-row__amount-sign">{{ balance.net_balance > 0 ? '+' : '−' }}</span>
              <AmountText
                :amount="Math.abs(balance.net_balance)"
                :language="language"
                :tone="balance.net_balance > 0 ? 'success' : 'danger'"
              />
            </template>
          </div>
          <span
            v-if="balance.net_balance !== 0"
            class="member-row__chevron"
            :class="{ 'is-open': expandedMemberId === balance.member_id }"
            aria-hidden="true"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </span>
        </component>
        <div
          v-if="expandedMemberId === balance.member_id && breakdownFor(balance.member_id, balance.net_balance).length > 0"
          class="breakdown-panel"
        >
          <div class="breakdown-panel__title">
            {{ balance.net_balance > 0 ? strings.breakdownOwedByTitle : strings.breakdownOwesToTitle }}
          </div>
          <div class="breakdown-panel__list">
            <div
              v-for="entry in breakdownFor(balance.member_id, balance.net_balance)"
              :key="`${entry.transfer.from_member_id}-${entry.transfer.to_member_id}`"
              class="breakdown-row"
            >
              <Avatar
                :name="memberName(entry.other_member_id)"
                :tone="entry.kind === 'incoming' ? 'accent' : 'brand'"
                :size="28"
              />
              <div class="breakdown-row__body">
                <strong>@{{ memberName(entry.other_member_id) }}</strong>
                <span class="breakdown-row__sub">@{{ balance.member_name }}</span>
              </div>
              <div
                class="breakdown-row__amount num"
                :class="{ 'is-pos': entry.kind === 'incoming', 'is-neg': entry.kind === 'outgoing' }"
              >
                <span class="breakdown-row__amount-sign">{{ entry.kind === 'incoming' ? '+' : '−' }}</span>
                <AmountText
                  :amount="entry.transfer.amount"
                  :language="language"
                  :tone="entry.kind === 'incoming' ? 'success' : 'danger'"
                />
              </div>
              <button
                type="button"
                class="breakdown-row__pay"
                @click="payBreakdownEntry(entry, $event)"
              >
                {{ strings.dashboardSettleUpAction }}
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>
```

- [ ] **Step 3: Replace the entire `<style scoped>` block with the new styles**

Replace the existing `<style scoped>` block (everything between `<style scoped>` and `</style>`) with:

```vue
<style scoped>
.balances-page { padding-top: 2px; }

.balances-head {
  margin-bottom: var(--s-2);
}
.balances-head__sub {
  font-size: var(--t-label);
  color: var(--fg-muted);
  margin-bottom: 2px;
}
.balances-head__title {
  font-size: var(--t-title);
  font-weight: var(--fw-semibold);
  letter-spacing: -0.01em;
}

.suggested-stack {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-2xl);
  overflow: hidden;
}
.suggested-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-4);
  background: transparent;
  border: 0;
  cursor: pointer;
  border-bottom: 1px solid var(--divider);
  text-align: start;
}
.suggested-row:last-of-type { border-bottom: 0; }
.suggested-row:hover { background: var(--hover); }
.suggested-row__arrow {
  color: var(--fg-subtle);
  display: inline-flex;
}
.suggested-row__meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.suggested-row__meta strong {
  font-size: var(--t-label);
  font-weight: var(--fw-medium);
}
.suggested-row__meta .muted {
  font-size: 11px;
  color: var(--fg-subtle);
}
.suggested-row__amount {
  font-weight: var(--fw-semibold);
}

/* Per-member list — single bordered card */
.member-list-eyebrow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  margin-bottom: var(--s-2);
}
.member-list-eyebrow .eyebrow { margin: 0; }
.member-list-eyebrow__hint {
  font-size: 11px;
  color: var(--fg-subtle);
}
.member-list-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  overflow: hidden;
}
.member-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--s-3);
  padding: 14px 16px;
  background: transparent;
  border: 0;
  cursor: pointer;
  text-align: start;
  transition: background var(--d-fast) var(--ease-standard);
}
.member-row + .member-row,
.member-row + .breakdown-panel,
.breakdown-panel + .member-row {
  border-top: 1px solid var(--divider);
}
div.member-row { cursor: default; }
.member-row:hover:not(div) { background: var(--hover); }
.member-row.is-expanded { background: var(--surface-sunk); }
.member-row__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.member-row__body strong {
  font-size: 14px;
  font-weight: var(--fw-medium);
}
.member-row__label {
  font-size: 11px;
  font-weight: var(--fw-medium);
}
.member-row__label.is-pos { color: var(--pos); }
.member-row__label.is-neg { color: var(--neg); }
.member-row__label.is-settled { color: var(--fg-subtle); }
.member-row__amount {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.member-row__amount.is-pos { color: var(--pos); }
.member-row__amount.is-neg { color: var(--neg); }
.member-row__amount.is-settled { color: var(--fg-subtle); font-weight: var(--fw-regular); }
.member-row__amount-sign {
  font-weight: 700;
}
.member-row__chevron {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--surface-sunk);
  color: var(--fg-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--d-fast) var(--ease-standard);
}
.member-row.is-expanded .member-row__chevron,
.member-row__chevron.is-open { transform: rotate(180deg); }

/* Breakdown panel */
.breakdown-panel {
  padding: 0 16px 16px;
  background: var(--surface-sunk);
}
.breakdown-panel__title {
  font-size: 11px;
  color: var(--fg-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding-top: 4px;
  margin-bottom: 10px;
}
.breakdown-panel__list {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  overflow: hidden;
}
.breakdown-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--divider);
}
.breakdown-row:last-child { border-bottom: 0; }
.breakdown-row__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.breakdown-row__body strong {
  font-size: 13px;
  font-weight: var(--fw-medium);
}
.breakdown-row__sub {
  font-size: 11px;
  color: var(--fg-muted);
}
.breakdown-row__amount {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  font-size: 14px;
  font-weight: var(--fw-semibold);
  font-variant-numeric: tabular-nums;
}
.breakdown-row__amount.is-pos { color: var(--pos); }
.breakdown-row__amount.is-neg { color: var(--neg); }
.breakdown-row__amount-sign { font-weight: 600; }
.breakdown-row__pay {
  padding: 5px 10px;
  font-size: 11px;
  font-weight: 600;
  background: var(--brand-soft);
  color: var(--brand);
  border: 0;
  border-radius: var(--r-pill);
  cursor: pointer;
}
.breakdown-row__pay:hover { background: color-mix(in srgb, var(--brand-soft) 70%, var(--brand) 30%); }
</style>
```

- [ ] **Step 4: Verify type-check + build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds with no errors. If `computed` is reported as unused, remove it from the import line (`import { onMounted, ref } from 'vue'`).

- [ ] **Step 5: Run the test suite to confirm no regressions**

```bash
cd web-new-version && npm test
```

Expected: all existing tests pass plus the four new `projectMemberBreakdown` tests from Task 1.

- [ ] **Step 6: Manual verification (dev server)**

```bash
cd web-new-version && npm run dev
```

Open the app, navigate to a group with at least 3 members and 2+ expenses, then go to Balances. Verify in **fa** (RTL) mode:

  1. No "حالت پرداخت بهینه" toggle anywhere on the page.
  2. No brand chip in the top bar.
  3. Suggested-payment rows show: `[from-avatar] → [to-avatar] @from / → @to · amount` — the inter-avatar arrow and the meta arrow both point in the same direction (visually `←` because of `scaleX(-1)`).
  4. Per-member list is one bordered card.
  5. Each non-settled member row has a chevron-down on the inline-end side.
  6. Tapping a creditor row expands a panel labeled "طلبکار از این افراد" with each debtor + a green `+amount` + a "پرداخت" pill.
  7. Tapping a debtor row expands "بدهکار به این افراد" with each creditor + red `−amount` + "پرداخت" pill.
  8. Tapping a settled row does nothing (no chevron, not interactive).
  9. Tapping "پرداخت" inside a breakdown navigates to the settlement editor pre-filled with from/to/amount.
  10. Tapping the same row again collapses the panel.
  11. Tapping a different row collapses the previous and expands the new one.

Then switch language to **en** and verify items 1–11 still hold (arrow visually points `→`).

Stop the dev server with Ctrl-C.

- [ ] **Step 7: Commit**

```bash
git add web-new-version/src/modules/balances/pages/BalancesPage.vue
git commit -m "feat(balances): add expandable per-member breakdown matching swiply design"
```

---

## Task 7: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

```bash
cd web-new-version && npm test
```

Expected: all tests pass. No new failures vs. baseline. The four new `projectMemberBreakdown` tests are green.

- [ ] **Step 2: Run a clean build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds. No TypeScript errors. No unused-import warnings on `BalancesPage.vue` or `SuggestedPaymentCard.vue`.

- [ ] **Step 3: Inspect git log**

```bash
git log --oneline -8
```

Expected: **6 new commits** on top of the previous head — one each from Tasks 1, 2, 3, 4, 5, 6. If you see fewer, a step's commit was skipped; investigate before continuing.

- [ ] **Step 4: Spot-check the diff of `BalancesPage.vue`**

```bash
git diff <commit-before-task-4>..HEAD -- web-new-version/src/modules/balances/pages/BalancesPage.vue
```

Confirm:
- No remaining references to `simplify`, `switch-field`, or `chip--brand` in this file.
- No remaining `<template v-if="isRtl">` SVG branches in this file.
- `projectMemberBreakdown` is imported and used.
- New `<style scoped>` rules for `.member-list-card`, `.member-row`, `.breakdown-panel` are present.

- [ ] **Step 5: Confirm `SuggestedPaymentCard.vue` is clean**

```bash
grep -n "isRtl\|v-if=\"isRtl" web-new-version/src/shared/components/SuggestedPaymentCard.vue
```

Expected: no matches.

- [ ] **Step 6: Done — no commit needed**

This task only verifies. If everything passes, the redesign is complete. If anything failed, return to the relevant earlier task and address.
