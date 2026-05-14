# Expense "By share" Split Mode — Full-Stack Design

**Date:** 2026-05-14
**Scope:** Add a third `SHARE` value to the `SplitType` enum end-to-end (backend models/schemas/service + Alembic migration + frontend types/logic/UI), plus i18n strings.
**Source design:** Swiply Redesign — `ExpenseSharesScreen` component (extracted from `/tmp/swiply-design-4.html`).

## Context

The expense editor currently supports two split modes:
- `EQUAL` — equal slice per participant
- `EXACT` — user types each member's exact amount

The Swiply Redesign introduces a third mode, **"By share"**: each member gets a *share weight* (e.g. `2`, `1.5`, `0.5`); amounts distribute proportionally. The UX is a stepper per row plus a "value per share" summary, plus a few quick-preset chips for common ratios.

The user explicitly requested **full backend extension at the same fidelity as the existing two modes** — the share weights must round-trip (save and reload) without loss, identical in that respect to how EXACT preserves typed amounts. This requires:
- A new `SHARE` enum value persisted in Postgres
- A new nullable `weight` column on the `expense_shares` table

Existing EQUAL/EXACT logic stays unchanged.

## Goals

1. Add `SHARE` to `SplitType` end-to-end: backend enum + Postgres ENUM extension + frontend type union.
2. Persist `weight: float | None` per `ExpenseShare` row. NULL for EQUAL/EXACT rows; the user-entered weight for SHARE rows.
3. Server-side validation + normalization for SHARE: at least one positive weight; amounts computed as `round(total × weight / sum_of_weights)`; rounding leftover added to the share with the largest weight so `sum(amount_owed) == total_amount` exactly.
4. Frontend UI: third tab labeled "By share" in the split-type segmented control, with a per-share summary card, per-row stepper, and quick-preset chips.
5. Round-trip fidelity: editing a saved SHARE expense reopens with the original weights and recomputes amounts live.

## Non-goals

- No changes to EQUAL or EXACT modes (audit confirms they have full backend + frontend support).
- No changes to the expense detail page (it shows resolved amounts — same for all three modes).
- No new payer logic. The payer pickers and payer split UI are orthogonal.
- No multi-decimal weights beyond what `float` already supports (0, 0.5, 1.0, 1.5, 2, etc. are all fine).
- No "extras" (tax / service / discount) logic changes. The existing `applyDiscount` machinery in `expenseEditor.ts` keeps working for all three modes.

## Architecture

### Backend

#### 1. Enum extension — `app/models/domain.py:14`

```python
class SplitType(str, Enum):
    EQUAL = "EQUAL"
    EXACT = "EXACT"
    SHARE = "SHARE"
```

#### 2. `ExpenseShare` model — add `weight` column

In `app/models/domain.py`, the existing `ExpenseShare` model:

```python
class ExpenseShare(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "expense_shares"
    # ...
    expense_id: Mapped[str] = mapped_column(...)
    member_id: Mapped[str] = mapped_column(...)
    amount_owed: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # NEW
```

NULL for EQUAL/EXACT rows; the weight value for SHARE rows.

#### 3. Schemas — `app/schemas/domain.py`

`ExpenseParticipantAmount` gains an optional `weight`:

```python
class ExpenseParticipantAmount(BaseModel):
    member_id: UUID
    amount: int
    weight: Optional[float] = None
```

`ExpenseShareRead` (and any equivalent output schema) exposes `weight` on responses.

#### 4. Service-layer split logic — `app/services/crud_service.py:_resolve_split`

Add a new branch BEFORE the existing EXACT fallthrough:

```python
if split_type == SplitType.SHARE:
    weighted = [(item.member_id, float(item.weight or 0.0)) for item in shares]
    total_weight = sum(w for _, w in weighted)
    if total_weight <= 0:
        raise DomainError(
            code="invalid_expense",
            message="At least one share weight must be greater than zero",
        )
    if any(w < 0 for _, w in weighted):
        raise DomainError(
            code="invalid_expense",
            message="Share weights cannot be negative",
        )
    raw = [(mid, int(round(total_amount * w / total_weight))) for mid, w in weighted]
    diff = total_amount - sum(amt for _, amt in raw)
    if diff != 0:
        idx_max = max(range(len(weighted)), key=lambda i: weighted[i][1])
        mid, amt = raw[idx_max]
        raw[idx_max] = (mid, amt + diff)
    normalized = [
        ExpenseParticipantAmount(member_id=mid, amount=amt, weight=w)
        for (mid, amt), (_, w) in zip(raw, weighted)
    ]
    return payers, normalized
```

For EXACT: the existing branch ignores `weight` on the incoming payload (any `weight` passed for EXACT is silently dropped). Same for EQUAL.

#### 5. Child-row writer — `app/services/crud_service.py:_apply_expense_children`

Existing function builds `ExpenseShare(expense_id=..., member_id=..., amount_owed=item.amount)`. Add `weight=item.weight`:

```python
expense.shares.extend(
    ExpenseShare(
        expense_id=expense.id,
        member_id=item.member_id,
        amount_owed=item.amount,
        weight=item.weight,
    )
    for item in shares
)
```

#### 6. Alembic migration — `alembic/versions/20260514_000014_expense_share_split.py`

```python
"""expense by-share split mode

Revision ID: 20260514_000014
Revises: 20260503_000013
"""
from alembic import op
import sqlalchemy as sa

revision = "20260514_000014"
down_revision = "20260503_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add the weight column (nullable; existing rows unaffected)
    op.add_column(
        "expense_shares",
        sa.Column("weight", sa.Float(), nullable=True),
    )

    # 2. Extend the Postgres ENUM. ALTER TYPE ... ADD VALUE cannot run inside a
    # transaction block, so use AUTOCOMMIT.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE split_type ADD VALUE IF NOT EXISTS 'SHARE'")


def downgrade() -> None:
    # Remove the column; the ENUM value is not removed (Postgres does not
    # support DROP VALUE), so downgrade is partial — a stale 'SHARE' value
    # would remain reachable on rows that haven't been migrated. Since this
    # is irreversible at the ENUM level, downgrade only drops the column.
    op.drop_column("expense_shares", "weight")
```

Postgres-specific note: `ALTER TYPE ... ADD VALUE` requires running outside a transaction. Alembic's `autocommit_block` provides this. If a future maintainer moves to SQLite for development, the migration still works because SQLite stores enum values as plain strings — the `ALTER TYPE` becomes a no-op-ish (or skipped with an explicit dialect check; we'll handle this defensively).

#### 7. Backend tests — `tests/test_expenses.py`

Add tests for the SHARE path:

- `test_share_split_distributes_proportionally` — total=300000, weights=[1,1,1] → each share=100000.
- `test_share_split_with_decimal_weights` — total=450000, weights=[2,1.5,1,1,0.5] → each member's amount matches `round(weight × per_share)`; sum equals total exactly.
- `test_share_split_zero_weight_skips_member` — weight=0 → amount=0, member still in shares list.
- `test_share_split_rejects_all_zero_weights` — all weights=0 → DomainError("share weight must be greater than zero").
- `test_share_split_rejects_negative_weight` — DomainError.
- `test_share_split_persists_weight_column` — after `create_expense`, reload from DB and assert each ExpenseShare.weight matches the input.
- `test_share_split_rounding_leftover_goes_to_heaviest_weight` — verifies the deterministic rounding patch.

If the existing test pattern uses fixtures/factories, follow that style.

### Frontend

#### 8. Types — `web-new-version/src/shared/api/types.ts`

```ts
export type SplitType = 'EQUAL' | 'EXACT' | 'SHARE'

export interface ExpenseShareInput {
  member_id: string
  amount: number
  weight?: number | null
}

export interface ExpenseShare extends ExpenseShareInput {
  // existing fields (id, created_at, etc.)
}
```

