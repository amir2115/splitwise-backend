# Android Auth — Phase 1 Web/PWA Parity (Swiply Redesign)

**Date:** 2026-05-14
**Initiative:** Swiply Android-to-Web parity (4 phases)
**Phase:** F1 — Auth
**Status:** Design approved by user, ready for implementation plan

## Goal

Rebuild the Android Auth flow so it matches the new Vue/PWA web client (`web/`) at 1:1 parity — same routes, same page order, same UI, same animations, same icons, same API calls, same validation. The web client is the source of truth; Android catches up.

This phase covers the six Auth routes in the web router. Phases F2–F4 cover the rest of the app.

## Approach

A single PR delivering the full Phase 1 rebuild with carefully sequenced internal commits. The PR ships:

- A new `NavHost`-based navigation graph that replaces the current `RootStage` enum + boolean flags.
- A new design-token layer (`SwiplyTokens`, `SwiplyTheme`, `SwiplyMotion`).
- 33 `ImageVector` icons ported verbatim from `web/src/shared/components/Icon.vue` into `AppIcons`.
- Shared Auth composables (`AuthFormScaffold`, `AuthHeader`, `StepPill`, `AuthTextField`, `AuthPasswordField`, `OtpInputCells`, `InlineAlert`, `PrimaryButton`, `SecondaryButton`, `TextLinkButton`, `CountdownLabel`).
- Six new Auth screens (`LoginScreen`, `RegisterScreen`, `ForgotPasswordScreen`, `CompleteAccountScreen`, `ChangePasswordScreen`, `VerifyPhoneScreen`).
- Cleanup of the legacy `AuthScreen.kt`, `ChangePasswordScreen.kt`, `PasswordRecoveryScreen.kt`, `PhoneVerificationDialog.kt`, `AuthUiComponents.kt`, and the `RootStage` switching in `SplitwiseApp.kt`.

The PR is large but commit-sequenced so each commit is reviewable on its own: tokens → icons → shared composables → nav skeleton → screens (one per commit, in route order) → cleanup of legacy code.

## Navigation Architecture

### Route table (mirrors `web/src/app/router.ts` exactly)

| Route | Composable | Guards |
|---|---|---|
| `auth/login` | `LoginScreen` | `guestOnly` |
| `auth/register` | `RegisterScreen` | `guestOnly` |
| `auth/forgot-password` | `ForgotPasswordScreen` | `guestOnly` |
| `auth/complete-account?token={token}` | `CompleteAccountScreen` | `guestOnly` |
| `auth/change-password` | `ChangePasswordScreen` | `requiresAuth + passwordChangeOnly` |
| `auth/verify-phone` | `VerifyPhoneScreen` | `requiresAuth + phoneVerifyOnly` |
| `app/*` (placeholder) | existing screens via legacy entry | `requiresAuth` |

A new `core/navigation/AppNavigationGuards.kt` mirrors Vue Router's `beforeEach` for these rules:

- Unauthenticated → redirect to `auth/login`.
- `session.mustChangePassword == true` → force `auth/change-password`.
- Authenticated, non-guest, `requiresPhoneVerification == true` → force `auth/verify-phone`.
- `hasActiveSession && destinationIsGuestOnly` → redirect to `app/groups`.
- Deeplink `https://pwa.splitwise.ir/auth/complete-account?token=...` resolves to the `auth/complete-account` route with the `token` query argument.

Guard evaluation runs in a `LaunchedEffect` keyed to the current `navBackStackEntry` and the `Session` flow. Redirect calls `navController.navigate(target) { popUpTo(graphId) { inclusive = false } }` and adapts `popUpTo` per the guard (e.g. login redirect pops back to `auth/login` inclusive).

### Removed from `SplitwiseApp.kt`

- `RootStage` enum.
- `showForgotPassword`, `showCompleteAccountToken`, `phoneVerificationVisible` flags in `AppShellViewModel`.
- The `PhoneVerificationDialog` modal overlay.

### Kept in `AppShellViewModel`

