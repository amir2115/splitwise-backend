# UsernameHandle Component — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a reusable `<UsernameHandle>` Vue component that renders `@username` with bidi-correct behavior in both RTL (Persian) and LTR (English), then migrate the Balances page (4 sites) so the user can validate the pattern visually before sweeping it across the rest of the app in a follow-up plan.

**Architecture:** A tiny single-prop component built on the HTML `<bdi>` element. `<bdi>` defaults to `dir="auto"`, which uses **first-strong-character detection** — for `@amir2115` the first strong char is `a` (Latin = LTR), so the run is treated as LTR and `@` lands before the name. The `<bdi>` is inline and inherits its block position from the parent, so in an RTL paragraph it sits at the RTL start (right side) — which fixes the leftward-drift regression introduced when we previously put bidi handling on a flex-stretched `<strong>` element.

**Tech Stack:** Vue 3 SFC `<script setup>`, Vitest + `@vue/test-utils` (already a devDependency). Working directory for all commands: `web-new-version/`.

**Spec source:** Brainstorming session immediately preceding this plan; user request: "make a custom view for it and use it for all the app (we can test it first and if it was ok change all of the usage)."

**Phased rollout (per user request):**
- **Phase A — this plan:** Build component + migrate `BalancesPage.vue` (4 sites). Stop and let the user verify visually.
- **Phase B — separate follow-up plan, NOT this one:** Sweep the remaining 22 sites across 8 files (`SettingsPage`, `SettlementEditorPage`, `GroupCardsSection`, `ExpenseEditorPage`, `GroupDashboardPage`, `GroupsPage`, `PersonalBalancesSummary`, `MembersPage`).

---

## File Map

| File | Type | Purpose |
|---|---|---|
| `web-new-version/src/shared/components/UsernameHandle.vue` | **create** | The new component — single root `<bdi>` rendering `@{{ username }}` |
| `web-new-version/tests/username-handle.test.ts` | **create** | Two unit tests verifying the `<bdi>` rendering and prop passthrough |
| `web-new-version/src/modules/balances/pages/BalancesPage.vue` | **modify** | Replace 4 `@{{ ... }}` text-interpolation sites with `<UsernameHandle>`; drop `class="handle"` annotations; add the import |
| `web-new-version/src/shared/theme/app.css` | **modify** | Remove the now-unused `.handle` rule (only Balances was using it; the component supersedes it) |

No backend code changes. No data layer changes. No new tests outside the component itself — existing `tests/group-balances.test.ts` is unaffected.

---

## Task 1: Build `UsernameHandle.vue` (TDD)

**Files:**
- Create: `web-new-version/src/shared/components/UsernameHandle.vue`
- Create: `web-new-version/tests/username-handle.test.ts`

The component is small, but a DOM-presence test gives a clean TDD seam and prevents future refactors from accidentally dropping the `<bdi>` wrapper.

- [ ] **Step 1: Write the failing tests**

Create `web-new-version/tests/username-handle.test.ts` with this content:

```ts
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import UsernameHandle from '@/shared/components/UsernameHandle.vue'

describe('UsernameHandle', () => {
  it('renders @username inside a <bdi> element', () => {
    const wrapper = mount(UsernameHandle, { props: { username: 'amir2115' } })
    const bdi = wrapper.find('bdi')
    expect(bdi.exists()).toBe(true)
    expect(bdi.text()).toBe('@amir2115')
  })

  it('passes special characters through without transformation', () => {
    const wrapper = mount(UsernameHandle, { props: { username: 'foo_bar.baz' } })
    expect(wrapper.find('bdi').text()).toBe('@foo_bar.baz')
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd web-new-version && npm test -- username-handle
```

Expected: both tests fail with a module-resolution error pointing at the missing `@/shared/components/UsernameHandle.vue` file.

- [ ] **Step 3: Create the component**

Create `web-new-version/src/shared/components/UsernameHandle.vue` with this content:

```vue
<script setup lang="ts">
defineProps<{ username: string }>()
</script>

<template>
  <bdi class="username-handle">@{{ username }}</bdi>
</template>

<style scoped>
.username-handle {
  /* <bdi> already implies unicode-bidi: isolate via the user-agent stylesheet,
     plus dir="auto" by default (first-strong direction detection). Repeating
     unicode-bidi: isolate is defensive in case anything overrides it. */
  unicode-bidi: isolate;
  font-variant-numeric: tabular-nums;
}
</style>
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd web-new-version && npm test -- username-handle
```

Expected: both tests pass.

- [ ] **Step 5: Type-check / build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git -C web-new-version add src/shared/components/UsernameHandle.vue tests/username-handle.test.ts
git -C web-new-version commit -m "feat(shared): add UsernameHandle component for bidi-correct @username rendering"
```

---

## Task 2: Migrate the Balances page to use `<UsernameHandle>`

**Files:**
- Modify: `web-new-version/src/modules/balances/pages/BalancesPage.vue`

Four template sites currently use the `@{{ … }}` + `class="handle"` pattern. Each becomes a `<UsernameHandle :username="…" />` inside the same outer wrapper. The `class="handle"` annotations are dropped (the component handles bidi internally).

- [ ] **Step 1: Add the import**

In `web-new-version/src/modules/balances/pages/BalancesPage.vue`, find the existing import block at the top of `<script setup>` and add the new component. The existing imports look like this:

```ts
import EmptyStateCard from '@/shared/components/EmptyStateCard.vue'
import PageTopBar from '@/shared/components/PageTopBar.vue'
import AmountText from '@/shared/components/AmountText.vue'
import Avatar from '@/shared/components/Avatar.vue'
```

Add this line below them (alphabetical placement is fine but not required):

```ts
import UsernameHandle from '@/shared/components/UsernameHandle.vue'
```

- [ ] **Step 2: Replace site #1 — suggested-row "from" name**

Find:

```vue
            <strong class="handle">@{{ memberName(transfer.from_member_id) }}</strong>