Wherever `ExpenseShare` / `ExpenseShareInput` are referenced (existing types), the optional `weight` field flows through.

#### 9. Editor logic — `web-new-version/src/modules/expenses/expenseEditor.ts`

The existing draft/form normalization branches on `splitType`. Add a SHARE branch that:
- Treats each member's `weight` (number) as the canonical input.
- Computes `total_weight = sum(weights)` from the draft state.
- For each member: `amount = round(totalAmount × weight / total_weight)`.
- Applies the same largest-remainder rounding patch as the backend (consistency between client preview and server result).
- The submitted payload passes both `amount` and `weight` for each share.

For EQUAL/EXACT: unchanged. They never set `weight` on the payload.

#### 10. UI — `web-new-version/src/modules/expenses/pages/ExpenseEditorPage.vue`

Add a third option to the existing split-type segmented control. The labels become: `Equal` / `Exact` / `By share`.

When `split_type === 'SHARE'`:

- **Per-share summary card** at the top of the participant section:
  - "Value per share" tile (brand-soft background, brand text, font 18): shows `round(totalAmount / total_weight)` as a formatted amount.
  - "Total shares" tile (sunken background, neutral text, font 18): shows `total_weight` (with up to 1 decimal place).
  - Side-by-side 2-col grid.
- **Member rows** (one per participant):
  - Avatar (36px).
  - `@username` (size 14, semibold).
  - Optional note text below the username (size 11, subtle).
  - **Share stepper**: a small `<div>` with three children — a `−` button (decrements by 0.5, min 0), the current weight (font 15, semibold, "num" class for tabular figures), and a `+` button (increments by 0.5). Background `surface-sunk`, padding 3, border-radius `r-sm`. The `+` button uses brand-soft tone.
  - Right-aligned: computed amount for that member (`round(weight × perShare)`), styled with brand color.
- **Quick-preset chips** below the rows (horizontal): each chip applies a uniform weight to ALL members:
  - `1× all` → every weight = 1
  - `2× adults` → every weight = 2 (sets all to 2; user then adjusts kids individually)
  - `0.5× kids` → every weight = 0.5
  - `0 to skip` → every weight = 0 (then user adjusts the people who participated)
- **Tip text** below the chips: "If someone ate 2 portions, give them 2 shares. Just a drink? 0.5." (translated for fa).

When switching split_type from EQUAL/EXACT to SHARE for the first time on an expense: seed every member's weight to 1. When switching back from SHARE to EQUAL/EXACT: weights are discarded.

Decimal weights are stored as `number` (JS float). The stepper steps by 0.5. Negative values blocked at the UI level.

Existing payer-side UI and extras (tax/service/discount) are unaffected.

#### 11. i18n — `web-new-version/src/shared/i18n/strings.ts`

Add 7 new keys:

```ts
shareSplitLabel: string         // 'سهم وزنی' / 'By share'
shareSplitSubtitle: string      // 'هر نفر چند سهم می‌گیرد؟' / 'How many shares does each person take?'
shareValuePerShare: string      // 'ارزش هر سهم' / 'Value per share'
shareTotalShares: string        // 'مجموع سهم‌ها' / 'Total shares'
shareTip: string                // tip text — see above
sharePresetAllOne: string       // '۱× همه' / '1× all'
sharePresetAdults: string       // '۲× بزرگسال' / '2× adults'
sharePresetKids: string         // '۰.۵× بچه‌ها' / '0.5× kids'
sharePresetSkip: string         // '۰ برای رد شدن' / '0 to skip'
```

That's 9 keys actually (including the 4 preset labels). Let me adjust the count: **9 new keys**.

## Edge cases

