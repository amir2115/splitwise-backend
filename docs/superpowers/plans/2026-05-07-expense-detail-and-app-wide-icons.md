# Expense Detail Rework + App-Wide Icon System Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `ExpenseDetailPage.vue` to match the Swiply Redesign, introduce a shared `<Icon>` component with all 33 design icons, and sweep every emoji icon (5 sites) and inline `<svg>` icon (~91 sites across 22 files) across the app to use the new component.

**Architecture:** Build `<Icon>` first, then make `EmptyStateCard`/`HeroCard` icon-name-aware so they render `<Icon>` for known names while still accepting text fallbacks. Rebuild `ExpenseDetailPage` against the new design using `<Icon>` for its top-bar buttons. Then sweep the rest of the app: emoji glyphs first (small) and inline-SVG icons after (per-file audit using the spec's shape→name mapping table).

**Tech Stack:** Vue 3 SFC, Vitest + @vue/test-utils, TypeScript. Working directory: `/Users/amir/PycharmProjects/offline-splitwise/web-new-version`.

**Spec:** `docs/superpowers/specs/2026-05-07-expense-detail-and-app-wide-icons-design.md`

---

## File Map

All paths relative to repo root.

| File | Type | Change |
|---|---|---|
| `web-new-version/src/shared/components/Icon.vue` | **create** | New component with all 33 design icons + named `IconName` type |
| `web-new-version/tests/icon.test.ts` | **create** | Unit tests verifying SVG render |
| `web-new-version/src/shared/i18n/strings.ts` | modify | Add 5 new keys |
| `web-new-version/src/shared/components/EmptyStateCard.vue` | modify | Render `<Icon>` when prop matches a known icon name |
| `web-new-version/src/shared/components/HeroCard.vue` | modify | Same icon-name handling |
| `web-new-version/src/modules/expenses/pages/ExpenseDetailPage.vue` | modify | Full rewrite |
| `web-new-version/src/shared/components/BaseModal.vue` | modify | `✕` → `<Icon name="close">` |
| `web-new-version/src/shared/components/CalculatorAmountInput.vue` | modify | `✕` → `<Icon name="close">` (keep animated SVGs as-is) |
| 22 SVG-sweep files (Task 6) | modify | Inline-SVG audit + replace with `<Icon>` |

---

## Task 1: Add 5 new i18n strings

**Files:**
- Modify: `web-new-version/src/shared/i18n/strings.ts`

- [ ] **Step 1: Add the 5 keys to the `AppStrings` interface**

In the file, find this existing line:

```ts
  settlementSuggestedAmountHint: string
```

Add 5 new lines immediately after it (before the next existing key):

```ts
  settlementSuggestedAmountHint: string
  expenseSummaryPill: string
  expenseGetsBackLabel: string
  expenseOwesLabel: string
  expenseShareLabel: string
  expensePaidLabel: string
```

- [ ] **Step 2: Add Persian (`fa`) values**

Find:

```ts
  settlementSuggestedAmountHint: 'مبلغ پیشنهادی از مانده‌های فعلی',
```

Add 5 new lines after it:

```ts
  settlementSuggestedAmountHint: 'مبلغ پیشنهادی از مانده‌های فعلی',
  expenseSummaryPill: 'خلاصه خرج',
  expenseGetsBackLabel: 'پس‌گرفت',
  expenseOwesLabel: 'بدهی',
  expenseShareLabel: 'سهم',
  expensePaidLabel: 'پرداخت',
```

- [ ] **Step 3: Add English (`en`) values**

Find:

```ts
  settlementSuggestedAmountHint: 'Suggested from current balances',
```

Add 5 new lines after it:

```ts
  settlementSuggestedAmountHint: 'Suggested from current balances',
  expenseSummaryPill: 'Expense summary',
  expenseGetsBackLabel: 'Gets back',
  expenseOwesLabel: 'Owes',
  expenseShareLabel: 'Share',
  expensePaidLabel: 'Paid',
```

- [ ] **Step 4: Build verify**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add src/shared/i18n/strings.ts
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "feat(i18n): add expense-detail rework strings"
```

---

## Task 2: Build `<Icon>` component (TDD)

**Files:**
- Create: `web-new-version/src/shared/components/Icon.vue`
- Create: `web-new-version/tests/icon.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `web-new-version/tests/icon.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import Icon from '@/shared/components/Icon.vue'

describe('Icon', () => {
  it('renders an <svg> for a known name with default size 18', () => {
    const wrapper = mount(Icon, { props: { name: 'edit' as const } })
    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('width')).toBe('18')
    expect(svg.attributes('height')).toBe('18')
    expect(svg.attributes('viewBox')).toBe('0 0 24 24')
    expect(svg.find('path').exists()).toBe(true)
  })

  it('respects the size prop', () => {
    const wrapper = mount(Icon, { props: { name: 'trash' as const, size: 24 } })
    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBe('24')
    expect(svg.attributes('height')).toBe('24')
  })

  it('renders distinct paths for distinct names', () => {
    const editPath = mount(Icon, { props: { name: 'edit' as const } }).find('path').attributes('d')
    const trashPath = mount(Icon, { props: { name: 'trash' as const } }).find('path').attributes('d')
    expect(editPath).toBeTruthy()
    expect(trashPath).toBeTruthy()
    expect(editPath).not.toBe(trashPath)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- icon
```

Expected: tests fail with module-resolution error pointing at the missing `@/shared/components/Icon.vue`.

- [ ] **Step 3: Create the Icon component**

Create `web-new-version/src/shared/components/Icon.vue` with this complete content:

```vue
<script setup lang="ts">
export type IconName =
  | 'plus' | 'arrow-right' | 'arrow-left'
  | 'chevron-right' | 'chevron-left' | 'chevron-down'
  | 'close' | 'check' | 'search'
  | 'users' | 'wallet' | 'scale'
  | 'settings' | 'home' | 'swap'
  | 'card' | 'copy' | 'edit' | 'trash'
  | 'dot' | 'eye' | 'download' | 'sparkle'
  | 'wifi' | 'phone' | 'moon' | 'sun'
  | 'lock' | 'mail' | 'shield'
  | 'user-plus' | 'message' | 'refresh'

withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 18 })
</script>

<template>
  <svg
    viewBox="0 0 24 24"
    :width="size"
    :height="size"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'plus'"><path d="M12 5v14M5 12h14" /></template>
    <template v-else-if="name === 'arrow-right'"><path d="M5 12h14M13 6l6 6-6 6" /></template>
    <template v-else-if="name === 'arrow-left'"><path d="M19 12H5M11 18l-6-6 6-6" /></template>
    <template v-else-if="name === 'chevron-right'"><path d="M9 6l6 6-6 6" /></template>
    <template v-else-if="name === 'chevron-left'"><path d="M15 6l-6 6 6 6" /></template>
    <template v-else-if="name === 'chevron-down'"><path d="M6 9l6 6 6-6" /></template>
    <template v-else-if="name === 'close'"><path d="M6 6l12 12M18 6l-12 12" /></template>
    <template v-else-if="name === 'check'"><path d="M5 12.5l4.5 4.5L19 7.5" /></template>
    <template v-else-if="name === 'search'"><circle cx="11" cy="11" r="6" /><path d="M20 20l-4-4" /></template>
    <template v-else-if="name === 'users'"><circle cx="9" cy="8" r="3.5" /><path d="M3 20c0-3 2.5-5 6-5s6 2 6 5M16 10.5a3 3 0 1 0 0-6M21 20c0-2.4-1.6-4.4-4-4.9" /></template>
    <template v-else-if="name === 'wallet'"><path d="M4 7c0-1.7 1.3-3 3-3h10a3 3 0 0 1 3 3M4 7v10a3 3 0 0 0 3 3h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2H4" /><circle cx="17" cy="13" r="1.25" /></template>
    <template v-else-if="name === 'scale'"><path d="M12 4v16M6 20h12M5 10l2.5-5L10 10M14 10l2.5-5L19 10" /><path d="M4 10h7M13 10h7M4 10c0 2 1.3 3.5 3.5 3.5S11 12 11 10M13 10c0 2 1.3 3.5 3.5 3.5S20 12 20 10" /></template>
    <template v-else-if="name === 'settings'"><circle cx="12" cy="12" r="3" /><path d="M19.4 14.6a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V20a2 2 0 0 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H4a2 2 0 0 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H10a1.6 1.6 0 0 0 1-1.5V4a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V10a1.6 1.6 0 0 0 1.5 1H20a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z" /></template>
    <template v-else-if="name === 'home'"><path d="M4 11l8-7 8 7v8a2 2 0 0 1-2 2h-4v-6h-4v6H6a2 2 0 0 1-2-2z" /></template>
    <template v-else-if="name === 'swap'"><path d="M7 7h13M17 4l3 3-3 3M17 17H4M7 14l-3 3 3 3" /></template>
    <template v-else-if="name === 'card'"><rect x="3" y="6" width="18" height="13" rx="2.5" /><path d="M3 10h18M7 15h4" /></template>
    <template v-else-if="name === 'copy'"><rect x="9" y="9" width="11" height="11" rx="2.5" /><path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" /></template>
    <template v-else-if="name === 'edit'"><path d="M4 20h4l10-10-4-4L4 16zM14 6l4 4" /></template>
    <template v-else-if="name === 'trash'"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" /></template>
    <template v-else-if="name === 'dot'"><circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" /></template>
    <template v-else-if="name === 'eye'"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></template>
    <template v-else-if="name === 'download'"><path d="M12 4v12M7 11l5 5 5-5M4 20h16" /></template>
    <template v-else-if="name === 'sparkle'"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6" /></template>
    <template v-else-if="name === 'wifi'"><path d="M3 9a14 14 0 0 1 18 0M6 13a9 9 0 0 1 12 0M9 17a4 4 0 0 1 6 0" /><circle cx="12" cy="20" r="1" fill="currentColor" stroke="none" /></template>
    <template v-else-if="name === 'phone'"><rect x="7" y="3" width="10" height="18" rx="2.5" /><path d="M10 18h4" /></template>
    <template v-else-if="name === 'moon'"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" /></template>
    <template v-else-if="name === 'sun'"><circle cx="12" cy="12" r="4" /><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4" /></template>
    <template v-else-if="name === 'lock'"><rect x="4.5" y="10" width="15" height="11" rx="2.5" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></template>
    <template v-else-if="name === 'mail'"><rect x="3" y="5" width="18" height="14" rx="2.5" /><path d="M3 7l9 7 9-7" /></template>
    <template v-else-if="name === 'shield'"><path d="M12 3l8 3v6c0 4.5-3.3 8.5-8 9-4.7-.5-8-4.5-8-9V6z" /><path d="M9 12.5l2 2 4-4" /></template>
    <template v-else-if="name === 'user-plus'"><circle cx="9" cy="8" r="3.5" /><path d="M3 20c0-3 2.5-5 6-5s6 2 6 5M18 9v6M15 12h6" /></template>
    <template v-else-if="name === 'message'"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H10l-4 4v-4H6a2 2 0 0 1-2-2z" /></template>
    <template v-else-if="name === 'refresh'"><path d="M4 12a8 8 0 0 1 13.7-5.7L20 9M20 4v5h-5M20 12a8 8 0 0 1-13.7 5.7L4 15M4 20v-5h5" /></template>
  </svg>
</template>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- icon
```

Expected: 3/3 pass.

- [ ] **Step 5: Build verify**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
```

Expected: clean build.

- [ ] **Step 6: Commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add src/shared/components/Icon.vue tests/icon.test.ts
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "feat(shared): add Icon component with 33 design icons"
```

---

## Task 3: Make `EmptyStateCard` and `HeroCard` icon-name-aware

**Files:**
- Modify: `web-new-version/src/shared/components/EmptyStateCard.vue`
- Modify: `web-new-version/src/shared/components/HeroCard.vue`

For each of these two components, the existing `icon` prop is a string (currently used to pass single-character glyphs like `'✓'` or `'◧'`). We make them render an `<Icon name="...">` when the value matches a known `IconName`, else render the prop as text (legacy fallback).

- [ ] **Step 1: Inspect both files first**

Run:

```bash
grep -n "icon" /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/shared/components/EmptyStateCard.vue | head -10
grep -n "icon" /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src/shared/components/HeroCard.vue | head -10
```

Note where the `icon` prop is rendered in each file's template. The implementation may vary; the strategy is the same.

- [ ] **Step 2: Update `EmptyStateCard.vue`**

In `web-new-version/src/shared/components/EmptyStateCard.vue`:

1. Add `import Icon, { type IconName } from '@/shared/components/Icon.vue'` to the script.
2. Add a small computed `isKnownIcon` that returns true when the `icon` prop is in the list of valid `IconName` values. Use a runtime list since TypeScript can't reflect:

```ts
const KNOWN_ICONS: readonly string[] = [
  'plus','arrow-right','arrow-left','chevron-right','chevron-left','chevron-down',
  'close','check','search','users','wallet','scale','settings','home','swap',
  'card','copy','edit','trash','dot','eye','download','sparkle','wifi','phone',
  'moon','sun','lock','mail','shield','user-plus','message','refresh',
]
const isKnownIcon = computed(() => typeof props.icon === 'string' && KNOWN_ICONS.includes(props.icon))
```

3. In the template where the `icon` is rendered, replace the bare text rendering with a conditional:

```vue
<Icon v-if="isKnownIcon" :name="(icon as IconName)" :size="22" />
<span v-else-if="icon">{{ icon }}</span>
```

(Adjust `:size` to match the existing visual size; `22` is a placeholder — pick a size that visually matches the previous emoji sizing in the component's CSS.)

- [ ] **Step 3: Update `HeroCard.vue`**

Apply the same pattern to `web-new-version/src/shared/components/HeroCard.vue`:

1. Add `import Icon, { type IconName } from '@/shared/components/Icon.vue'`.
2. Add the same `KNOWN_ICONS` list + `isKnownIcon` computed.
3. Replace the bare-text icon rendering with the same `<Icon v-if="isKnownIcon">` / `<span v-else>` conditional.

(If both files share the same `KNOWN_ICONS` list verbatim, that's a small repetition we can consolidate later. Out of scope for this task — DRY can wait until a third consumer exists.)

- [ ] **Step 4: Build verify**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
```

Expected: clean build. Existing consumers of `EmptyStateCard` and `HeroCard` still work — their string-glyph icons (`'✓'`, `'◧'`, etc.) are not in `KNOWN_ICONS` so they fall through to the text branch.

- [ ] **Step 5: Run tests**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- icon group-balances username-handle
```

Expected: 3 + 5 + 4 = 12 pass. (No new tests added in this task — the component changes are presentational with a fallback.)

- [ ] **Step 6: Commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add src/shared/components/EmptyStateCard.vue src/shared/components/HeroCard.vue
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "feat(shared): EmptyStateCard and HeroCard render Icon for known names"
```

---

## Task 4: Rebuild `ExpenseDetailPage.vue`

**Files:**
- Modify: `web-new-version/src/modules/expenses/pages/ExpenseDetailPage.vue`

Full rewrite of all three SFC blocks. The new file uses the `<Icon>` component (from Task 2) for the top-bar edit/trash buttons.

- [ ] **Step 1: Replace the `<script setup>` block**

In `web-new-version/src/modules/expenses/pages/ExpenseDetailPage.vue`, replace the entire `<script setup lang="ts">` … `</script>` block with:

```vue
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import PageTopBar from '@/shared/components/PageTopBar.vue'
import AmountText from '@/shared/components/AmountText.vue'
import Avatar from '@/shared/components/Avatar.vue'
import Icon from '@/shared/components/Icon.vue'
import UsernameHandle from '@/shared/components/UsernameHandle.vue'
import { useMembersStore } from '@/modules/members/store'
import { useExpensesStore } from '@/modules/expenses/store'
import { useSettingsStore } from '@/shared/stores/settings'
import { useSnackbarStore } from '@/shared/stores/snackbar'
import { formatDate } from '@/shared/utils/format'

const route = useRoute()
const router = useRouter()
const groupId = route.params.groupId as string
const expenseId = route.params.expenseId as string

const membersStore = useMembersStore()
const expensesStore = useExpensesStore()
const settingsStore = useSettingsStore()
const snackbarStore = useSnackbarStore()

const { strings, language } = storeToRefs(settingsStore)
const { byGroupId: membersByGroupId } = storeToRefs(membersStore)
const { byGroupId: expensesByGroupId } = storeToRefs(expensesStore)

const members = computed(() => membersByGroupId.value[groupId] ?? [])
const expense = computed(() => (expensesByGroupId.value[groupId] ?? []).find((item) => item.id === expenseId))

const memberName = (memberId: string) => members.value.find((item) => item.id === memberId)?.username ?? `${strings.value.membersLabel} ${memberId}`

const splitMethodLabel = computed(() => {
  if (!expense.value) return ''
  return expense.value.split_type === 'EQUAL' ? strings.value.equalSplitLabel : strings.value.exactSplitLabel
})

const dateLabel = computed(() => expense.value ? formatDate(expense.value.created_at, language.value) : '')

const participantRows = computed(() => {
  if (!expense.value) return []
  const orderedIds = [
    ...new Set([
      ...expense.value.shares.map((share) => share.member_id),
      ...expense.value.payers.map((payer) => payer.member_id),
    ]),
  ]
  const rows = orderedIds.map((memberId) => {
    const paid = expense.value?.payers.find((payer) => payer.member_id === memberId)?.amount ?? 0
    const owed = expense.value?.shares.find((share) => share.member_id === memberId)?.amount ?? 0
    const net = paid - owed
    return {
      memberId,
      name: memberName(memberId),
      paid,
      owed,
      net,
      netAbsolute: Math.abs(net),
    }
  })
  return rows.sort((a, b) => b.net - a.net)
})

onMounted(async () => {
  try {
    await Promise.all([membersStore.load(groupId), expensesStore.load(groupId)])
  } catch (error) {
    snackbarStore.push(error instanceof Error ? error.message : strings.value.genericError, 'error')
  }
})

async function removeExpense() {
  if (!expense.value || !window.confirm(strings.value.confirmDelete)) return
  try {
    await expensesStore.remove(expense.value)
    router.back()
  } catch (error) {
    snackbarStore.push(error instanceof Error ? error.message : strings.value.genericError, 'error')
  }
}
</script>
```

(Notes: removes `HeroCard`, `SectionHeader` imports — no longer used. Adds `Icon`, `UsernameHandle`. Sorts participants by `net` descending. Removes `overviewItems`/`initial` since those are no longer needed.)

- [ ] **Step 2: Replace the `<template>` block**

Replace the entire `<template>` block with:

```vue
<template>
  <div class="page-shell page-stack expense-detail-page">
    <PageTopBar :title="expense?.title ?? strings.expenseDetailsFallback" can-go-back sticky @back="router.back()">
      <template #actions>
        <button
          v-if="expense"
          class="topbar-icon-button"
          type="button"
          :aria-label="strings.edit"
          @click="router.push(`/groups/${groupId}/expense/${expenseId}/edit`)"
        >
          <Icon name="edit" :size="14" />
        </button>
        <button
          v-if="expense"
          class="topbar-icon-button is-danger"
          type="button"
          :aria-label="strings.delete"
          @click="removeExpense"
        >
          <Icon name="trash" :size="14" />
        </button>
      </template>
    </PageTopBar>

    <template v-if="expense">
      <!-- Hero summary card -->
      <section class="expense-hero">
        <span class="expense-hero__pill">{{ strings.expenseSummaryPill }}</span>
        <div class="expense-hero__amount-row">
          <span class="expense-hero__amount num">{{ expense.total_amount.toLocaleString(language === 'fa' ? 'fa-IR' : 'en-US') }}</span>
          <span class="expense-hero__currency">{{ language === 'fa' ? 'تومان' : 'T' }}</span>
        </div>
        <p v-if="expense.note" class="expense-hero__note">{{ expense.note }}</p>
        <div class="expense-hero__meta">
          <div class="expense-hero__meta-cell">
            <div class="expense-hero__meta-label">{{ strings.splitMethodStat }}</div>
            <div class="expense-hero__meta-value">{{ splitMethodLabel }}</div>
          </div>
          <div class="expense-hero__meta-cell">
            <div class="expense-hero__meta-label">{{ strings.dateStat }}</div>
            <div class="expense-hero__meta-value">{{ dateLabel }}</div>
          </div>
        </div>
      </section>

      <h3 class="eyebrow expense-detail-page__eyebrow">{{ strings.membersAndPayersTitle }}</h3>

      <section class="participant-card-list">
        <article
          v-for="row in participantRows"
          :key="row.memberId"
          class="participant-card"
        >
          <header class="participant-card__header">
            <Avatar :name="row.name" :size="36" :tone="row.net > 0 ? 'brand' : row.net < 0 ? 'accent' : 'settled'" />
            <div class="participant-card__meta">
              <strong class="participant-card__name"><UsernameHandle :username="row.name" /></strong>
              <span
                class="participant-card__role"
                :class="{
                  'is-credit': row.net > 0,
                  'is-debit': row.net < 0,
                  'is-settled': row.net === 0,
                }"
              >
                {{ row.net > 0 ? strings.expenseGetsBackLabel : (row.net < 0 ? strings.expenseOwesLabel : strings.settledLabel) }}
              </span>
            </div>
            <span
              v-if="row.net !== 0"
              class="participant-card__net num"
              :class="{ 'is-credit': row.net > 0, 'is-debit': row.net < 0 }"
            >
              <span class="participant-card__net-sign">{{ row.net > 0 ? '+' : '−' }}</span>
              <AmountText :amount="row.netAbsolute" :language="language" :tone="row.net > 0 ? 'success' : 'danger'" />
            </span>
          </header>
          <div class="participant-card__stats">
            <div class="participant-stat">
              <div class="participant-stat__label">{{ strings.expenseShareLabel }}</div>
              <AmountText :amount="row.owed" :language="language" />
            </div>
            <div class="participant-stat" :class="{ 'is-paid': row.paid > 0 }">
              <div class="participant-stat__label">{{ strings.expensePaidLabel }}</div>
              <AmountText :amount="row.paid" :language="language" :tone="row.paid > 0 ? 'primary' : 'default'" />
            </div>
          </div>
        </article>
      </section>
    </template>

    <div v-else class="surface-card empty-card">{{ strings.expenseNotFound }}</div>
  </div>
</template>
```

- [ ] **Step 3: Replace the `<style scoped>` block**

Replace the entire `<style scoped>` block with:

```vue
<style scoped>
.expense-detail-page { padding-top: 2px; }
.expense-detail-page__eyebrow { margin-top: var(--s-2); }

/* Top-bar icon buttons */
.topbar-icon-button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background var(--d-fast) var(--ease-standard), color var(--d-fast) var(--ease-standard);
}
.topbar-icon-button:hover { background: var(--hover); color: var(--fg); }
.topbar-icon-button.is-danger { color: var(--neg); }
.topbar-icon-button.is-danger:hover { color: var(--neg); background: var(--neg-soft); }

/* Hero summary card */
.expense-hero {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  padding: 20px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.expense-hero__pill {
  display: inline-block;
  align-self: flex-start;
  font-size: 11px;
  font-weight: var(--fw-semibold);
  color: var(--brand);
  background: var(--brand-soft);
  padding: 4px 10px;
  border-radius: var(--r-pill);
}
.expense-hero__amount-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.expense-hero__amount {
  font-size: 44px;
  font-weight: var(--fw-bold);
  color: var(--fg);
  letter-spacing: -0.03em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.expense-hero__currency {
  font-size: 16px;
  color: var(--fg-muted);
  font-weight: var(--fw-medium);
}
.expense-hero__note {
  margin: 0;
  font-size: 13px;
  color: var(--fg-muted);
  line-height: 1.5;
  white-space: pre-wrap;
}
.expense-hero__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.expense-hero__meta-label {
  font-size: 11px;
  color: var(--fg-subtle);
  margin-bottom: 4px;
}
.expense-hero__meta-value {
  font-size: 14px;
  font-weight: var(--fw-semibold);
}

/* Participant cards */
.participant-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.participant-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.participant-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.participant-card__meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.participant-card__name {
  font-size: 14px;
  font-weight: var(--fw-semibold);
}
.participant-card__role {
  font-size: 12px;
  font-weight: var(--fw-medium);
}
.participant-card__role.is-credit { color: var(--pos); }
.participant-card__role.is-debit { color: var(--neg); }
.participant-card__role.is-settled { color: var(--fg-subtle); }
.participant-card__net {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 14px;
  font-weight: var(--fw-bold);
  padding: 5px 10px;
  border-radius: var(--r-pill);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.participant-card__net.is-credit { background: var(--pos-soft); color: var(--pos); }
.participant-card__net.is-debit { background: var(--neg-soft); color: var(--neg); }
.participant-card__net-sign { font-weight: var(--fw-bold); }

.participant-card__stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.participant-stat {
  padding: 10px 12px;
  border-radius: var(--r-sm);
  background: var(--surface-sunk);
  border: 1px solid var(--divider);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.participant-stat.is-paid {
  background: var(--brand-soft);
  border-color: transparent;
}
.participant-stat__label {
  font-size: 10px;
  font-weight: var(--fw-semibold);
  color: var(--fg-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.participant-stat.is-paid .participant-stat__label { color: var(--brand); }
.participant-stat.is-paid :deep(.amount-text) { color: var(--brand); }
</style>
```

- [ ] **Step 4: Build verify**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
```

Expected: clean build.

- [ ] **Step 5: Run tests**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- icon group-balances username-handle
```

Expected: 12/12 pass.

- [ ] **Step 6: Commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add src/modules/expenses/pages/ExpenseDetailPage.vue
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "refactor(expenses): rebuild expense detail to match swiply design"
```

Stage ONLY this one file. Do not use `git add .` — the inner `web-new-version/` repo has unrelated working-tree drift.

---

## Task 5: Replace `✕` emoji icons in BaseModal and CalculatorAmountInput

**Files:**
- Modify: `web-new-version/src/shared/components/BaseModal.vue`
- Modify: `web-new-version/src/shared/components/CalculatorAmountInput.vue`

Both files use the bare `✕` character as a close-button glyph. Replace with `<Icon name="close" :size="14" />`.

- [ ] **Step 1: BaseModal.vue close button**

In `web-new-version/src/shared/components/BaseModal.vue`:

1. Add `import Icon from '@/shared/components/Icon.vue'` to the existing imports (script setup block at the top).
2. Find the close button line (around line 16):

```vue
<button v-if="dismissible !== false" class="icon-button modal-card__close" type="button" @click="emit('close')">✕</button>
```

Replace with:

```vue
<button v-if="dismissible !== false" class="icon-button modal-card__close" type="button" @click="emit('close')">
  <Icon name="close" :size="14" />
</button>
```

- [ ] **Step 2: CalculatorAmountInput.vue close button**

In `web-new-version/src/shared/components/CalculatorAmountInput.vue`:

1. Add `import Icon from '@/shared/components/Icon.vue'` to the existing imports.
2. Find the close button line (around line 263):

```vue
<button class="icon-button calculator-sheet__close" type="button" @click="closeCalculator">✕</button>
```

Replace with:

```vue
<button class="icon-button calculator-sheet__close" type="button" @click="closeCalculator">
  <Icon name="close" :size="14" />
</button>
```

(The other inline `<svg>` elements in this file — calculator key icons, animated check, etc. — stay unchanged in this task. Task 6 covers any of those that match a design icon.)

- [ ] **Step 3: Build + test**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- icon group-balances username-handle
```

Expected: clean build, 12/12 tests pass.

- [ ] **Step 4: Commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add src/shared/components/BaseModal.vue src/shared/components/CalculatorAmountInput.vue
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "refactor(shared): replace close emoji glyphs with Icon component"
```

Stage ONLY these two files.

---

## Task 6: App-wide inline-SVG icon sweep

**Files:**
- Modify: 22 Vue files (listed in the spec under "Phase 2 — Inline SVG sweep")

This task is a per-file audit. For each file, the implementer reads the template, identifies every `<svg viewBox="0 0 24 24">...</svg>` block (or similar inline SVG), determines which design icon name matches the shape using the mapping table below, and replaces the SVG with `<Icon name="...">`. Common shapes are listed for reference; if a shape doesn't match any of the 33 design icons, the implementer LEAVES the SVG inline and notes the exception.

### Reference: shape → icon-name mapping

(Match by inspecting the `d` attribute of the inner `<path>`/`<circle>`/`<rect>` elements.)

| Shape (path data hint) | Icon name |
|---|---|
| `M12 5v14M5 12h14` | `plus` |
| `M5 12h14M13 6l6 6-6 6` | `arrow-right` |
| `M19 12H5M11 18l-6-6 6-6` | `arrow-left` |
| `M9 6l6 6-6 6` or `m9 18 6-6-6-6` | `chevron-right` |
| `M15 6l-6 6 6 6` | `chevron-left` |
| `M6 9l6 6 6-6` | `chevron-down` |
| `M6 6l12 12M18 6l-12 12` | `close` |
| `M5 12.5l4.5 4.5L19 7.5` or shorter check | `check` |
| Magnifier circle + handle | `search` |
| Cog circle | `settings` |
| Pencil shape | `edit` |
| Trash shape | `trash` |
| Eye outline + pupil | `eye` |
| Lock body + shackle | `lock` |
| Phone rect | `phone` |
| Sparkle radiating lines | `sparkle` |
| Two opposing arrows | `swap` |
| Sun rays | `sun` |
| Moon crescent | `moon` |
| WiFi arcs | `wifi` |
| House outline | `home` |
| Mail envelope | `mail` |
| Shield | `shield` |
| Speech bubble | `message` |
| Circular refresh | `refresh` |
| Single user circle + body | `users` (close enough for single-user shapes) |
| User + plus sign | `user-plus` |
| Card rect with stripe | `card` |
| Download arrow + tray | `download` |

### Per-file procedure (apply to every file in the list below)

For each file:

1. Read the file. Find every inline `<svg viewBox="0 0 24 24">` block.
2. For each SVG, identify the matching icon name from the mapping table.
3. Note the surrounding context (what the SVG is decorating). If a wrapper `<span class="suggested-arrow">` exists for direction-flip CSS, **keep the wrapper** — just swap the inner SVG content for `<Icon name="...">`.
4. If a SVG has direction branches (e.g., `<template v-if="isRtl">arrow-left</template><template v-else>arrow-right</template>`), replace both branches with a single `<Icon :name="isRtl ? 'arrow-left' : 'arrow-right'" :size="..."/>` (preserving the existing direction logic and size).
5. If a SVG doesn't match any icon, **leave it inline** and note in the commit message which file/line was kept inline and why.
6. Pick `:size` to roughly match the existing SVG `width="N"` value (e.g., `width="14"` → `:size="14"`).
7. Pick the `<Icon>` import once per file (add `import Icon from '@/shared/components/Icon.vue'` to the top of `<script setup>`).

### Files to sweep

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

### Steps

- [ ] **Step 1: Audit each file**

For each of the 22 files, read it and apply the per-file procedure above. The total count of inline `<svg>` blocks across these files is ~91. After all replacements, the only inline SVGs remaining should be:
- Animated/decorative SVGs (e.g., loader spinners, success-check animations) that aren't flat icons.
- Shapes that don't match any of the 33 design icons (note the exceptions at commit time).

- [ ] **Step 2: Verify zero icon-shaped SVGs remain**

After all per-file audits, run:

```bash
grep -rln '<svg viewBox="0 0 24 24"' /Users/amir/PycharmProjects/offline-splitwise/web-new-version/src --include="*.vue"
```

Each file in the result list should be one of:
- A file containing animated SVG (e.g., `CalculatorAmountInput.vue` may still have key glyphs / pulse animations).
- A file the implementer explicitly noted as having a leave-inline exception.
- The `Icon.vue` itself (which is now the canonical SVG source).

The implementer should be able to articulate WHY each remaining file still has an inline SVG. Otherwise, treat unaccounted matches as missed sweeps.

- [ ] **Step 3: Build + test**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- icon group-balances username-handle
```

Expected: clean build, 12/12 tests pass.

- [ ] **Step 4: Commit**

Stage all 22 files explicitly by name (do NOT use `git add .` — the inner repo has unrelated working-tree drift):

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add \
  src/app/App.vue \
  src/shared/components/CalculatorAmountInput.vue \
  src/shared/components/TransferFlow.vue \
  src/shared/components/AmountField.vue \
  src/shared/components/SuggestedPaymentCard.vue \
  src/shared/components/PageTopBar.vue \
  src/modules/settings/pages/SettingsPage.vue \
  src/modules/settings/pages/AppDownloadPage.vue \
  src/modules/auth/pages/RegisterPage.vue \
  src/modules/auth/pages/LoginPage.vue \
  src/modules/auth/pages/ChangePasswordPage.vue \
  src/modules/auth/pages/AuthPage.vue \
  src/modules/auth/pages/PhoneVerificationPage.vue \
  src/modules/settlements/pages/SettlementEditorPage.vue \
  src/modules/expenses/pages/ExpenseEditorPage.vue \
  src/modules/groupCards/components/GroupCardsSection.vue \
  src/modules/groups/components/SwipeableGroupRow.vue \
  src/modules/groups/pages/GroupDashboardPage.vue \
  src/modules/groups/pages/GroupsPage.vue \
  src/modules/balances/components/PersonalBalancesSummary.vue \
  src/modules/balances/pages/BalancesPage.vue \
  src/modules/members/pages/MembersPage.vue

git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "refactor: sweep inline SVG icons to use Icon component across the app"
```

(If only some files actually have changes — for instance, no icon-shaped SVGs were found in a file — drop that file from the `git add` list. Only stage what changed.)

---

## Task 7: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Confirm 6 new commits**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version log --oneline -7
```

Expected: top 6 commits are this plan's (Tasks 1–6). The 7th is the prior `ec2d048` (settlement code-review fixes).

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test
```

Expected: all targeted tests pass (`icon`, `group-balances`, `username-handle`). Pre-existing failures (`group-cards-section`, `phone-verification`) inherited from the user's earlier in-flight work remain — these are not from this plan.

- [ ] **Step 3: Manual visual gate (`fa` RTL)**

Run:

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run dev
```

Navigate the app in **fa** mode and verify:

1. **ExpenseDetailPage** — open an expense from the Group Dashboard's "Recent expenses" section.
   - Top bar has two circular icon buttons (edit pencil, trash) with the design's stroke style.
   - Hero card: brand-soft pill ("خلاصه خرج"), big amount (44px), note as a muted subtitle if non-empty, 2-col meta grid.
   - "MEMBERS & PAYERS" eyebrow.
   - Per-member cards in credit-first order: avatar + `@name` + role label (`پس‌گرفت`/`بدهی`/`تسویه` colored) + net pill, with 2-col stat tiles below (`SHARE` + `PAID` — the PAID tile is brand-tinted when paid > 0).
2. **Other pages with replaced icons** — spot-check 4-5 pages for visual regressions:
   - **PageTopBar back arrow** — direction matches RTL (chevron-right/arrow-right with proper LTR/RTL handling).
   - **SettlementEditor swap button** — same swap icon as before.
   - **Settings page** — language/theme toggle icons render.
   - **Login page** — eye icon (show password) renders.
   - **Group Cards section** — copy/edit/trash icons on each card row.

- [ ] **Step 4: Manual visual gate (`en` LTR)**

Switch to **en** and spot-check:
- ExpenseDetailPage same structure but LTR-aligned.
- Direction-aware icons (back arrow, chevrons) flipped correctly.

- [ ] **Step 5: Done — no commit**

If any icon looks wrong in a particular spot, isolate the offending file and either fix the icon name or restore the inline SVG (and add it as a documented exception). Otherwise the rollout is complete.

---

## Out of scope (per spec)

- Icon size variants (`size="sm" | "md" | "lg"`) — the design uses raw numeric sizes; we do the same.
- Animated icons (spinners, success animations) — left inline.
- Storybook / icon-gallery page — could be added later.
- Icons not in the design's 33-icon set — leave inline as exceptions, document them in commit messages.