- `session: StateFlow<Session?>`
- `isOnline: StateFlow<Boolean>`
- `apiCallStatus` (loading)
- Auth call methods (`login()`, `requestRegister()`, `verifyRegister()`, `resendRegister()`, `requestPasswordReset()`, `verifyPasswordResetCode()`, `confirmPasswordReset()`, `requestInvitedAccount()`, `verifyInvitedAccountPhone()`, `completeInvitedAccount()`, `changePassword()`, `requestPhoneVerification()`, `verifyPhone()`, `signOut()`).

Each new screen accesses these via `hiltViewModel<AppShellViewModel>(activityScope)` or a smaller per-screen `AuthViewModel` that wraps it. Pattern is decided per screen during implementation but is uniform within Phase 1.

## Foundation

### Design tokens — `ui/theme/SwiplyTokens.kt` and `SwiplyTheme.kt`

Values mirror `web/src/shared/theme/tokens.css` exactly.

**Colors** (light + dark scopes):
- Brand: `brand`, `brandStrong`, `brandSoft`, `brandOn`, `brandRing`.
- Surfaces: `bg`, `bgSubtle`, `surface`, `surface2`, `surfaceSunk`, `overlay`.
- Text: `fg`, `fgMuted`, `fgSubtle`, `fgInverse`.
- Borders: `border`, `borderStrong`, `divider`.
- Semantic: `pos`, `posSoft`, `neg`, `negSoft`, `warn`, `warnSoft`, `settled`, `settledSoft`.
- Accent: `accent`, `accentSoft`, `accentOn`.
- Interactive: `press`, `hover`, `ring`.
- Shadows: `shadow1`, `shadow2`, `shadow3`.
- Background gradient: composed `Brush` matching `--background-gradient`.

Light values copy from the `tokens.css` `light` block; dark values copy from the `dark` block. The legacy `Colors.kt` is rewritten to alias these (so existing Compose code using `MaterialTheme.colorScheme.primary` keeps compiling during the transition, but Auth screens use `SwiplyTheme.colors.brand`).

**Type scale:** `tDisplay=28sp`, `tTitle=20sp`, `tH2=17sp`, `tBody=15sp`, `tLabel=13sp`, `tCaption=12sp`. Line heights `lhTight=1.15`, `lhSnug=1.3`, `lhBody=1.5`. Weights `fwRegular`, `fwMedium`, `fwSemibold`, `fwBold`.

**Spacing scale:** `s1=2dp`, `s2=4dp`, `s3=8dp`, `s4=12dp`, `s5=16dp`, `s6=20dp`, `s7=24dp`, `s8=32dp`, `s9=40dp`, `s10=56dp`.

**Shape:** `rSm=10dp`, `rMd=14dp`, `rLg=20dp`, `rXl=28dp`, `r2xl=36dp`, `rPill=CircleShape`.

**Typography:** `ui/theme/Typography.kt` reads the active locale (Persian → IranYekan, English → GoogleSans) and applies `FontFeature.tabularNums` to numerics.

### Motion — `ui/theme/SwiplyMotion.kt`

Durations: `dInstant=80ms`, `dFast=140ms`, `dBase=220ms`, `dSlow=320ms`, `dEmphasized=420ms`.

Easings: `easeStandard=CubicBezierEasing(0.2f, 0f, 0f, 1f)`, `easeExit=CubicBezierEasing(0.4f, 0f, 1f, 1f)`, `easeEnter=CubicBezierEasing(0f, 0f, 0f, 1f)`, `easeEmphasized=CubicBezierEasing(0.16f, 1f, 0.3f, 1f)`.

Composite transitions exposed as functions:
- `authScreenEnter()` — `fadeIn + slideInVertically(it/10) + scaleIn(initialScale=0.985f)` over `dSlow` with `easeEmphasized`.
- `authScreenExit()` — `fadeOut + slideOutVertically(-it/16)` over `dBase` with `easeStandard`.
- `inlineAlertEnter()` / `inlineAlertExit()` — fade + 4dp slide over `dFast`.
- `otpCellFocusScale()` — `animateFloatAsState(1f → 1.02f)` over `dFast`.
- `countdownNumberTransition()` — `AnimatedContent` with crossfade over `dInstant`.

