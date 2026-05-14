# Settlement Page Swiply Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `web-new-version/src/modules/settlements/pages/SettlementEditorPage.vue` to match the Swiply Redesign Settlement screen — replacing the current chip-picker layout (which has a horizontal-overflow bug on narrow viewports) with a slot-based hero + active searchable picker panel.

**Architecture:** Pure presentational rebuild of one Vue SFC. The `<script setup>` keeps all existing data wiring (stores, form, submit/delete) and gains a small amount of new state (`activeStep`, `searchQuery`) and a few helpers (`filteredMembers`, `recentMembers`, `balanceHintFor`, `selectMember`, `swap`, `focusSlot`). The `<template>` and `<style scoped>` are fully replaced. 13 new i18n keys are added.

**Tech Stack:** Vue 3 SFC `<script setup>` + scoped CSS, Pinia, vue-router, Vitest. Working directory for all commands: `/Users/amir/PycharmProjects/offline-splitwise/web-new-version`.

**Spec:** `docs/superpowers/specs/2026-05-06-settlement-page-swiply-rework-design.md`

---

## File Map

All paths relative to repo root `/Users/amir/PycharmProjects/offline-splitwise/`.

| File | Type | Change |
|---|---|---|
| `web-new-version/src/shared/i18n/strings.ts` | modify | Add 13 new keys to `AppStrings` interface + `fa` + `en` value blocks |
| `web-new-version/src/modules/settlements/pages/SettlementEditorPage.vue` | modify | **Full rewrite** of `<script setup>`, `<template>`, and `<style scoped>` blocks |

No new files created. No files deleted.

---

## Task 1: Add 13 new i18n strings

**Files:**
- Modify: `web-new-version/src/shared/i18n/strings.ts`

The new template references string keys that don't exist yet. Add them first so the page rewrite in Task 2 type-checks immediately.

- [ ] **Step 1: Add the 13 keys to the `AppStrings` interface**

In `web-new-version/src/shared/i18n/strings.ts`, find this existing line in the interface (around line 251):

```ts
  suggestedPaymentsTitle: string
```

Add 13 new lines immediately after it (before whatever comes next):

```ts
  suggestedPaymentsTitle: string
  settlementStep1: string
  settlementStep2: string
  settlementChoosePayer: string
  settlementChooseReceiver: string
  settlementSearchMember: string
  settlementRecentLabel: string
  settlementAllMembersLabel: string
  settlementSwapLabel: string
  settlementTapToPick: string
  settlementMemberOwesLabel: string
  settlementMemberOwedLabel: string
  settlementMemberSettledLabel: string
  settlementSuggestedAmountHint: string
```

- [ ] **Step 2: Add the 13 Persian (`fa`) values**

Find this existing line in the `fa` object (around line 585):

```ts
  suggestedPaymentsTitle: 'پرداخت‌های پیشنهادی',
```

Add 13 new lines immediately after it:

```ts
  suggestedPaymentsTitle: 'پرداخت‌های پیشنهادی',
  settlementStep1: 'مرحله ۱',
  settlementStep2: 'مرحله ۲',
  settlementChoosePayer: 'انتخاب پرداخت‌کننده',
  settlementChooseReceiver: 'انتخاب دریافت‌کننده',
  settlementSearchMember: 'جست‌وجوی عضو',
  settlementRecentLabel: 'آخرین تسویه‌ها',
  settlementAllMembersLabel: 'همه اعضا',
  settlementSwapLabel: 'جابه‌جایی',
  settlementTapToPick: 'انتخاب کن',
  settlementMemberOwesLabel: 'بدهکار',
  settlementMemberOwedLabel: 'طلبکار',
  settlementMemberSettledLabel: 'تسویه',
  settlementSuggestedAmountHint: 'مبلغ پیشنهادی از مانده‌های فعلی',
```

- [ ] **Step 3: Add the 13 English (`en`) values**

Find this existing line in the `en` object (around line 916):

```ts
  suggestedPaymentsTitle: 'Suggested payments',
```

