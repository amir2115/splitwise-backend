# Android F2 — Groups, GroupDashboard, Members Web/PWA Parity

**Date:** 2026-05-14
**Initiative:** Swiply Android-to-Web parity (4 phases)
**Phase:** F2 — Home + Group
**Status:** Design approved by user, ready for implementation plan
**Depends on:** F1 (Auth) — `docs/superpowers/specs/2026-05-14-android-auth-parity-design.md`

## Goal

Rebuild the three core post-login screens — `GroupsPage`, `GroupDashboardPage`, `MembersPage` — so they match the new Vue/PWA web client at 1:1 parity: same UI, animations, gestures, requests, validation. Web is the source of truth. The existing Compose screens are replaced in place at the same NavGraph routes that F1 set up.

This phase introduces the second wave of shared Swiply-themed components that F3/F4 will reuse: `PageTopBar`, `HeroCard`, `SummaryGrid`, `SectionHeader`, `EmptyStateCard`, `ListRow`, `Avatar`, `UsernameHandle`, `SuggestedPaymentCard`, `TransferFlow`, `BaseModal`, `SwipeableRow`, `SkeletonBox`, `PullToRefreshScaffold`.

## Approach

A single PR delivering the full F2 rebuild with carefully sequenced internal commits. The PR ships:

- Three new shared Swiply layout components: `PageTopBar`, `HeroCard`, `SummaryGrid`, `SectionHeader`, `EmptyStateCard`, `ListRow`, `Avatar`, `UsernameHandle`.
- New money-flow components reused later: `SuggestedPaymentCard`, `TransferFlow`.
- New interactive components: `BaseModal`, `SwipeableRow` (custom-gesture, web-spec thresholds), `PullToRefreshScaffold` (84.dp threshold), `SkeletonBox` (shimmer).
- `BankBins` table (Iranian bank BIN → name + color) ported from `web/src/modules/groupCards/banks.ts`.
- Rewritten `GroupsScreen.kt`, `GroupDashboardScreen.kt`, `MembersScreen.kt` plus split-out sub-components: `GroupCardsSection.kt`, `PersonalBalancesSummary.kt`, `MemberSuggestionPanel.kt`, `InlineMemberCreateForm.kt`, `NetHeroCard.kt`, `SectionWithExpand.kt`.
- Rewritten ViewModels (`GroupsViewModel`, `GroupDashboardViewModel`, `MembersViewModel`) with explicit `UiState` data classes.

Routes do not change. `groups`, `group/{groupId}`, `members/{groupId}` keep their names — only the composables they call change. This avoids disturbing the F1 NavHost wiring.

## NavGraph (no changes from F1)

| Route | Composable | Notes |
|---|---|---|
| `groups` | New `GroupsScreen` | Replaces the legacy implementation in place |
| `group/{groupId}` | New `GroupDashboardScreen` | Replaces the legacy implementation in place |
| `members/{groupId}` | New `MembersScreen` | Replaces the legacy implementation in place |

`AppNavigationGuards` from F1 needs no change. `requiresAuth + allowGuest` semantics are preserved.

## Shared components (new)

All under `ui/components/` unless noted.