These are used by:
- `NavHost`'s per-route `enterTransition`/`exitTransition`.
- `AnimatedContent` blocks switching steps within `RegisterScreen`, `ForgotPasswordScreen`, `CompleteAccountScreen`, `VerifyPhoneScreen`.
- `AnimatedVisibility` around every `InlineAlert`.
- Field-stagger animation in `AuthFormScaffold` (each field appears with `60ms * index` delay on first mount).

The legacy `ui/components/AppMotion.kt` is rewritten to delegate to `SwiplyMotion` so the rest of the app continues to compile.

### Icons — `ui/icons/AppIcons.kt`

A single Kotlin file declaring 33 `ImageVector` properties, each transcribing the SVG path from `web/src/shared/components/Icon.vue` verbatim. All icons use `viewportSize = 24f x 24f`, `stroke = 1.75f`, `strokeLineCap = Round`, `strokeLineJoin = Round`, `fill = null` (transparent) unless the source uses `fill="currentColor"` (the `dot` icon), and tint comes from `LocalContentColor`.

Names: `Plus`, `ArrowRight`, `ArrowLeft`, `ChevronRight`, `ChevronLeft`, `ChevronDown`, `Close`, `Check`, `Search`, `Users`, `Wallet`, `Scale`, `Settings`, `Home`, `Swap`, `Card`, `Copy`, `Edit`, `Trash`, `Dot`, `Eye`, `Download`, `Sparkle`, `Wifi`, `Phone`, `Moon`, `Sun`, `Lock`, `Mail`, `Shield`, `UserPlus`, `Message`, `Refresh`.

A helper composable `AppIcon(image: ImageVector, size: Dp = 18.dp, tint: Color = LocalContentColor.current, contentDescription: String? = null)` wraps `Icon(...)` with Swiply defaults. A `directedArrowIcon(isBack: Boolean): ImageVector` helper returns `ArrowRight` or `ArrowLeft` based on the current layout direction so back/forward icons honor RTL/LTR.

### Shared Auth composables

All under `ui/auth/` unless otherwise noted.

- `AuthFormScaffold(modifier, content)` — scrollable column with `imePadding`, background gradient from `SwiplyTheme`, centered content with `--content-width` cap on tablet, field-stagger setup. Matches `web .page-shell .auth-screen`.
- `AuthHeader(title: String, subtitle: String? = null, heroIcon: ImageVector? = null)` — title/subtitle text using `SwiplyTheme.typography.tTitle`/`tBody`. Matches `.auth-title`/`.auth-subtitle`.
- `StepPill(text: String, accent: Boolean)` — pill with `rPill` shape, `brand`/`brandSoft` colors. Matches `.auth-step-pill`/`--accent`.
- `AuthTextField(value, onValueChange, label, leadingIcon, placeholder, error, ime, keyboardType)` — OutlinedTextField with leading `AppIcon`, error border using `SwiplyTheme.colors.neg`, supporting text from `error`. Replaces ad-hoc fields in current `AuthScreen.kt`.
- `AuthPasswordField(value, onValueChange, label, leadingIcon = AppIcons.Lock, error, ime)` — built on `AuthTextField` with trailing `AppIcons.Eye` toggle.
- `OtpInputCells(value, onValueChange, length = 5, autoSubmit, onSubmit)` — `Row` of 5 cells. Each cell is a `BasicTextField` with `KeyboardType.NumberPassword`, single-digit filter. Manages `FocusRequester` per cell, paste handler, backspace navigation. Wraps in `CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr)`. Cell focus triggers `otpCellFocusScale` + border color animation. When all `length` digits are filled, fires `onSubmit` once.
- `InlineAlert(severity: AlertSeverity, text: String, icon: ImageVector?)` — `AnimatedVisibility` wrapped row with severity-specific colors (`neg`/`warn`/`brand`). Severities: `Error`, `Warning`, `Info`.
- `PrimaryButton(text, onClick, loading, enabled)` — filled button using `SwiplyTheme.colors.brand` / `brandOn`, height `s10=56dp`, shape `rLg=20dp`, with `ButtonLoadingIndicator` cross-fading the label when `loading`.
- `SecondaryButton(text, onClick, enabled)` — outlined ghost variant matching `.btn-ghost`.
- `TextLinkButton(text, onClick, secondary)` — `TextButton` with `brand` color, or muted `fgMuted` when `secondary=true` (used for the "Continue Offline" link).
- `CountdownLabel(secondsRemaining)` — formats `0:MM` with `countdownNumberTransition` crossfade on second change.