Add 13 new lines immediately after it:

```ts
  suggestedPaymentsTitle: 'Suggested payments',
  settlementStep1: 'Step 1',
  settlementStep2: 'Step 2',
  settlementChoosePayer: 'Choose who paid',
  settlementChooseReceiver: 'Choose who got paid',
  settlementSearchMember: 'Search a member',
  settlementRecentLabel: 'Recently settled with',
  settlementAllMembersLabel: 'All members',
  settlementSwapLabel: 'Swap',
  settlementTapToPick: 'Tap to choose',
  settlementMemberOwesLabel: 'owes',
  settlementMemberOwedLabel: 'is owed',
  settlementMemberSettledLabel: 'settled',
  settlementSuggestedAmountHint: 'Suggested from current balances',
```

- [ ] **Step 4: Type-check**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
```

Expected: build succeeds with no TypeScript errors. The interface and both value blocks must be in sync (no missing keys in either object).

- [ ] **Step 5: Commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add src/shared/i18n/strings.ts
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "feat(i18n): add settlement-rework strings (step indicator, picker, swap)"
```

---

## Task 2: Rewrite SettlementEditorPage.vue

**Files:**
- Modify: `web-new-version/src/modules/settlements/pages/SettlementEditorPage.vue`

This task replaces the entire content of the file. The new file uses the same imports plus relies on the 13 i18n keys added in Task 1.

The rewrite is done by replacing each of the three SFC blocks (`<script setup>`, `<template>`, `<style scoped>`) in turn.

- [ ] **Step 1: Replace the `<script setup>` block**

Open `web-new-version/src/modules/settlements/pages/SettlementEditorPage.vue` and replace the entire existing `<script setup lang="ts">` … `</script>` block (currently lines 1–148) with this new content:

```vue
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import PageTopBar from '@/shared/components/PageTopBar.vue'
import InlineAlert from '@/shared/components/InlineAlert.vue'
import AmountText from '@/shared/components/AmountText.vue'
import Avatar from '@/shared/components/Avatar.vue'
import { useMembersStore } from '@/modules/members/store'
import { useSettlementsStore } from '@/modules/settlements/store'
import { useBalancesStore } from '@/modules/balances/store'
import { useSettingsStore } from '@/shared/stores/settings'
import { useSnackbarStore } from '@/shared/stores/snackbar'
import { digitsOnly, formatAmountInput, parseAmountInput, isAmountOverflow } from '@/shared/utils/format'
import { translateMessageKey } from '@/shared/i18n/strings'
import { resolveAppErrorMessage } from '@/shared/utils/apiErrors'
import UsernameHandle from '@/shared/components/UsernameHandle.vue'

type SlotRole = 'from' | 'to'

const route = useRoute()
const router = useRouter()
const groupId = route.params.groupId as string
const settlementId = route.params.settlementId as string | undefined
const isEdit = computed(() => Boolean(settlementId))

const membersStore = useMembersStore()
const settlementsStore = useSettlementsStore()
const balancesStore = useBalancesStore()
const settingsStore = useSettingsStore()
const snackbarStore = useSnackbarStore()

const { strings, language } = storeToRefs(settingsStore)
const { byGroupId: membersByGroupId } = storeToRefs(membersStore)
const { byGroupId: settlementsByGroupId } = storeToRefs(settlementsStore)

const members = computed(() => membersByGroupId.value[groupId] ?? [])
const settlement = computed(() => (settlementsByGroupId.value[groupId] ?? []).find((item) => item.id === settlementId))
const balanceResponse = computed(() => balancesStore.byGroupId[groupId])
const errorMessage = ref('')
const isSaving = ref(false)
const prefilledSuggestedAmount = computed(() => parseAmountInput(String(route.query.amount ?? '')))

const form = reactive({
  from_member_id: '',
  to_member_id: '',
  amountInput: '',
  note: '',
})

const activeStep = ref<SlotRole>('from')
const searchQuery = ref('')

onMounted(async () => {
  try {
    await Promise.all([membersStore.load(groupId), settlementsStore.load(groupId), balancesStore.load(groupId)])
    if (settlement.value) {
      form.from_member_id = settlement.value.from_member_id
      form.to_member_id = settlement.value.to_member_id
      form.amountInput = String(settlement.value.amount)
      form.note = settlement.value.note ?? ''
      activeStep.value = 'from'
    } else {
      form.from_member_id = String(route.query.from ?? members.value[0]?.id ?? '')
      form.to_member_id = String(route.query.to ?? members.value[1]?.id ?? members.value[0]?.id ?? '')
      form.amountInput = prefilledSuggestedAmount.value > 0 ? String(prefilledSuggestedAmount.value) : ''
      activeStep.value = route.query.to ? 'to' : 'from'
    }
  } catch (error) {
    snackbarStore.push(error instanceof Error ? error.message : strings.value.genericError, 'error')
  }
})

const suggestedAmount = computed(() => {
  if (prefilledSuggestedAmount.value > 0 && form.from_member_id === String(route.query.from ?? '') && form.to_member_id === String(route.query.to ?? '')) {
    return prefilledSuggestedAmount.value
  }
  return balanceResponse.value?.simplified_debts.find((item) => item.from_member_id === form.from_member_id && item.to_member_id === form.to_member_id)?.amount ?? 0
})

const fromMember = computed(() => members.value.find((m) => m.id === form.from_member_id))
const toMember = computed(() => members.value.find((m) => m.id === form.to_member_id))
const otherSlotMemberId = computed(() => activeStep.value === 'from' ? form.to_member_id : form.from_member_id)

const filteredMembers = computed(() => {
  const otherSlot = otherSlotMemberId.value
  const query = searchQuery.value.trim().toLowerCase()
  return members.value
    .filter((m) => m.id !== otherSlot)
    .filter((m) => !query || m.username.toLowerCase().includes(query))
})

const recentMembers = computed(() => {
  const otherSlot = otherSlotMemberId.value
  const recents = new Set<string>()
  const settlementsList = settlementsByGroupId.value[groupId] ?? []
  ;[...settlementsList]
    .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
    .forEach((s) => {
      const counterpart = activeStep.value === 'from' ? s.from_member_id : s.to_member_id
      if (!counterpart || counterpart === otherSlot) return
      recents.add(counterpart)
    })
  return Array.from(recents)
    .slice(0, 4)
    .map((id) => members.value.find((m) => m.id === id))
    .filter((m): m is NonNullable<typeof m> => Boolean(m))
})

function balanceHintFor(memberId: string): { kind: 'owes' | 'owed' | 'settled'; amount: number } {
  const balance = balanceResponse.value?.balances.find((b) => b.member_id === memberId)
  if (!balance || balance.net_balance === 0) return { kind: 'settled', amount: 0 }
  if (balance.net_balance > 0) return { kind: 'owed', amount: balance.net_balance }
  return { kind: 'owes', amount: Math.abs(balance.net_balance) }
}

function focusSlot(slot: SlotRole) {
  activeStep.value = slot
  searchQuery.value = ''
}

function selectMember(memberId: string) {
  if (activeStep.value === 'from') {
    form.from_member_id = memberId
    if (form.to_member_id === memberId) form.to_member_id = ''
    if (!form.to_member_id) {
      activeStep.value = 'to'
      searchQuery.value = ''
    }
  } else {
    form.to_member_id = memberId
    if (form.from_member_id === memberId) form.from_member_id = ''
    if (!form.from_member_id) {
      activeStep.value = 'from'
      searchQuery.value = ''
    }
  }
}

function swap() {
  const previousFrom = form.from_member_id
  form.from_member_id = form.to_member_id
  form.to_member_id = previousFrom
}

function fillSuggestedAmount() {
  if (suggestedAmount.value > 0) form.amountInput = String(suggestedAmount.value)
}

async function submit() {
  errorMessage.value = ''
  if (isAmountOverflow(form.amountInput)) {
    errorMessage.value = strings.value.amountTooLarge
    return
  }
  const amount = parseAmountInput(form.amountInput)
  const messageKey =
    !form.from_member_id || !form.to_member_id
      ? 'SETTLEMENT_SELECT_TWO_MEMBERS'
      : form.from_member_id === form.to_member_id
        ? 'SETTLEMENT_MEMBERS_MUST_DIFFER'
        : amount <= 0
          ? 'SETTLEMENT_AMOUNT_POSITIVE'
          : null

  if (messageKey) {
    errorMessage.value = translateMessageKey(language.value, messageKey) ?? strings.value.genericError
    return
  }

  try {
    isSaving.value = true
    await settlementsStore.save({
      existingId: settlementId,
      group_id: groupId,
      from_member_id: form.from_member_id,
      to_member_id: form.to_member_id,
      amount,
      note: form.note.trim() || null,
    })
    snackbarStore.push(translateMessageKey(language.value, 'SETTLEMENT_SAVED') ?? strings.value.saveSettlement)
    router.back()
  } catch (error) {
    errorMessage.value = resolveAppErrorMessage(error, strings.value, language.value)
  } finally {
    isSaving.value = false
  }
}

async function removeSettlement() {
  if (!settlement.value || !window.confirm(strings.value.confirmDelete)) return
  try {
    await settlementsStore.remove(settlement.value)
    router.back()
  } catch (error) {
    snackbarStore.push(error instanceof Error ? error.message : strings.value.genericError, 'error')
  }
}
</script>
```