```

Replace with:

```vue
            <strong><UsernameHandle :username="memberName(transfer.from_member_id)" /></strong>
```

- [ ] **Step 3: Replace site #2 — suggested-row "to" name (muted sub-line)**

Find:

```vue
            <span class="muted handle">@{{ memberName(transfer.to_member_id) }}</span>
```

Replace with:

```vue
            <span class="muted"><UsernameHandle :username="memberName(transfer.to_member_id)" /></span>
```

- [ ] **Step 4: Replace site #3 — per-member row name**

Find:

```vue
            <strong class="handle">@{{ balance.member_name }}</strong>
```

Replace with:

```vue
            <strong><UsernameHandle :username="balance.member_name" /></strong>
```

- [ ] **Step 5: Replace site #4 — breakdown row name**

Find:

```vue
                <strong class="handle">@{{ memberName(entry.other_member_id) }}</strong>
```

Replace with:

```vue
                <strong><UsernameHandle :username="memberName(entry.other_member_id)" /></strong>
```

- [ ] **Step 6: Verify all four sites replaced and no `class="handle"` remains**

```bash
grep -n 'class="handle"\|class="muted handle"' web-new-version/src/modules/balances/pages/BalancesPage.vue || echo "(clean — no handle classes left)"
grep -n "UsernameHandle" web-new-version/src/modules/balances/pages/BalancesPage.vue
```

Expected:
- First grep prints `(clean — no handle classes left)`
- Second grep prints 5 lines: 1 import line + 4 component usage lines

- [ ] **Step 7: Type-check + build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds.

- [ ] **Step 8: Run the existing balances tests**

```bash
cd web-new-version && npm test -- group-balances username-handle
```

Expected: 5 group-balances tests + 2 username-handle tests = 7 pass.

- [ ] **Step 9: Commit**

```bash
git -C web-new-version add src/modules/balances/pages/BalancesPage.vue
git -C web-new-version commit -m "refactor(balances): use UsernameHandle for all @username rendering on the page"
```

---

## Task 3: Remove the now-unused `.handle` utility

**Files:**
- Modify: `web-new-version/src/shared/theme/app.css`

`.handle` was added in Round 2 specifically for the Balances page; nothing else uses it. With Task 2 complete, the rule is dead code. Phase B (separate plan) won't reintroduce it — it'll use `<UsernameHandle>` directly.

- [ ] **Step 1: Confirm `.handle` truly has no remaining users**

```bash
grep -rn 'class="[^"]*handle[^"]*"' web-new-version/src --include="*.vue" || echo "(no .handle references left in templates)"
```

Expected: `(no .handle references left in templates)`. If any other file still uses `class="handle"`, **stop** and report — Phase B should migrate those first instead of removing the utility now.

- [ ] **Step 2: Delete the rule**

In `web-new-version/src/shared/theme/app.css`, find this block (it sits right after the `.suggested-arrow,.toolbar-arrow` rules and the RTL transform rule):

```css
/* Latin handles like @username — keep `@` before the name regardless of paragraph direction */
.handle {
  unicode-bidi: isolate;
}
```

Delete the comment line AND the rule (the entire 4-line block). The file should flow directly from the RTL `transform: scaleX(-1)` rule into whatever rule comes next.

- [ ] **Step 3: Verify the deletion**

```bash
grep -n "^\.handle" web-new-version/src/shared/theme/app.css || echo "(no .handle rule — clean)"
```

Expected: `(no .handle rule — clean)`.

- [ ] **Step 4: Type-check + build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git -C web-new-version add src/shared/theme/app.css
git -C web-new-version commit -m "chore(theme): remove unused .handle utility (superseded by UsernameHandle component)"
```

---

## Task 4: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Confirm three new commits**

```bash
git -C web-new-version log --oneline -4
```

Expected: top three commits are the ones from Tasks 1, 2, 3 in reverse order. The fourth line is the previous Round 3 commit `1eea4a3`.

- [ ] **Step 2: Run the full project test suite**

```bash
cd web-new-version && npm test
```

Expected: all `group-balances` (5) and `username-handle` (2) tests pass; existing pre-existing failures (`group-cards-section`, `phone-verification`) remain — those are inherited from the user's earlier in-flight work, not from this plan.

- [ ] **Step 3: Manual visual verification (Phase A gate)**

Run:

```bash
cd web-new-version && npm run dev
```

Open the app, navigate to a group's Balances page. In **fa (RTL)**, verify:

1. **Suggested rows**: `@from-name` (strong) and `@to-name` (muted) sit right next to the avatars at the RTL start (right side of the row), not drifting to the left. `@` appears BEFORE each name.
2. **Per-member rows**: `@member-name` sits next to the role label "طلبکار/بدهکار/تسویه" at the RTL start. `@` before name.
3. **Breakdown rows** (after expanding a creditor or debtor row): `@other-name` sits next to the small avatar at the RTL start. `@` before name.

Then switch to **en (LTR)**:
- All `@username` reads naturally LTR (no regression).

If both languages look correct, **Phase A is verified** — Phase B (sweeping the remaining 22 sites in 8 other files) can be planned separately.

- [ ] **Step 4: Done — no commit needed**

This task only verifies. If anything is off, return to Task 2 (most likely cause: a `<UsernameHandle>` left out of one of the four sites).