- **No members in the group:** UI hides the SHARE tab (already hidden in current code when `members.length === 0`).
- **All weights zero (server-side):** rejected with DomainError → frontend shows the existing inline-alert with `strings.amountTooLarge` equivalent (we'll use a new SHARE-specific validation message string or reuse an existing one).
- **All weights zero (client-side):** the "value per share" tile shows `—`; save button validates and shows error before submission.
- **Adding a new member after switching to SHARE:** the new member gets default weight 1.
- **Removing a member while in SHARE mode:** their weight goes with them; no orphan state.
- **Editing an EQUAL expense, switching to SHARE, and saving:** Backend re-validates the shares for SHARE, computes amounts. The `weight` column populates for all share rows.
- **Editing a SHARE expense, switching to EXACT, and saving:** Backend ignores `weight` payload, validates exact amounts sum to total. Shares persist with `weight=NULL` on save (the new amounts overwrite the old SHARE rows; the writer always writes the current payload).
- **Migration on a non-Postgres DB (SQLite for tests):** SQLite doesn't have a real ENUM type — the column is a `VARCHAR` with no constraint. The `ALTER TYPE` `op.execute()` will fail on SQLite. We guard it: `if op.get_context().dialect.name == 'postgresql': ALTER TYPE...`. SQLite just adds the column and moves on.
- **Rounding determinism:** Client and server must use the same rounding rule (largest-remainder to the heaviest weight) so client-side previews match what server persists.

## Files affected

| File | Type | Change |
|---|---|---|
| `app/models/domain.py` | modify | Add `SHARE` to enum; add `weight` column to `ExpenseShare` |
| `app/schemas/domain.py` | modify | Add optional `weight` to `ExpenseParticipantAmount` (and read schema) |
| `app/services/crud_service.py` | modify | Add SHARE branch to `_resolve_split`; pass `weight` through `_apply_expense_children` |
| `alembic/versions/20260514_000014_expense_share_split.py` | **create** | Add `weight` column; `ALTER TYPE split_type ADD VALUE 'SHARE'` (Postgres only) |
| `tests/test_expenses.py` | modify | ~6-7 new tests for SHARE branch |
| `web-new-version/src/shared/api/types.ts` | modify | Extend `SplitType` union; add optional `weight` to ExpenseShare types |
| `web-new-version/src/modules/expenses/expenseEditor.ts` | modify | Add SHARE branch in draft normalization + rounding patch |
| `web-new-version/src/modules/expenses/pages/ExpenseEditorPage.vue` | modify | Add "By share" tab, per-share summary, member steppers, quick presets, tip |
| `web-new-version/src/shared/i18n/strings.ts` | modify | 9 new keys (interface + fa + en) |

Existing frontend tests `group-balances`, `username-handle`, `icon` should continue to pass (none touch split-type logic directly).

## Testing

**Backend:** new tests in `tests/test_expenses.py` (listed in section 7).

**Frontend:** add 2-3 unit tests for the rounding helper in `expenseEditor.ts` (largest-remainder distribution; sum-matches-total invariant).

**Manual visual gate:**
1. New expense, switch to "By share" tab. Verify:
   - Default weight = 1 per member.
   - Per-share tiles show `total / member_count` and `member_count` respectively.
   - Stepper increments by 0.5 with `+`/`−` buttons.
   - Member amount on the right updates live as weights change.
   - Sum of member amounts equals total amount (rounding leftover applied to heaviest weight).
   - Quick-preset chips reset all weights to the chip's value.
2. Save → re-open the saved expense → verify weights round-trip correctly.
3. Switch a saved SHARE expense to EXACT and save → verify weights cleared on subsequent re-open.
4. RTL: layout reads right-to-left, stepper buttons swap visual sides.

## Out of scope

- Per-person notes in the SHARE rows (the design mockup has note text like "Full meal + drink"; we won't add a backend `note` field per share. If desired, add as a follow-up.)
- Default weight presets persisted per-group (e.g., "this group is all adults"). Out of scope; user manually sets weights each expense.
- Visualization of share distribution as a stacked bar / pie. Out of scope.
- Modifying the Expense Detail page to surface weights when viewing a SHARE expense — current detail page shows the resolved share/paid amounts which is sufficient. Adding the weight breakdown is a future polish.