(Note: the old `isRtl` computed and `selectPayer`/`selectReceiver` helpers are gone — replaced by `selectMember` + `focusSlot` + `swap`. Use `Edit` with the full old `<script setup>` block as `old_string` and the above as `new_string`.)

- [ ] **Step 2: Replace the `<template>` block**

Replace the entire existing `<template>` … `</template>` block (currently lines 150–251) with this new content:

```vue
<template>
  <div class="page-shell page-stack settlement-page">
    <PageTopBar :title="isEdit ? strings.editSettlementTitle : strings.addSettlementTitle" can-go-back sticky @back="router.back()">
      <template #actions>
        <button class="filled-button filled-button--sm" type="button" :disabled="isSaving" @click="submit">
          <span v-if="isSaving" class="button-loader" aria-hidden="true"></span>
          {{ isEdit ? strings.save : strings.saveSettlement }}
        </button>
      </template>
    </PageTopBar>

    <Transition name="feature-transition">
      <InlineAlert v-if="errorMessage" :title="strings.formErrorTitle" :message="errorMessage" />
    </Transition>

    <!-- Step indicator -->
    <div class="settlement-step-indicator">
      <span :class="['settlement-step-indicator__label', { 'is-active': activeStep === 'from' }]">{{ strings.settlementStep1 }}</span>
      <span class="settlement-step-indicator__progress">
        <span class="settlement-step-indicator__progress-fill" :style="{ width: activeStep === 'to' ? '100%' : '50%' }" />
      </span>
      <span :class="['settlement-step-indicator__label', 'settlement-step-indicator__label--accent', { 'is-active': activeStep === 'to' }]">{{ strings.settlementStep2 }}</span>
    </div>

    <!-- Hero with two slots + centered swap -->
    <div class="settlement-hero">
      <div class="settlement-hero__slots">
        <button
          type="button"
          :class="['settlement-slot', 'settlement-slot--from', {
            'is-active': activeStep === 'from',
            'is-empty': !form.from_member_id,
          }]"
          @click="focusSlot('from')"
        >
          <span class="settlement-slot__avatar">
            <Avatar v-if="fromMember" :name="fromMember.username" tone="brand" :size="56" />
            <span v-else class="settlement-slot__avatar-empty" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
            </span>
          </span>
          <span class="settlement-slot__role settlement-slot__role--from">{{ strings.payerLabel }}</span>
          <span class="settlement-slot__name">
            <UsernameHandle v-if="fromMember" :username="fromMember.username" />
            <span v-else class="settlement-slot__name-placeholder">{{ strings.settlementTapToPick }}</span>
          </span>
        </button>
        <button
          type="button"
          :class="['settlement-slot', 'settlement-slot--to', {
            'is-active': activeStep === 'to',
            'is-empty': !form.to_member_id,
          }]"
          @click="focusSlot('to')"
        >
          <span class="settlement-slot__avatar">
            <Avatar v-if="toMember" :name="toMember.username" tone="accent" :size="56" />
            <span v-else class="settlement-slot__avatar-empty" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
            </span>
          </span>
          <span class="settlement-slot__role settlement-slot__role--to">{{ strings.receiverLabel }}</span>
          <span class="settlement-slot__name">
            <UsernameHandle v-if="toMember" :username="toMember.username" />
            <span v-else class="settlement-slot__name-placeholder">{{ strings.settlementTapToPick }}</span>
          </span>
        </button>
      </div>
      <button class="settlement-swap" type="button" :aria-label="strings.settlementSwapLabel" @click="swap">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 16l-4-4 4-4"/>
          <path d="M3 12h18"/>
          <path d="M17 8l4 4-4 4"/>
        </svg>
      </button>
    </div>

    <!-- Active picker -->
    <div class="picker-panel">
      <div class="picker-panel__header">
        <div :class="['picker-panel__role', activeStep === 'from' ? 'picker-panel__role--from' : 'picker-panel__role--to']">
          {{ activeStep === 'from' ? strings.settlementChoosePayer : strings.settlementChooseReceiver }}
        </div>
        <div class="picker-search">
          <svg class="picker-search__icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input v-model="searchQuery" class="picker-search__input" :placeholder="strings.settlementSearchMember" />
          <span class="picker-search__count num">{{ filteredMembers.length }}</span>
        </div>
      </div>

      <div v-if="recentMembers.length > 0" class="picker-recent">
        <div class="picker-section-label">{{ strings.settlementRecentLabel }}</div>
        <div class="picker-recent__row">
          <button
            v-for="member in recentMembers"
            :key="`recent-${member.id}`"
            class="picker-recent__chip"
            type="button"
            @click="selectMember(member.id)"
          >
            <Avatar :name="member.username" :size="32" />
            <span class="picker-recent__chip-name"><UsernameHandle :username="member.username" /></span>
          </button>
        </div>
      </div>

      <div class="picker-list">
        <div class="picker-section-label">{{ strings.settlementAllMembersLabel }}</div>
        <button
          v-for="member in filteredMembers"
          :key="`pick-${member.id}`"
          class="picker-row"
          :class="{ 'is-selected': activeStep === 'from' ? form.from_member_id === member.id : form.to_member_id === member.id }"
          type="button"
          @click="selectMember(member.id)"
        >
          <Avatar :name="member.username" :size="38" />
          <div class="picker-row__body">
            <strong class="picker-row__name"><UsernameHandle :username="member.username" /></strong>
            <span
              class="picker-row__balance"
              :class="{
                'is-pos': balanceHintFor(member.id).kind === 'owed',
                'is-neg': balanceHintFor(member.id).kind === 'owes',
                'is-settled': balanceHintFor(member.id).kind === 'settled',
              }"
            >
              <template v-if="balanceHintFor(member.id).kind === 'settled'">{{ strings.settlementMemberSettledLabel }}</template>
              <template v-else>
                {{ balanceHintFor(member.id).kind === 'owed' ? strings.settlementMemberOwedLabel : strings.settlementMemberOwesLabel }}
                <span class="num">{{ formatAmountInput(String(balanceHintFor(member.id).amount), language) }}</span>
              </template>
            </span>
          </div>
          <span class="picker-row__chevron suggested-arrow" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
          </span>
        </button>
        <div v-if="filteredMembers.length === 0" class="picker-list__empty">{{ strings.noMembersTitle }}</div>
      </div>
    </div>

    <!-- Amount block -->
    <div class="amount-block">
      <span class="amount-block__label">{{ strings.settlementAmountLabel }}</span>
      <div class="amount-block__row">
        <input
          :value="formatAmountInput(form.amountInput, language)"
          class="amount-block__input num"
          inputmode="numeric"
          :placeholder="language === 'fa' ? '۰' : '0'"
          @input="form.amountInput = digitsOnly(($event.target as HTMLInputElement).value)"
        />
        <span class="amount-block__suffix">{{ language === 'fa' ? 'تومان' : 'T' }}</span>
      </div>
      <button v-if="suggestedAmount > 0" type="button" class="amount-block__hint" @click="fillSuggestedAmount">
        <span class="amount-block__hint-dot" aria-hidden="true"></span>
        {{ strings.settlementSuggestedAmountHint }}
        ·
        <AmountText :amount="suggestedAmount" :language="language" tone="primary" />
      </button>
    </div>

    <!-- Note -->
    <div class="form-field">
      <label class="form-field__label">{{ strings.noteLabel }}</label>
      <textarea v-model="form.note" class="text-area" />
    </div>

    <button v-if="isEdit" class="outline-button is-danger" type="button" @click="removeSettlement">
      {{ strings.delete }}
    </button>
  </div>
</template>
```