These are all new files. The current `AuthUiComponents.kt` (`PasswordTextField`, `OtpCodeInput`, `ButtonLoadingIndicator`) is replaced by these and deleted at the end of the PR.

## Cross-cutting concerns

### RTL/LTR

- `LocalLayoutDirection` follows the active locale.
- `OtpInputCells` and any pure-numeric input force `LayoutDirection.Ltr` via `CompositionLocalProvider`.
- `directedArrowIcon(isBack: Boolean)` chooses the correct arrow per direction.
- Phone-number `AuthTextField` always uses LTR.

### Copy strings (i18n)

- `LocalizedStrings.kt` is extended with all string keys used by the new Auth screens.
- Key names are copied from the web `shared/i18n/*` files verbatim (e.g. `auth.login.title`, `auth.register.step.form.title`, `auth.forgotPassword.identifier.subtitle`).
- Persian and English copy is copied byte-for-byte from web. No creative re-translation.

### Error mapping

- `AuthErrorMapper.kt` is reviewed against the web `mapError` (or equivalent) to ensure every server error code (`registration_username_taken`, `registration_phone_taken`, `registration_code_invalid`, `registration_code_expired`, `registration_attempts_exceeded`, `password_reset_code_invalid`, `phone_number_taken`, etc.) maps to the same localized string on both clients.
- `InlineAlert` accepts the mapped string + severity.

### SMS auto-fill

