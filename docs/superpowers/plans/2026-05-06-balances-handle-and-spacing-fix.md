# Balances — Handle Alignment + Eyebrow Spacing Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two regressions on the Balances page in the `web-new-version` PWA: (1) `@username` text now drifts to the LEFT of each row in RTL because the `.handle` utility forces `direction: ltr` on a stretched flex item; (2) the gap between the eyebrow ("پرداخت‌های پیشنهادی") and the title beneath it is still too tight at 8px.

**Architecture:** Two purely presentational CSS edits. Drop `direction: ltr` from `.handle` so it relies on `unicode-bidi: isolate` alone — the bidi algorithm then keeps `@` before the username while the element's block-level direction inherits from the page (RTL), restoring right-edge alignment. Bump `.balances-head__sub` margin-bottom from `var(--s-2)` (8px) to `var(--s-4)` (16px).

**Tech Stack:** Vue 3 SFC scoped CSS + global `app.css`. Working directory for all commands: `web-new-version/`.

---

## File Map

| File | Change |
|---|---|
| `web-new-version/src/shared/theme/app.css` | Remove `direction: ltr;` line from the `.handle` rule |
| `web-new-version/src/modules/balances/pages/BalancesPage.vue` | Bump `.balances-head__sub` `margin-bottom` from `var(--s-2)` to `var(--s-4)` |

No other files touched. No tests change. No data layer change.

---

## Task 1: Fix `.handle` so it isolates bidi without forcing block direction

**Files:**
- Modify: `web-new-version/src/shared/theme/app.css` (the `.handle` rule)

**Why:** With `direction: ltr` on a `<strong class="handle">` flex item that stretches the full width of `.member-row__body` (a column flexbox), CSS resolves `text-align: start` to LEFT and the username text drifts away from the avatar. Removing `direction: ltr` keeps the inherited RTL direction at the block level (so text aligns at the RTL start = right side of the row, next to the avatar) while `unicode-bidi: isolate` still creates an independent bidi paragraph for the `@username` content. Inside that isolate, the strong-LTR Latin characters drive the visual order, putting `@` before the name correctly.

- [ ] **Step 1: Apply the edit**

In `web-new-version/src/shared/theme/app.css`, find the `.handle` rule (added in the previous round, located right after the `.suggested-arrow,.toolbar-arrow` rule):

```css
/* Latin handles like @username — keep `@` before the name regardless of paragraph direction */
.handle {
  unicode-bidi: isolate;
  direction: ltr;
}
```

Change it to:

```css
/* Latin handles like @username — keep `@` before the name regardless of paragraph direction */
.handle {
  unicode-bidi: isolate;
}
```

(Just delete the `direction: ltr;` line. Keep the comment and the `unicode-bidi: isolate;` line.)

- [ ] **Step 2: Verify the rule reads correctly**

Run:

```bash
grep -A 3 "^\.handle" web-new-version/src/shared/theme/app.css
```

Expected output:

```
.handle {
  unicode-bidi: isolate;
}
```

If you still see a `direction: ltr;` line, the edit didn't land — re-apply Step 1.

- [ ] **Step 3: Type-check + build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds, no TypeScript or CSS errors.

- [ ] **Step 4: Commit**

```bash
git -C web-new-version add src/shared/theme/app.css
git -C web-new-version commit -m "fix(theme): drop forced LTR direction from .handle so RTL block alignment is preserved"
```

---

## Task 2: Bump eyebrow → title spacing on the Balances page

**Files:**
- Modify: `web-new-version/src/modules/balances/pages/BalancesPage.vue` (scoped `<style>` block, `.balances-head__sub` rule)

**Why:** The user explicitly wants visibly more breathing room between "پرداخت‌های پیشنهادی" (eyebrow) and the headline beneath it. Round 2 increased the gap from 2px to 8px (`var(--s-2)`); the screenshot shows that's still too tight. `var(--s-4)` (16px) is the next step in the spacing token system and matches what the user is asking for.

- [ ] **Step 1: Apply the edit**

In `web-new-version/src/modules/balances/pages/BalancesPage.vue`, inside the `<style scoped>` block, find:

```css
.balances-head__sub {
  font-size: var(--t-label);
  color: var(--fg-muted);
  margin-bottom: var(--s-2);
}
```

Change `margin-bottom: var(--s-2);` to `margin-bottom: var(--s-4);` so the rule reads:

```css
.balances-head__sub {
  font-size: var(--t-label);
  color: var(--fg-muted);
  margin-bottom: var(--s-4);
}
```

- [ ] **Step 2: Verify the change**

Run:

```bash
grep -A 4 "^\.balances-head__sub" web-new-version/src/modules/balances/pages/BalancesPage.vue
```

Expected output (the third line is the one that changed):

```
.balances-head__sub {
  font-size: var(--t-label);
  color: var(--fg-muted);
  margin-bottom: var(--s-4);
}
```

- [ ] **Step 3: Type-check + build**

```bash
cd web-new-version && npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git -C web-new-version add src/modules/balances/pages/BalancesPage.vue
git -C web-new-version commit -m "fix(balances): widen eyebrow-to-title gap to var(--s-4)"
```

---

## Task 3: Final verification

**Files:** none (verification only).

- [ ] **Step 1: Confirm two new commits landed**

```bash
git -C web-new-version log --oneline -3
```

Expected: top two commits are the two from Tasks 1 and 2 (handle direction fix + eyebrow spacing). The third line is the previous Round 2 commit `55af58a`.

- [ ] **Step 2: Run the existing test suite for the touched module**

```bash
cd web-new-version && npm test -- group-balances
```

Expected: 5/5 pass (no behavior changes since we only modified CSS).

- [ ] **Step 3: Manual visual check**

Run:

```bash
cd web-new-version && npm run dev
```

Open the app, navigate to a group's Balances page. In **fa (RTL)**, verify:

1. **Each row's `@username` sits next to its avatar/label on the RTL side (right edge of the row), not floating in the middle / left.** Specifically:
   - Suggested rows: the `@from` and `@to` lines align flush with the avatars at the RTL start — same horizontal column as before, no leftward drift.
   - Per-member rows: `@member-name` sits immediately next to the role label ("طلبکار"/"بدهکار"/"تسویه") at the RTL start.
   - Breakdown rows (after expanding a creditor/debtor): `@other-name` sits next to its small avatar on the RTL side.
2. **`@` still appears BEFORE the username** (e.g., `@amir2115`, not `amir2115@`) in every spot.
3. **Visible breathing room** between "پرداخت‌های پیشنهادی" eyebrow and the larger headline below it (about double what it was before — ~16px).

Then switch language to **en (LTR)** in Settings:
- All `@username` reads naturally LTR (as it always did) — no regression.
- The eyebrow-title spacing change applies in both languages (token-based, not RTL-specific).

Stop the dev server with Ctrl-C.

- [ ] **Step 4: Done — no commit needed**

This task only verifies. If the visuals match the description above, the fix is complete. If anything is off (still drifting, still tight), return to Task 1 or Task 2.