- [ ] **Step 3: Replace the `<style scoped>` block**

Replace the entire existing `<style scoped>` … `</style>` block (currently lines 253–375) with this new content:

```vue
<style scoped>
.settlement-page { padding-top: 2px; }

/* Step indicator */
.settlement-step-indicator {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  font-size: 11px;
  color: var(--fg-subtle);
}
.settlement-step-indicator__label {
  font-weight: var(--fw-semibold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex-shrink: 0;
}
.settlement-step-indicator__label.is-active { color: var(--brand); }
.settlement-step-indicator__label--accent.is-active { color: var(--accent); }
.settlement-step-indicator__progress {
  flex: 1;
  height: 2px;
  background: var(--brand-soft);
  border-radius: 999px;
  position: relative;
  overflow: hidden;
}
.settlement-step-indicator__progress-fill {
  position: absolute;
  inset-inline-start: 0;
  inset-block-start: 0;
  height: 100%;
  background: var(--brand);
  border-radius: 999px;
  transition: width var(--d-base) var(--ease-standard);
}

/* Hero: two slots + swap button */
.settlement-hero {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  padding: 14px;
  box-shadow: var(--shadow-1);
}
.settlement-hero__slots {
  display: flex;
  align-items: stretch;
  gap: 10px;
  min-width: 0;
}
.settlement-slot {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 8px;
  background: transparent;
  border: 1.5px dashed var(--border-strong);
  border-radius: var(--r-lg);
  cursor: pointer;
  transition: background var(--d-fast) var(--ease-standard), border-color var(--d-fast) var(--ease-standard);
}
.settlement-slot:not(.is-empty) {
  border: 1px solid var(--border);
}
.settlement-slot.is-active.settlement-slot--from {
  background: var(--brand-soft);
  border: 1.5px solid var(--brand);
}
.settlement-slot.is-active.settlement-slot--to {
  background: var(--accent-soft);
  border: 1.5px solid var(--accent);
}
.settlement-slot__avatar {
  width: 56px;
  height: 56px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.settlement-slot__avatar-empty {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--surface-sunk);
  border: 1px dashed var(--border-strong);
  color: var(--fg-subtle);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.settlement-slot__role {
  font-size: 11px;
  font-weight: var(--fw-bold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 4px;
}
.settlement-slot__role--from { color: var(--brand); }
.settlement-slot__role--to { color: var(--accent); }
.settlement-slot__name {
  font-size: 13px;
  font-weight: var(--fw-semibold);
  color: var(--fg);
  text-align: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.settlement-slot.is-empty .settlement-slot__name { color: var(--fg-subtle); }
.settlement-slot__name-placeholder {
  color: var(--fg-subtle);
  font-weight: var(--fw-medium);
}
.settlement-swap {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg-muted);
  box-shadow: var(--shadow-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

/* Picker panel */
.picker-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  overflow: hidden;
}
.picker-panel__header {
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--divider);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.picker-panel__role {
  font-size: 11px;
  font-weight: var(--fw-semibold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.picker-panel__role--from { color: var(--brand); }
.picker-panel__role--to { color: var(--accent); }
.picker-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface-sunk);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  min-width: 0;
}
.picker-search__icon {
  color: var(--fg-subtle);
  flex-shrink: 0;
}
.picker-search__input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: 0;
  outline: none;
  font-size: 14px;
  color: var(--fg);
  text-align: start;
  font-family: inherit;
}
.picker-search__input::placeholder { color: var(--fg-subtle); }
.picker-search__count {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--surface);
  color: var(--fg-subtle);
  border: 1px solid var(--border);
  font-family: var(--font-en);
  flex-shrink: 0;
}

.picker-recent {
  padding: 10px 16px;
  border-bottom: 1px solid var(--divider);
}
.picker-recent__row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}
.picker-recent__chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: var(--surface-sunk);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  flex-shrink: 0;
  min-width: 64px;
  cursor: pointer;
}
.picker-recent__chip-name {
  font-size: 11px;
  font-weight: var(--fw-medium);
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker-section-label {
  padding: 10px 16px 4px;
  font-size: 10px;
  font-weight: var(--fw-semibold);
  color: var(--fg-subtle);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.picker-list {
  max-height: 320px;
  overflow-y: auto;
}
.picker-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--divider);
  cursor: pointer;
  text-align: start;
  transition: background var(--d-fast) var(--ease-standard);
  min-width: 0;
}
.picker-row:last-child { border-bottom: 0; }
.picker-row:hover { background: var(--hover); }
.picker-row.is-selected { background: var(--brand-soft); }
.picker-row__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.picker-row__name { font-size: 14px; font-weight: var(--fw-semibold); }
.picker-row__balance {
  font-size: 11px;
  font-weight: var(--fw-medium);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.picker-row__balance.is-pos { color: var(--pos); }
.picker-row__balance.is-neg { color: var(--neg); }
.picker-row__balance.is-settled { color: var(--fg-subtle); font-weight: var(--fw-regular); }
.picker-row__chevron {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--surface-sunk);
  color: var(--fg-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.picker-list__empty {
  padding: 20px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--fg-subtle);
}

/* Amount block */
.amount-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.amount-block__label {
  font-size: 12px;
  color: var(--fg-subtle);
}
.amount-block__row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.amount-block__input {
  flex: 1;
  min-width: 0;
  font-size: 32px;
  font-weight: var(--fw-bold);
  letter-spacing: -0.02em;
  color: var(--brand);
  background: transparent;
  border: 0;
  outline: 0;
  padding: 0;
  text-align: start;
  line-height: 1;
}
.amount-block__suffix {
  font-size: 14px;
  font-weight: var(--fw-medium);
  color: var(--fg-muted);
  flex-shrink: 0;
}
.amount-block__hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 0;
  background: transparent;
  border: 0;
  font-size: 11px;
  color: var(--fg-muted);
  cursor: pointer;
  text-align: start;
  align-self: flex-start;
}
.amount-block__hint-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand);
  flex-shrink: 0;
}
</style>
```