`SmsOtpRetriever` is kept (Android-specific UX enhancement; web has no equivalent). When it delivers a code:
- `OtpInputCells` is populated programmatically via `onValueChange`.
- Cells animate into the populated state (`otpCellFocusScale` per cell with `30ms * index` stagger so the digits look like they "type in").
- If the populated value reaches `length`, `onSubmit` auto-fires (mirrors web's auto-submit behavior).

### Field stagger

`AuthFormScaffold` exposes a `riseStep: Int` local via `CompositionLocal`. Each direct child that opts in (`AuthTextField`, `AuthPasswordField`, `InlineAlert`, button rows) reads the local, starts `animateFloatAsState` with `delay = index * 60ms`, and animates `alpha 0→1 + translateY 8dp→0`. The stagger triggers once on screen mount, not on subsequent recompositions.

## Per-screen specifications

### `auth/login` — `LoginScreen`

- Entry: route `auth/login`. Guard `guestOnly` redirects authenticated users to `app/groups`.
- Layout: `AuthFormScaffold` → `AuthHeader(strings.loginTitle, strings.loginSubtitle)` → `AuthTextField(username, leadingIcon = AppIcons.Users)` → `AuthPasswordField(password)` → `InlineAlert(error)` → `PrimaryButton(strings.loginAction, loading)` → `TextLinkButton(strings.forgotPassword, to = "auth/forgot-password")` → divider → `TextLinkButton("ساخت حساب جدید", to = "auth/register")` → spacer → `TextLinkButton(strings.continueOffline, secondary = true, onClick = continueAsGuest)`.
- State: `username`, `password`, `isSubmitting`, `error`.
- API: `POST /auth/login` with `{ username, password }`. On success, `launchPostAuthBootstrap()` then `navController.navigate("app/groups") { popUpTo("auth/login") { inclusive = true } }`.
- Icons: `Users`, `Lock`, `Eye`.
- Validation: both fields non-empty enables the button.
- Motion: `authScreenEnter/Exit`, `inlineAlertEnter/Exit`, field stagger.

### `auth/register` — `RegisterScreen`

- Entry: route `auth/register`. Guard `guestOnly`.
- Step state: `RegisterStep.Form ↔ RegisterStep.Otp`, switched via `AnimatedContent { authScreenEnter/Exit }`.
- Step 1 (Form):
  - Fields: `name` (`Users`), `username` (`UserPlus`), `phoneNumber` (`Phone`, validated by `isValidIranMobileInput`, LTR), `password` (`Lock`+`Eye`), `confirmPassword` (`Lock`+`Eye`).
  - API: `POST /auth/register/request` with `{ name, username, phone_number, password }`. Response: `{ registration_id, phone_number, resend_available_in_seconds }`.
  - On success: `step = Otp`, `maskedPhone = response.phone_number`, start countdown.
- Step 2 (OTP):
  - `StepPill("Step 2 of 2", accent = true)` above header.
  - `AuthHeader(strings.otpTitle, "با کد ارسالی به ${maskedPhone}")`.
  - `OtpInputCells(length = 5, autoSubmit = true, onSubmit = verify)`.
  - `SmsOtpRetriever` active.
  - `TextLinkButton(strings.resendCode, onClick = resend, enabled = resendAvailableInSeconds == 0)`, with `CountdownLabel(resendAvailableInSeconds)` when locked.
  - `PrimaryButton(strings.verifyAction, loading)` and `TextLinkButton(strings.backToForm, onClick = { step = Form })`.
  - API verify: `POST /auth/register/verify` with `{ registration_id, code }`. Response: AuthResponse → `launchPostAuthBootstrap()` → `navigate("app/groups") { popUpTo("auth/register") { inclusive = true } }`.
  - API resend: `POST /auth/register/resend` with `{ registration_id }`. Updates countdown.
- Validation: Step 1 — all fields non-empty, password ≥ 8 chars, `password == confirmPassword`, phone passes `isValidIranMobileInput`. Step 2 — all 5 digits filled (auto-submit on completion).
- Icons: `Users`, `UserPlus`, `Phone`, `Lock`, `Eye`, `Refresh`.
- Motion: step `AnimatedContent` with `authScreenEnter/Exit`, OTP cell focus scale, countdown crossfade.

### `auth/forgot-password` — `ForgotPasswordScreen`

- Entry: route `auth/forgot-password`. Guard `guestOnly`.
- Stage state: `Stage.Identifier → Stage.Otp → Stage.NewPassword`.
- Stage 1 (Identifier):
  - Field: `identifier` (no leading icon), normalized via `normalizePhoneCandidate` if it looks like a phone.
  - API: `POST /auth/forgot-password/request` with `{ identifier }`. Response: `{ masked_phone_number, resend_available_in_seconds }`.
  - `PrimaryButton(strings.sendCode)`.
- Stage 2 (OTP):
  - Same pattern as register OTP. SmsOtpRetriever active.
  - API verify: `POST /auth/forgot-password/verify` with `{ identifier, code }`. Response: `{ reset_token }`.
  - API resend: `POST /auth/forgot-password/request` with original identifier.
  - `TextLinkButton(strings.back, onClick = { stage = Identifier })`.
- Stage 3 (NewPassword):
  - Fields: `newPassword` (`Lock`+`Eye`), `confirmPassword` (`Lock`+`Eye`).
  - API: `POST /auth/forgot-password/confirm` with `{ reset_token, new_password }`. Response: AuthResponse → `launchPostAuthBootstrap()` → `navigate("app/groups")`.
- Validation: Stage 1 — identifier non-empty. Stage 3 — `newPassword ≥ 8` and equals `confirmPassword`.
- Icons: `Phone`, `Shield`, `Lock`, `Eye`, `Refresh`, `ArrowLeft`/`ArrowRight`.
- Motion: stage `AnimatedContent`, standard alert + stagger + countdown.

### `auth/complete-account?token={token}` — `CompleteAccountScreen`

- Entry: route `auth/complete-account` with required `token` query arg, or deeplink resolved into the same. Guard `guestOnly`.
- Initial: `LaunchedEffect(token) { requestInvitedAccount(token) }`. API: `POST /auth/invited-account/request` with `{ token }`. Response: `{ requires_phone_verification, masked_phone_number }`.
- State branching:
  - If `requires_phone_verification == true` → `Stage.PhoneOtp` first, then `Stage.NewPassword`.
  - Otherwise → `Stage.NewPassword` directly.
- Stage `PhoneOtp`:
  - `OtpInputCells` on `masked_phone_number`. SmsOtpRetriever active.
  - API verify: `POST /auth/invited-account/verify-phone` with `{ token, code }`. On success → `Stage.NewPassword`.
  - Resend: `POST /auth/invited-account/request` with original `token`.
- Stage `NewPassword`:
  - Fields: `newPassword` (`Lock`+`Eye`), `confirmPassword` (`Lock`+`Eye`).
  - API: `POST /auth/invited-account/complete` with `{ token, new_password }`. Response: AuthResponse → `launchPostAuthBootstrap()` → `navigate("app/groups")`.
- Edge case: initial `request` failure (expired token, network) → `InlineAlert(error)` plus `TextLinkButton("بازگشت به ورود", to = "auth/login")`.
- Icons: `Shield` (hero), `Phone`, `Lock`, `Eye`, `Refresh`.

### `auth/change-password` — `ChangePasswordScreen`

- Entry: route `auth/change-password`. Guard `requiresAuth + passwordChangeOnly`. The guard forces the user here whenever `session.mustChangePassword == true` and refuses to leave until a successful change.
- Layout: `AuthFormScaffold` → `AuthHeader(strings.changePasswordTitle, strings.changePasswordSubtitle)` → three fields: `currentPassword`, `newPassword`, `confirmPassword` (each `AuthPasswordField`) → `InlineAlert(error)` → `PrimaryButton(strings.changePasswordAction, loading)` → `TextLinkButton(strings.signOut, secondary = true, onClick = signOut)`.
- API: `POST /auth/change-password` with `{ current_password, new_password }`. Response: updated `User` → `session.mustChangePassword = false` → `navigate("app/groups") { popUpTo("auth/change-password") { inclusive = true } }`.
- Validation: all three non-empty, `newPassword ≥ 8`, `newPassword != currentPassword`, `newPassword == confirmPassword`.
- Icons: `Shield` (hero optional), `Lock`, `Eye`.

### `auth/verify-phone` — `VerifyPhoneScreen`

- Entry: route `auth/verify-phone`. Guard `requiresAuth + phoneVerifyOnly`. Forced when `session.user.phoneNumber.isVerified == false` and the user is not in guest mode.
- Step state: `Stage.PhonePrompt ↔ Stage.Otp`.
- Stage `PhonePrompt`:
  - `AuthHeader` with `Shield` hero.
  - Field: `phoneNumber` (`Phone`, `isValidIranMobileInput`, LTR).
  - API: `POST /auth/phone/request-verification` with `{ phone_number }`. Response: `{ phone_number, resend_available_in_seconds }` → `Stage.Otp`.
  - `TextLinkButton(strings.signOut, secondary = true)` at the bottom.
- Stage `Otp`:
  - `StepPill`, `OtpInputCells`, resend with `CountdownLabel`. SmsOtpRetriever active.
  - API verify: `POST /auth/phone/verify` with `{ phone_number, code }`. Response: updated `User` → `session.requiresPhoneVerification = false` → `navigate("app/groups")`.
  - API resend: `POST /auth/phone/request-verification` with same phone.
  - `TextLinkButton(strings.back, onClick = { stage = PhonePrompt })` and `TextLinkButton(strings.signOut, secondary = true)`.

## Files touched

### New

- `ui/theme/SwiplyTokens.kt`, `SwiplyTheme.kt`, `SwiplyMotion.kt`, `Typography.kt` (rewrite).
- `ui/icons/AppIcons.kt`.
- `ui/auth/AuthFormScaffold.kt`, `AuthHeader.kt`, `StepPill.kt`, `AuthTextField.kt`, `AuthPasswordField.kt`, `OtpInputCells.kt`, `InlineAlert.kt`, `PrimaryButton.kt`, `SecondaryButton.kt`, `TextLinkButton.kt`, `CountdownLabel.kt`.
- `features/auth/LoginScreen.kt`, `RegisterScreen.kt`, `ForgotPasswordScreen.kt`, `CompleteAccountScreen.kt`, `VerifyPhoneScreen.kt`.
- `core/navigation/AppNavGraph.kt`, `AppNavigationGuards.kt`.

### Modified

- `core/navigation/SplitwiseApp.kt` — replaces `RootStage` with `NavHost(graph = AppNavGraph)`.
- `core/navigation/AppRoutes.kt` — adds auth route constants and helper builders.
- `ui/theme/Colors.kt`, `Theme.kt` — rewritten to wrap `SwiplyTokens`; legacy `MaterialTheme.colorScheme.*` aliases preserved so the rest of the app keeps compiling.
- `ui/components/AppMotion.kt` — delegates `AppAnimatedVisibility`/`AppAnimatedSection` to `SwiplyMotion`.
- `core/navigation/AppShellViewModel.kt` — removes `RootStage` and dialog flags; keeps auth methods and global state flows.
- `features/auth/AuthErrorMapper.kt` — extended for any new error codes; aligned with web.
- `ui/localization/LocalizedStrings.kt` — adds keys for new Auth copy, with values copied verbatim from web i18n.
- `features/auth/ChangePasswordScreen.kt` — fully rewritten in place to match the new design. (Kept at the same path; treated as a rewrite, not a new file.)

### Deleted (at end of PR, in cleanup commit)

- `features/auth/AuthScreen.kt`
- `features/auth/AuthUiComponents.kt`
- `features/auth/PasswordRecoveryScreen.kt`
- `features/auth/PhoneVerificationDialog.kt`

## Verification

1. Side-by-side screenshots: every route in `{light, dark} × {fa, en}` on a Pixel 7 emulator vs the web app at 412×915 in Chrome. Stored under `docs/swiply-parity/phase1/screenshots/`.
2. Motion recordings: short screen recordings of each step transition, alert appearance, OTP focus, countdown, route transitions. Stored under `docs/swiply-parity/phase1/motion/`. Each is reviewed against the web counterpart for duration and easing parity.
3. Network log diff: for each flow (login, register, forgot, complete-account, change, verify-phone), capture and compare request/response payloads from web and Android with mitmproxy. Payloads and headers must match.
4. Icon visual diff: PNG export of each of the 33 web SVGs vs Compose-rendered `ImageVector` bitmap; pixel diff < 1% per icon.
5. Unit tests:
   - `AppNavigationGuards` — one test per redirect rule.
   - `AuthErrorMapper` — one test per error code.
   - Per-screen form validation — pure functions extracted from each screen's view model.
6. Manual checklist at `docs/swiply-parity/phase1/manual-checklist.md` covering: offline submit, rotation, SMS auto-fill, back/forward navigation, deeplink open from cold start, locale switch mid-flow, theme switch mid-flow.

The PR is not mergeable until items 1–5 are complete and item 6 is signed off by the maintainer.

## Out of scope

- `app/*` routes (Groups, GroupDashboard, Members, ExpenseEditor, ExpenseDetail, SettlementEditor, Balances, Settings, AppDownload). These belong to Phases F2–F4.
- Replacing icons in non-Auth features. They migrate in the phase that touches their screen.
- The legacy `HeroCards.kt` component is kept; it is used by non-Auth features and is not used by the new Auth screens.
- Server-side changes. No new API endpoints are introduced; only consumption changes.
- NavGraph performance optimizations (lazy graph loading, etc.). Revisit in F2 if needed.
- Web side does not gain "Continue Offline" in this phase; that's an Android-only entry point with web-matched styling.