- `PageTopBar(title, canGoBack, actions)` — height 56dp, title in `tH2`, optional leading back arrow via `directedArrowIcon(isBack = true)`, optional trailing action slot. Background `SwiplyTheme.colors.surface`, divider on bottom via 1dp border.
- `HeroCard(modifier, leading, title, subtitle, trailing)` — generic hero with leading slot (Avatar or Icon), title (`tTitle` semibold), subtitle (`tBody` muted), trailing CTA slot. Replaces the legacy `HeroCards.kt` for F2-touched screens (legacy stays for F3/F4).
- `SummaryGrid(items: List<SummaryItem>)` — two-column equal-width grid. Each item is `{label, amount, tone}` rendered with `AmountText`.
- `SectionHeader(text: String)` — `Text(tLabel, fgMuted)` with top padding `s4`.
- `EmptyStateCard(icon, title, subtitle, cta?)` — vertical column, centered, 24.dp icon, `tH2` title, `tBody` muted subtitle, optional `PrimaryButton` CTA.
- `ListRow(leading?, title, sub?, amount?, amountTone?, trailing?, onClick?)` — generic single source for groups/expenses/settlements/members rows.
- `Avatar(name, size = 40.dp, tone = AvatarTone.Brand)` — circle background colored per tone, initials inside. Tones: `Brand`, `Accent`, `Neutral`.
- `UsernameHandle(username: String)` — `Text("@$username")` with `Modifier` enforcing LTR so the handle stays readable inside RTL text.
- `SuggestedPaymentCard(from, to, amount, tone, icon?, onClick?)` — directional flow card with from→to and amount.
- `TransferFlow(from, to, fromCaption?, toCaption?, prefixAt = "@", stacked = false)` — arrow layout used inside `SuggestedPaymentCard` and elsewhere.
- `BaseModal(title, dismissible = true, onDismiss, body)` — `androidx.compose.material3.AlertDialog` themed with Swiply: `surface` container, `r-xl` shape, `s5` padding, optional close icon top-right.
- `SwipeableRow(...)` — see "SwipeableRow spec" below. Lives in `ui/components/` because F3 settlement-list also uses it.
- `SkeletonBox(modifier)` — shimmer using `infiniteRepeatable(tween(1200, easing = easeEmphasized))` over a linear gradient between `surface2` and `bgSubtle`.
- `PullToRefreshScaffold(threshold = 84.dp, onRefresh, content)` — custom implementation (not Material's PullRefreshState) to match web threshold and animation.

### SwipeableRow spec

```kotlin
@Composable
fun SwipeableRow(
    openId: String?,
    rowId: String,
    onOpenChange: (String?) -> Unit,
    onTap: () -> Unit,
    onLongPress: (() -> Unit)? = null,
    leadingActions: List<SwipeAction> = emptyList(),
    trailingActions: List<SwipeAction> = emptyList(),
    content: @Composable RowScope.() -> Unit,
)
```

Behavior parity with web `modules/groups/components/SwipeableGroupRow.vue`:

- `ACTION_WIDTH = 84.dp` per action.
- `SNAP_OPEN = 28.dp` — drag below this snaps back closed.
- `AUTO_TRIGGER = 110.dp` — drag past this fires the action immediately on release.
- `LONG_PRESS_MS = 480L` — hold time to fire `onLongPress`.
- `MOVE_TOLERANCE = 6.dp` — minimum movement to lock the gesture axis.
- Spring-back: `tween(240, easing = easeEmphasized)`.
- Implementation: `Modifier.pointerInput(...) { awaitPointerEventScope { ... } }` driving an `Animatable<Float>` `offsetX` and an `axisLock` state (`None`/`Horizontal`/`Vertical`). Vertical motion above `MOVE_TOLERANCE` cancels the long-press timer and prevents swipe.
- Haptic feedback (`LocalHapticFeedback.current.performHapticFeedback`) on crossing `AUTO_TRIGGER` and on long-press fire.
- Closing on `openId` prop change: when another row opens, this one springs back.

## BankBins

`modules/group_dashboard/BankBins.kt` ports `web/src/modules/groupCards/banks.ts` verbatim:

```kotlin
object BankBins {
    private data class Bank(val prefix: String, val nameFa: String, val nameEn: String, val color: Color)

    private val table: List<Bank> = listOf(
        Bank("603799", "ملی", "Melli", Color(0xFF...)),
        Bank("589210", "سپه", "Sepah", Color(0xFF...)),
        // ... full table from web
    )

    fun colorFor(cardNumber: String): Color {
        val digits = cardNumber.filter(Char::isDigit)
        return table.firstOrNull { digits.startsWith(it.prefix) }?.color
            ?: SwiplyTheme.colors.brandSoft
    }

    fun nameFor(cardNumber: String, language: AppLanguage): String? {
        val digits = cardNumber.filter(Char::isDigit)
        val bank = table.firstOrNull { digits.startsWith(it.prefix) } ?: return null
        return if (language == AppLanguage.EN) bank.nameEn else bank.nameFa
    }
}
```

Implementer copies the actual rows from web at execution time; this spec only fixes the API.

## GroupsScreen

### Route entry

`groups` — guard `requiresAuth + allowGuest`. On mount, `GroupsViewModel.load()` is called.

### Layout

`PullToRefreshScaffold(threshold = 84.dp)` wrapping a `LazyColumn`:

1. `PageTopBar(title = strings.appTitle, action = AppIcons.Plus → openCreate())`.
2. `HeroCard` with leading `Avatar(session?.name, 44.dp)`, title `session?.name ?: strings.homeHeroGuestTitle`, subtitle `"@${session?.username}" ?: strings.homeHeroGuestSubtitle`, trailing `PrimaryButton(strings.signIn or strings.addGroup)`.
3. Search field (only when `groups.size > 4`): `AuthTextField(value=query, leadingIcon=AppIcons.Search, placeholder=strings.searchGroupsLabel)`.
4. Invites section (`AnimatedVisibility` on non-empty or loading): `SectionHeader(strings.invitesTitle)` + per invite `InviteRow` with `[Reject] [Accept]` buttons.
5. Groups section: `SectionHeader(strings.groupsSectionTitle)` + one of:
   - `repeat(3) { SkeletonGroupRow() }` while loading,
   - `EmptyStateCard(strings.noGroupsTitle, strings.noGroupsSubtitle)` if `filteredGroups.isEmpty() && query.isBlank()`,
   - `EmptyStateCard(strings.noSearchResultsTitle, ...)` if filter yielded nothing,
   - else for each group: `SwipeableRow(leading = [Edit action], trailing = [Delete action], onLongPress = …, onTap = navigate(group/{id}))` wrapping a `GroupRowContent(group, balance, memberCount)`.
6. Three modal states are mutually exclusive: `createOrEditModal`, `longPressGroupId`, `pendingGroupActionId`. Each opens a `BaseModal` with the appropriate form or confirm body.

### ViewModel state

```kotlin
data class GroupsUiState(
    val groups: List<Group> = emptyList(),
    val invites: List<GroupInvite> = emptyList(),
    val membersByGroup: Map<String, List<Member>> = emptyMap(),
    val balancesByGroup: Map<String, GroupBalances> = emptyMap(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val invitesLoading: Boolean = false,
    val error: String? = null,
)
```

Methods (suspend where applicable): `load()`, `refresh()`, `create(name)`, `update(groupId, name)`, `deleteForEveryone(groupId)`, `leave(groupId)`, `acceptInvite(inviteId)`, `rejectInvite(inviteId)`.

### API endpoints

All already exist in `ApiClient`:

- `GET /groups`
- `POST /groups`
- `PATCH /groups/{id}`
- `DELETE /groups/{id}` (with `forEveryone` flag)
- `POST /members/{id}` (delete, used for leave)
- `GET /group-invites?status=pending`
- `POST /group-invites/{id}/accept`
- `POST /group-invites/{id}/reject`
- `GET /members?group_id={id}` (background per group, for member count)
- `GET /groups/{id}/balances` (background per group, for amount badge)

### Motion

- Hero/groups list rise: `SwiplyMotion.heroRiseEnter()` (400ms emphasized, 8dp).
- Invite section enter/exit: `inlineAlertEnter()` / `inlineAlertExit()`.
- Group rows: `LazyColumn.animateItemPlacement()`.
- SwipeableRow per spec above.
- Pull-to-refresh: threshold 84.dp.

### Validation

- Group name: non-empty, max 80 characters.
- `deleteForEveryone` enabled only when `group.user_id == currentUser.id || group.user_id == null`.

## GroupDashboardScreen

### Route entry

`group/{groupId}` — guard `requiresAuth`. On mount, `GroupDashboardViewModel.load(groupId)` cascade-fetches members, cards, expenses, settlements, balances in parallel after ensuring groups list is loaded.

### Layout

`PullToRefreshScaffold` wrapping a `Column`:

1. `PageTopBar(title = group?.name ?: strings.groupFallbackTitle, canGoBack = true, action = AppIcons.Users → navigate(members/{groupId}))`.
2. `NetHeroCard(label = heroLabel, amount = personalNet, paidTotal, owedTotal, memberCount, loading)`. Hero label is one of `strings.youAreOwed(amount)`, `strings.youOwe(amount)`, `strings.allSettledTitle` depending on `personalNet` sign.
3. `InlineAlert(AlertSeverity.Info, strings.needSecondMemberMessage)` only when `members.size < 2`.
4. `PersonalBalancesSummary(items = personalSummary, onSettleUp = …)` if there are debts, else `EmptyStateCard(strings.allSettledTitle, strings.allSettledSubtitle)`.
5. `TextLinkButton(strings.openBalancesLabel, → navigate(balances/{groupId}))`.
6. Quick actions row (two equal `QuickActionButton`s): `New Expense` and `Add Settlement`. Disabled when `members.size < 2`; disabled tap shows snackbar `strings.needSecondMemberMessage`.
7. `GroupCardsSection(...)` (see sub-component below).
8. `SectionWithExpand(strings.recentExpensesTitle, items = expenses, previewSize = 4, itemContent = ListRow(...))`.
9. `SectionWithExpand(strings.recentSettlementsTitle, items = settlements, previewSize = 4, itemContent = ListRow(...) with trailing trash button)`.

### ViewModel state

```kotlin
data class GroupDashboardUiState(
    val group: Group? = null,
    val members: List<Member> = emptyList(),
    val balances: GroupBalances? = null,
    val expenses: List<Expense> = emptyList(),
    val settlements: List<Settlement> = emptyList(),
    val groupCards: List<GroupCard> = emptyList(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val error: String? = null,
) {
    val canCreateTransactions: Boolean get() = members.size >= 2
    val personalNet: Long get() = …
    val paidTotal: Long get() = …
    val owedTotal: Long get() = …
    val personalSummary: List<DebtItem>? get() = …
}
```

`personalNet`, `paidTotal`, `owedTotal`, and `personalSummary` are derived in the ViewModel via the existing `SimplifyDebtsUseCase` / `BalanceCalculator`. Implementer extracts a pure helper if the calculation is duplicated between F2 and F4 (balances page).

### API endpoints

All already exist:

- `GET /groups/{id}/balances`
- `GET /members?group_id={id}`
- `GET /expenses?group_id={id}`
- `GET /settlements?group_id={id}`
- `DELETE /settlements/{id}`
- `GET /group-cards?group_id={id}`
- `POST /group-cards`
- `PATCH /group-cards/{id}`
- `DELETE /group-cards/{id}`

### Motion

- Hero rise: `heroRiseEnter()`.
- Recent expenses/settlements: `AnimatedContent(items)` with `featureTransitionEnter()` / `featureTransitionExit()`.
- Section expand/collapse: `AnimatedVisibility(expandVertically + fadeIn, 220ms)`.
- Group cards: `LazyColumn.animateItemPlacement()`.

### GroupCardsSection (sub-component)

Each card row:

- 4.dp left stripe with `BankBins.colorFor(card.cardNumber)`.
- `Avatar(memberName, 28.dp, AvatarTone.Brand)`.
- Column with cardholder name (`tBody`) and formatted card number (`monospace`, `tabular`, masked as `1234 5678 9012 3456`).
- Trailing icons `IconButton(AppIcons.Copy/Edit/Trash)`.

Modal create/edit (via `BaseModal`):

- `MemberDropdownPicker(members, selected, onSelect)` — `ExposedDropdownMenuBox` themed with Swiply colors.
- `CardNumberInput(value, onChange)` — four 4-digit cells with auto-advance and paste-split, similar shape to `OtpInputCells` but each cell takes 4 digits and width is bigger.
- `[Cancel] [Save]` actions row.

### Validation (cards)

- `cardholder` must be a member.
- `cardNumber` must be exactly 16 digits.

## MembersScreen

### Route entry

`members/{groupId}` — guard `requiresAuth`. On mount, `MembersViewModel.load(groupId)` fetches members; falls back to ensuring groups list is loaded first.

### Layout

1. `PageTopBar(title = strings.membersOfGroupPrefix + " " + group.name, canGoBack = true, action = AppIcons.Plus → openCreate())`.
2. `PullToRefreshScaffold` wrapping a `LazyColumn` of `MemberRow` items, or `repeat(4) { SkeletonMemberRow() }` while loading, or `EmptyStateCard(strings.noMembersTitle, strings.noMembersSubtitle)` if empty.
3. Modal (mutually exclusive with delete confirm): `MemberModalDialog(modal)` rendered via `BaseModal`.
4. Delete confirm: `BaseModal` with `[Cancel] [Delete]`.

### MemberRow

`Row` with `Avatar(member.username, 40.dp, AvatarTone.Brand)`, column with `UsernameHandle(member.username)` + optional `Chip(strings.pendingInviteLabel, tone = brandSoft)`, then `Text(strings.memberSince(formatDate(member.createdAt)), fgMuted)`. Trailing `IconButton(AppIcons.Edit, onEdit)` and `IconButton(AppIcons.Trash, tint = neg, onDelete)`.

### MemberModalDialog

Two modes via a sealed `MemberModalState`:

- `Create`: username input with leading `AppIcons.UserPlus`. When `username.length >= 2` and `!showInlineCreate`, render `MemberSuggestionPanel`. If user picks "create new", flip `showInlineCreate = true` and render `InlineMemberCreateForm` below.
- `Edit`: username input only.

`MemberSuggestionPanel` renders states: hint (query too short), loading spinner, error message, empty (with "User not found, create new?" link), or list of `SuggestionRow` (highlight on hover/`ArrowDown`/`ArrowUp`, select on tap/`Enter`).

`InlineMemberCreateForm`:

- `AuthTextField(value = name, label = strings.nameLabel, leadingIcon = AppIcons.Users)`.
- `AuthTextField(value = phone, label = strings.memberCreatePhoneLabel, leadingIcon = AppIcons.Phone, keyboardType = Phone)`.
- `AuthPasswordField(value = password, label = strings.passwordLabel)`.
- `TextLinkButton(strings.useDefaultPasswordAction, onClick = ::setDefaultPassword)`.

Footer: `[Cancel] [Save | Create user]` (text depends on `showInlineCreate`).

### ViewModel state

```kotlin
data class MembersUiState(
    val groupId: String,
    val group: Group? = null,
    val members: List<Member> = emptyList(),
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val modal: MemberModalState? = null,
    val pendingDelete: Member? = null,
)

sealed interface MemberModalState {
    data class Create(
        val username: String = "",
        val suggestions: List<UserSuggestion> = emptyList(),
        val suggestionsLoading: Boolean = false,
        val suggestionsError: String? = null,
        val highlightedIndex: Int = -1,
        val showInlineCreate: Boolean = false,
        val name: String = "",
        val phone: String = "",
        val password: String = "",
        val isSubmitting: Boolean = false,
        val error: String? = null,
    ) : MemberModalState

    data class Edit(
        val memberId: String,
        val username: String,
        val isSubmitting: Boolean = false,
        val error: String? = null,
    ) : MemberModalState
}
```

Methods: `load()`, `refresh()`, `openCreate()`, `openEdit(member)`, `dismiss()`, `setUsername(v)` (debounced search), `selectSuggestion(s)`, `switchToInlineCreate()`, `setName/setPhone/setPassword(v)`, `setDefaultPassword()`, `submit()`, `confirmDelete()`, `cancelDelete()`.

`setUsername` schedules a debounced search via `Flow.debounce(250)`; previous in-flight searches are cancelled.

### API endpoints

- `GET /members?group_id={id}` (already in client)
- `POST /members` (already in client)
- `GET /members/suggestions?group_id&query&limit=8` — **verify presence** during implementation; if missing in Android client, add it (backend exposes it per web call).
- `POST /members/inline-create` — verify and add if needed.
- `PATCH /members/{id}` (already in client)
- `DELETE /members/{id}` (already in client)

### Validation

- Suggestion-based create: username non-empty + a suggestion selected, or username non-empty and server accepts.
- Inline create: name non-empty, username non-empty, password ≥ 8 chars, phone optional but if non-empty must pass `isValidIranMobileInput`.
- Edit: username non-empty.

## Cross-cutting

### SwiplyMotion additions

```kotlin
fun heroRiseEnter(): EnterTransition =
    fadeIn(tween(400, easing = easeEmphasized)) +
    slideInVertically(tween(400, easing = easeEmphasized)) { 8 }

fun featureTransitionEnter(): EnterTransition =
    fadeIn(tween(220, easing = easeEmphasized)) +
    slideInVertically(tween(220, easing = easeEmphasized)) { it / 8 }

fun featureTransitionExit(): ExitTransition =
    fadeOut(tween(140, easing = easeStandard))

fun swipeSpring(): TweenSpec<Float> = tween(240, easing = easeEmphasized)

const val shimmerDuration = 1200
```

### RTL/LTR rules

- All screens inherit `LocalLayoutDirection` from the active locale.
- `AmountText`, card numbers, phone inputs, and OTP cells are forced LTR via `CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr)`.
- `UsernameHandle` wraps its text in an LTR composition local to keep `@user` readable in RTL contexts.

### i18n keys to add (in `AppStrings` as computed getters)

New keys for F2:

```
homeHeroGuestTitle, homeHeroGuestSubtitle
signIn, addGroup
invitesEmptyTitle, invitesEmptySubtitle
swipeActionEdit, swipeActionDelete, swipeActionLeave
groupActionsTitle, deleteForEveryoneConfirm, leaveConfirm
allSettledTitle, allSettledSubtitle
openMembersAction
cardCopiedToast
newCardTitle, editCardTitle, cardNumberLabel, cardholderLabel
noCardsTitle, noCardsSubtitle
noMembersTitle, noMembersSubtitle
createUserAction, createUserPrompt
useDefaultPasswordAction
errorRetryAction
fun membersCount(n: Int): String
fun youAreOwed(amount: String): String
fun youOwe(amount: String): String
```

Values are copied verbatim from `web/src/shared/i18n/*`.

## Files touched

### New

- `ui/components/PageTopBar.kt`, `HeroCard.kt`, `SummaryGrid.kt`, `SectionHeader.kt`, `EmptyStateCard.kt`, `ListRow.kt`, `Avatar.kt`, `UsernameHandle.kt`, `SuggestedPaymentCard.kt`, `TransferFlow.kt`, `BaseModal.kt`, `SwipeableRow.kt`, `SkeletonBox.kt`, `PullToRefreshScaffold.kt`.
- `features/group_dashboard/NetHeroCard.kt`, `PersonalBalancesSummary.kt`, `BankBins.kt`, `SectionWithExpand.kt`.
- `features/members/MemberSuggestionPanel.kt`, `InlineMemberCreateForm.kt`.
- Unit tests: `GroupsViewModelTest`, `GroupDashboardViewModelTest`, `MembersViewModelTest`, `BankBinsTest`.
- Instrumented test: `SwipeableRowGestureTest`.

### Modified (rewritten in place)

- `features/groups/GroupsScreen.kt`, `GroupsViewModel.kt`.
- `features/group_dashboard/GroupDashboardScreen.kt`, `GroupDashboardViewModel.kt`, `GroupCardsSection.kt`.
- `features/members/MembersScreen.kt`, `MembersViewModel.kt`.
- `ui/components/AppMotion.kt` — additional helpers if needed (otherwise unchanged).
- `ui/theme/SwiplyMotion.kt` — add `heroRiseEnter`, `featureTransition*`, `swipeSpring`, `shimmerDuration`.
- `ui/localization/Localization.kt` — add new keys as computed getters.

### Out of scope (kept for now)

- `ui/components/HeroCards.kt` (legacy) — still referenced by F3/F4 features. Migrates in F3.
- F3 routes and screens.
- F4 routes and screens.

## Verification

1. Side-by-side screenshots: every state for each screen in `{light, dark} × {fa, en}` on Pixel 7 emulator vs web Chrome at 412×915. Store under `docs/swiply-parity/phase2/screenshots/`.
2. Motion recordings: swipe (snap/auto-trigger/long-press), hero rise, section expand, pull-to-refresh threshold. Under `docs/swiply-parity/phase2/motion/`.
3. Network log diff: capture mitmproxy traces for create/edit/delete group, accept/reject invite, member CRUD with suggestions and inline-create, card CRUD, settlement delete from dashboard. Compare to web byte-for-byte.
4. Bank BIN visual diff: render the GroupCardsSection with a sample card per known bank; compare the stripe color to web side-by-side.
5. Unit tests:
   - `GroupsViewModelTest` — load, create, update, delete (both modes), leave, invite accept/reject, search filter.
   - `GroupDashboardViewModelTest` — cascade load, `personalNet` math, `canCreateTransactions` gating, settlement delete.
   - `MembersViewModelTest` — debounced search, suggestion select, inline-create submit, edit submit, delete.
   - `BankBinsTest` — `colorFor` and `nameFor` for at least ten known prefixes plus an unknown fallback.
6. Instrumented test:
   - `SwipeableRowGestureTest` — SNAP_OPEN, AUTO_TRIGGER, LONG_PRESS_MS, axis lock against vertical scroll.
7. Manual checklist at `docs/swiply-parity/phase2/manual-checklist.md` with the bullet set from the design discussion.

The PR is not mergeable until items 1–6 are green and item 7 is signed off.

## Open items the implementer must resolve

- Existence and shape of `/members/suggestions` and `/members/inline-create` in `AuthApi.kt` / `ApiClient.kt`. If absent, add them with the same payload web uses.
- Existence of `GroupCardsApi` create/update/delete endpoints in Android client. If missing, add to mirror web `groupCardsStore.save / remove`.
- Exact Bank BIN table content — copy directly from `web/src/modules/groupCards/banks.ts`.
- Whether `GroupBalances` already exposes `paid_total` and `owed_total` per member, or if the dashboard needs to compute via `BalanceCalculator`.