- [ ] **Step 4: Type-check + build**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run build
```

Expected: build succeeds with no errors. If you see an error about a missing string key, double-check Task 1's edits all landed in `strings.ts`.

- [ ] **Step 5: Run targeted tests**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm test -- group-balances username-handle
```

Expected: 4 + 5 = 9 pass. (No new tests for this rebuild — manual visual gate is the contract.)

- [ ] **Step 6: Commit**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version add src/modules/settlements/pages/SettlementEditorPage.vue
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version commit -m "refactor(settlement): rebuild settlement editor with slot-based picker (Swiply design)"
```

Stage ONLY `src/modules/settlements/pages/SettlementEditorPage.vue`. Do not use `git add .` — the inner `web-new-version/` repo has unrelated in-flight working-tree drift; staging by file name absorbs that drift only into commits the user has accepted, but no other files should sneak in.

---

## Task 3: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Confirm two new commits**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version log --oneline -3
```

Expected: HEAD is the page rebuild; HEAD~1 is the i18n strings; HEAD~2 is the previous Phase B commit `8a7b3c2`.

- [ ] **Step 2: Diff sanity check**

```bash
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version show --stat HEAD~1
git -C /Users/amir/PycharmProjects/offline-splitwise/web-new-version show --stat HEAD
```

Expected: HEAD~1 touches only `src/shared/i18n/strings.ts`. HEAD touches only `src/modules/settlements/pages/SettlementEditorPage.vue`.

- [ ] **Step 3: Manual visual gate (`fa` RTL)**

Run:

```bash
cd /Users/amir/PycharmProjects/offline-splitwise/web-new-version && npm run dev
```

Open the app, navigate to a group with at least 3 members, and start a new settlement (Add Settlement action). Verify in **fa** (RTL):

1. **No horizontal scroll.** The page fits within the viewport at 360px width. Drag-to-the-side behavior is gone.
2. **Top bar.** Title "ثبت تسویه" + Save button present. Back arrow on the inline-end side.
3. **Step indicator.** "مرحله ۱" on the start side, progress bar in the middle, "مرحله ۲" on the end side. Step 1 is brand-colored when active; Step 2 is accent-colored when active. Progress fill grows from 50% to 100% when you advance to Step 2.
4. **Hero card with two slots.** Left/start slot is the payer (brand color); right/end slot is the receiver (accent color). Empty slots have dashed border + plus icon. Filled slots have solid border + 56px avatar. Active slot has tinted background + 1.5px solid colored border.
5. **Swap button.** A 36px circular button is centered between the two slots (visually overlapping the gap). Clicking it swaps from↔to.
6. **Picker panel.** Below the hero: a card with role label ("انتخاب پرداخت‌کننده" / "انتخاب دریافت‌کننده"), search input with icon and count badge, optional "آخرین تسویه‌ها" row of recent counterparts, and "همه اعضا" vertical list.
7. **Member rows.** Each row shows: 38px avatar, `@username`, balance hint sub-line ("بدهکار 272,000" / "طلبکار 136,000" / "تسویه" with corresponding color), chevron on the inline-end side.
8. **Selecting a member.** Tap a member row → step advances; the slot fills with that member; the picker panel header updates.
9. **Search.** Type a substring → list filters live; count badge updates.
10. **Amount block.** Below the picker: a card with "مبلغ تسویه" label, a 32px-font amount input, "تومان" suffix. If a suggested amount is available, a small hint button below shows a brand dot + "مبلغ پیشنهادی از مانده‌های فعلی" + amount; tapping it fills the input.
11. **Note.** Below the amount: "یادداشت" label + textarea, full width, no overflow.
12. **Save flow.** Tap Save → if validation passes, settlement saves and navigates back. If the form is incomplete, an inline error appears.
13. **Deep link.** Navigate from Balances page via "Pay" pill on a suggested-payment row → editor opens with from/to/amount pre-filled, `activeStep` defaults to `'to'`.

- [ ] **Step 4: Manual visual gate (`en` LTR)**

Switch language to English in Settings, then revisit the page:

1. Layout reads left-to-right. Step indicator "Step 1" on the left, "Step 2" on the right. Slot order from→to reads naturally.
2. All Persian strings are now their English equivalents (Step 1, Step 2, Choose who paid, Choose who got paid, Search a member, Recently settled with, All members, Tap to choose, owes/is owed/settled, Suggested from current balances).
3. Amount input behaves the same; suffix is "T".

- [ ] **Step 5: Done — no commit needed**

This task only verifies. If anything is off, return to Task 2 and address.

---

## Out of scope (mentioned in spec)

- Sticky save bar at the bottom of long forms.
- Picker animations (active step transitions, picker fade in/out).
- Multi-select / split settlements.
- Empty-state illustration when there are no members in the group.
- Migrating other settlement-adjacent surfaces (settlement detail page, settlement history list) to match the redesign.
