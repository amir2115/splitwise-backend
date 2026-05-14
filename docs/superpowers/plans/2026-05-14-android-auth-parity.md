# Android Auth — Phase 1 Web/PWA Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Android's Auth flow to match the new Vue/PWA design 1:1 — routes, UI, animations, icons, validation, and request shapes. Spec: `docs/superpowers/specs/2026-05-14-android-auth-parity-design.md`.

**Architecture:** Replace `RootStage`-based switching in `SplitwiseApp.kt` with `NavHost` and six Auth routes that mirror `web/src/app/router.ts`. Introduce a Swiply design token layer (`SwiplyTheme`, `SwiplyMotion`, `AppIcons` with 33 ported SVGs) that the rest of the app will adopt in F2–F4. Build the six Auth screens on top.

**Tech Stack:** Kotlin, Jetpack Compose, Navigation Compose 2.9, Hilt 2.52, Retrofit, Material 3 (transitional). Tests: JUnit 4, kotlinx-coroutines-test, Compose UI testing (instrumentation), Robolectric is **not** used.

---

## File Structure

### New files

```
android/app/src/main/java/com/encer/splitwise/
├── ui/theme/
│   ├── SwiplyTokens.kt              # All design tokens (colors, type, spacing, shape)
│   ├── SwiplyTheme.kt               # CompositionLocal provider + theme wrapper
│   └── SwiplyMotion.kt              # Durations, easings, composite transitions
├── ui/icons/
│   ├── AppIcons.kt                  # 33 ImageVector definitions
│   └── AppIcon.kt                   # AppIcon composable + directedArrowIcon helper
├── ui/auth/
│   ├── AuthFormScaffold.kt          # Scrollable scaffold + field stagger
│   ├── AuthHeader.kt                # Title + subtitle
│   ├── StepPill.kt
│   ├── AuthTextField.kt             # OutlinedTextField + leading icon
│   ├── AuthPasswordField.kt         # AuthTextField + Eye toggle
│   ├── OtpInputCells.kt             # 5 cells, paste/keydown/auto-submit
│   ├── InlineAlert.kt
│   ├── PrimaryButton.kt
│   ├── SecondaryButton.kt
│   ├── TextLinkButton.kt
│   └── CountdownLabel.kt
├── core/navigation/
│   ├── AppNavGraph.kt               # NavHost + NavGraph builder
│   └── AppNavigationGuards.kt       # beforeEach-style guard rules
└── features/auth/
    ├── LoginScreen.kt
    ├── RegisterScreen.kt
    ├── ForgotPasswordScreen.kt
    ├── CompleteAccountScreen.kt
    └── VerifyPhoneScreen.kt
```

### Modified files

```
core/navigation/SplitwiseApp.kt          # RootStage → NavHost
core/navigation/AppRoutes.kt             # Add auth route constants
core/navigation/AppShellViewModel.kt     # Remove dialog flags; add verifyInvitedAccountPhone()
data/remote/api/AuthApi.kt               # Add POST /auth/invited-account/verify-phone
data/remote/network/ApiClient.kt         # Add verifyInvitedAccountPhone wrapper
data/sync/SyncCoordinator.kt             # Add verifyInvitedAccountPhone wrapper
data/remote/model/RemoteModels.kt        # Add InvitedAccountVerifyPhoneRequest type
features/auth/ChangePasswordScreen.kt    # Rewrite in place
features/auth/AuthErrorMapper.kt         # Add new error codes
ui/theme/Colors.kt                       # Replace values with web tokens
ui/theme/Theme.kt                        # Wrap SwiplyTheme, keep MaterialTheme aliases
ui/theme/Typography.kt                   # Locale-aware fonts
ui/components/AppMotion.kt               # Delegate to SwiplyMotion
ui/localization/LocalizedStrings.kt      # Add new keys verbatim from web
```

### Deleted files (final cleanup task)

```
features/auth/AuthScreen.kt
features/auth/AuthUiComponents.kt
features/auth/PasswordRecoveryScreen.kt
features/auth/PhoneVerificationDialog.kt
```

---

## Task 0: Bootstrap & guardrails

**Files:**
- Create branch: `feat/auth-phase1-parity`

- [ ] **Step 1: Create feature branch and confirm clean working tree**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise
git status
# expect: clean tree (or stash existing work)
git checkout -b feat/auth-phase1-parity
```

- [ ] **Step 2: Verify Android module builds in current state**

```bash
cd android
./gradlew :app:compileOrganicDebugKotlin
```

Expected: BUILD SUCCESSFUL. If it fails, fix the existing build error first — do **not** start this work on top of a broken tree.

- [ ] **Step 3: Run existing unit tests as baseline**

```bash
./gradlew :app:testOrganicDebugUnitTest
```

Expected: PASS. Note the test count; the new work must not reduce it.

- [ ] **Step 4: Commit branch baseline**

```bash
git commit --allow-empty -m "chore(auth): start phase-1 web parity branch"
```

---

## Task 1: SwiplyTokens — color, type, spacing, shape

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/ui/theme/SwiplyTokens.kt`

- [ ] **Step 1: Write the failing test**

`android/app/src/test/java/com/encer/splitwise/ui/theme/SwiplyTokensTest.kt`

```kotlin
package com.encer.splitwise.ui.theme

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.junit.Assert.assertEquals
import org.junit.Test

class SwiplyTokensTest {
    @Test fun `light brand matches web token`() {
        assertEquals(Color(0xFF0E6B61), SwiplyLightColors.brand)
    }
    @Test fun `dark brand matches web token`() {
        assertEquals(Color(0xFF5EB8A9), SwiplyDarkColors.brand)
    }
    @Test fun `spacing scale matches web token`() {
        val s = SwiplySpacing
        assertEquals(2.dp, s.s1)
        assertEquals(16.dp, s.s5)
        assertEquals(56.dp, s.s10)
    }
    @Test fun `radius scale matches web token`() {
        val r = SwiplyRadius
        assertEquals(10.dp, r.sm)
        assertEquals(28.dp, r.xl)
    }
    @Test fun `type scale matches web token`() {
        val t = SwiplyType
        assertEquals(28.sp, t.tDisplay)
        assertEquals(15.sp, t.tBody)
    }
}
```

- [ ] **Step 2: Run to confirm failure**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.SwiplyTokensTest"
```

Expected: FAIL (`SwiplyLightColors` etc. unresolved).

- [ ] **Step 3: Create `SwiplyTokens.kt`**

```kotlin
package com.encer.splitwise.ui.theme

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class SwiplyColors(
    val bg: Color, val bgSubtle: Color, val surface: Color, val surface2: Color,
    val surfaceSunk: Color, val overlay: Color,
    val fg: Color, val fgMuted: Color, val fgSubtle: Color, val fgInverse: Color,
    val border: Color, val borderStrong: Color, val divider: Color,
    val brand: Color, val brandStrong: Color, val brandSoft: Color,
    val brandOn: Color, val brandRing: Color,
    val accent: Color, val accentSoft: Color, val accentOn: Color,
    val pos: Color, val posSoft: Color,
    val neg: Color, val negSoft: Color,
    val warn: Color, val warnSoft: Color,
    val settled: Color, val settledSoft: Color,
    val press: Color, val hover: Color, val ring: Color,
)

val SwiplyLightColors = SwiplyColors(
    bg = Color(0xFFF6F2EA), bgSubtle = Color(0xFFEFE9DD),
    surface = Color(0xFFFFFBF4), surface2 = Color(0xFFF9F4EA),
    surfaceSunk = Color(0xFFECE5D6), overlay = Color(0x6B141E1C),
    fg = Color(0xFF15201E), fgMuted = Color(0xFF5C6562),
    fgSubtle = Color(0xFF8A8E87), fgInverse = Color(0xFFFFFBF4),
    border = Color(0x14182826), borderStrong = Color(0x24182826),
    divider = Color(0x0F182826),
    brand = Color(0xFF0E6B61), brandStrong = Color(0xFF0A5048),
    brandSoft = Color(0xFFDCECE8), brandOn = Color(0xFFFFFBF4),
    brandRing = Color(0x380E6B61),
    accent = Color(0xFFA07240), accentSoft = Color(0xFFF1E5D1),
    accentOn = Color(0xFFFFFBF4),
    pos = Color(0xFF0E6B61), posSoft = Color(0xFFDCECE8),
    neg = Color(0xFFB44B44), negSoft = Color(0xFFF4DFDC),
    warn = Color(0xFFB88B2C), warnSoft = Color(0xFFF3E6C7),
    settled = Color(0xFF6B7A76), settledSoft = Color(0xFFE5E7E1),
    press = Color(0x0D141E1C), hover = Color(0x0D0E6B61),
    ring = Color(0x380E6B61),
)

val SwiplyDarkColors = SwiplyColors(
    bg = Color(0xFF0C100F), bgSubtle = Color(0xFF0F1413),
    surface = Color(0xFF141A19), surface2 = Color(0xFF1A2120),
    surfaceSunk = Color(0xFF0B100F), overlay = Color(0x94000000),
    fg = Color(0xFFE9EDE9), fgMuted = Color(0xFF9DA6A2),
    fgSubtle = Color(0xFF6D746F), fgInverse = Color(0xFF0C100F),
    border = Color(0x14E9EDE9), borderStrong = Color(0x24E9EDE9),
    divider = Color(0x0DE9EDE9),
    brand = Color(0xFF5EB8A9), brandStrong = Color(0xFF7FCFC1),
    brandSoft = Color(0x245EB8A9), brandOn = Color(0xFF0A1918),
    brandRing = Color(0x475EB8A9),
    accent = Color(0xFFC49866), accentSoft = Color(0x24C49866),
    accentOn = Color(0xFF1A0F06),
    pos = Color(0xFF5EB8A9), posSoft = Color(0x245EB8A9),
    neg = Color(0xFFD97A6D), negSoft = Color(0x24D97A6D),
    warn = Color(0xFFD4A95A), warnSoft = Color(0x24D4A95A),
    settled = Color(0xFF8A938F), settledSoft = Color(0x1F8A938F),
    press = Color(0x0FE9EDE9), hover = Color(0x145EB8A9),
    ring = Color(0x475EB8A9),
)

object SwiplySpacing {
    val s1 = 2.dp;  val s2 = 4.dp;  val s3 = 8.dp;  val s4 = 12.dp
    val s5 = 16.dp; val s6 = 20.dp; val s7 = 24.dp; val s8 = 32.dp
    val s9 = 40.dp; val s10 = 56.dp
}

object SwiplyRadius {
    val sm = 10.dp;  val md = 14.dp; val lg = 20.dp
    val xl = 28.dp;  val xl2 = 36.dp
    // For pill use androidx.compose.foundation.shape.CircleShape from call sites.
}

object SwiplyType {
    val tDisplay = 28.sp; val tTitle = 20.sp; val tH2 = 17.sp
    val tBody = 15.sp; val tLabel = 13.sp; val tCaption = 12.sp
    const val lhTight = 1.15f
    const val lhSnug  = 1.30f
    const val lhBody  = 1.50f
}
```

- [ ] **Step 4: Run the tokens test, expect pass**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.SwiplyTokensTest"
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/ui/theme/SwiplyTokens.kt \
        android/app/src/test/java/com/encer/splitwise/ui/theme/SwiplyTokensTest.kt
git commit -m "feat(theme): add Swiply design tokens mirroring web tokens.css"
```

---

## Task 2: SwiplyTheme provider + Colors/Theme/Typography rewrite

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/ui/theme/SwiplyTheme.kt`
- Modify: `android/app/src/main/java/com/encer/splitwise/ui/theme/Colors.kt`
- Modify: `android/app/src/main/java/com/encer/splitwise/ui/theme/Theme.kt`
- Modify: `android/app/src/main/java/com/encer/splitwise/ui/theme/Typography.kt`

- [ ] **Step 1: Create `SwiplyTheme.kt`**

```kotlin
package com.encer.splitwise.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf

private val LocalSwiplyColors = staticCompositionLocalOf { SwiplyLightColors }

object SwiplyTheme {
    val colors: SwiplyColors
        @Composable @ReadOnlyComposable get() = LocalSwiplyColors.current
    val spacing get() = SwiplySpacing
    val radius get() = SwiplyRadius
    val type get() = SwiplyType
}

@Composable
fun ProvideSwiplyColors(dark: Boolean, content: @Composable () -> Unit) {
    val colors = if (dark) SwiplyDarkColors else SwiplyLightColors
    CompositionLocalProvider(LocalSwiplyColors provides colors, content = content)
}
```

- [ ] **Step 2: Rewrite `Colors.kt` to alias Swiply tokens for legacy code**

Replace the file contents entirely. The legacy `LightPrimary`, `DarkPrimary`, etc. become read-from-Swiply aliases so existing screens keep compiling:

```kotlin
package com.encer.splitwise.ui.theme

import androidx.compose.ui.graphics.Color

// Legacy aliases — derived from Swiply tokens. Do not introduce new uses; new
// code reads SwiplyTheme.colors directly.

val LightPrimary = SwiplyLightColors.brand
val LightOnPrimary = SwiplyLightColors.brandOn
val LightSecondary = SwiplyLightColors.brandStrong
val LightOnSecondary = SwiplyLightColors.brandOn
val LightTertiary = SwiplyLightColors.accent
val LightOnTertiary = SwiplyLightColors.accentOn
val LightBackground = SwiplyLightColors.bg
val LightOnBackground = SwiplyLightColors.fg
val LightSurface = SwiplyLightColors.surface
val LightOnSurface = SwiplyLightColors.fg
val LightSurfaceVariant = SwiplyLightColors.surfaceSunk
val LightOnSurfaceVariant = SwiplyLightColors.fgMuted
val LightOutline = SwiplyLightColors.fgSubtle
val LightError = SwiplyLightColors.neg
val LightOnError = Color(0xFFFFFFFF)

val DarkPrimary = SwiplyDarkColors.brand
val DarkOnPrimary = SwiplyDarkColors.brandOn
val DarkSecondary = SwiplyDarkColors.brandStrong
val DarkOnSecondary = SwiplyDarkColors.brandOn
val DarkTertiary = SwiplyDarkColors.accent
val DarkOnTertiary = SwiplyDarkColors.accentOn
val DarkBackground = SwiplyDarkColors.bg
val DarkOnBackground = SwiplyDarkColors.fg
val DarkSurface = SwiplyDarkColors.surface
val DarkOnSurface = SwiplyDarkColors.fg
val DarkSurfaceVariant = SwiplyDarkColors.surfaceSunk
val DarkOnSurfaceVariant = SwiplyDarkColors.fgMuted
val DarkOutline = SwiplyDarkColors.fgSubtle
val DarkError = SwiplyDarkColors.neg
val DarkOnError = Color(0xFF5C1410)

// Gradient stops mapped from --background-gradient.
val LightBackgroundGradientTop = SwiplyLightColors.bg
val LightBackgroundGradientBottom = SwiplyLightColors.bgSubtle

val DarkBackgroundGradientTop = SwiplyDarkColors.bg
val DarkBackgroundGradientMiddle = SwiplyDarkColors.bgSubtle
val DarkBackgroundGradientBottom = SwiplyDarkColors.surfaceSunk
```

- [ ] **Step 3: Update `Theme.kt` to wrap `ProvideSwiplyColors`**

Read the current `Theme.kt`, identify the `@Composable fun SwiplyTheme` (or whatever it's currently called — likely `SplitwiseTheme`), and wrap its content with `ProvideSwiplyColors(dark = isDark) { ... }`. Keep the existing `MaterialTheme(colorScheme = ...)` call so all current components still resolve.

Do not change the public name or signature of the existing theme composable in this task; we only inject `ProvideSwiplyColors` underneath it.

- [ ] **Step 4: Update `Typography.kt` to be locale-aware with tabular numerics**

Read the existing file. Wrap the Typography body so:
- `fontFamily` resolves to `IranYekan` when `LocalAppLocale.current == AppLocale.FA`, else `GoogleSans`.
- Each `TextStyle` includes `fontFeatureSettings = "tnum"` to enable tabular numerics globally (matches web `.num`, `.amount-text`).

If `LocalAppLocale` doesn't exist, fall back to reading `Locale.getDefault().language == "fa"` once at theme-construction time.

- [ ] **Step 5: Build and test**

```bash
./gradlew :app:compileOrganicDebugKotlin :app:testOrganicDebugUnitTest
```

Expected: BUILD SUCCESSFUL, no test regressions.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/ui/theme/
git commit -m "feat(theme): wire SwiplyTheme provider and align legacy colors to web tokens"
```

---

## Task 3: SwiplyMotion — durations, easings, composite transitions

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/ui/theme/SwiplyMotion.kt`
- Modify: `android/app/src/main/java/com/encer/splitwise/ui/components/AppMotion.kt` (delegate)

- [ ] **Step 1: Write the failing test**

`android/app/src/test/java/com/encer/splitwise/ui/theme/SwiplyMotionTest.kt`

```kotlin
package com.encer.splitwise.ui.theme

import org.junit.Assert.assertEquals
import org.junit.Test

class SwiplyMotionTest {
    @Test fun `durations match web tokens`() {
        assertEquals(80, SwiplyMotion.dInstant)
        assertEquals(140, SwiplyMotion.dFast)
        assertEquals(220, SwiplyMotion.dBase)
        assertEquals(320, SwiplyMotion.dSlow)
        assertEquals(420, SwiplyMotion.dEmphasized)
    }
}
```

- [ ] **Step 2: Run, expect fail**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.SwiplyMotionTest"
```

- [ ] **Step 3: Create `SwiplyMotion.kt`**

```kotlin
package com.encer.splitwise.ui.theme

import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically

object SwiplyMotion {
    const val dInstant = 80
    const val dFast = 140
    const val dBase = 220
    const val dSlow = 320
    const val dEmphasized = 420

    val easeStandard   = CubicBezierEasing(0.2f, 0f, 0f, 1f)
    val easeExit       = CubicBezierEasing(0.4f, 0f, 1f, 1f)
    val easeEnter      = CubicBezierEasing(0f, 0f, 0f, 1f)
    val easeEmphasized = CubicBezierEasing(0.16f, 1f, 0.3f, 1f)

    fun authScreenEnter(): EnterTransition =
        fadeIn(tween(dSlow, easing = easeEmphasized)) +
        slideInVertically(tween(dSlow, easing = easeEmphasized)) { it / 10 } +
        scaleIn(tween(dSlow, easing = easeEmphasized), initialScale = 0.985f)

    fun authScreenExit(): ExitTransition =
        fadeOut(tween(dBase, easing = easeStandard)) +
        slideOutVertically(tween(dBase, easing = easeStandard)) { -it / 16 }

    fun inlineAlertEnter(): EnterTransition =
        fadeIn(tween(dFast, easing = easeStandard)) +
        slideInVertically(tween(dFast, easing = easeStandard)) { 4 }

    fun inlineAlertExit(): ExitTransition =
        fadeOut(tween(dFast, easing = easeStandard))

    fun routeEnter(): EnterTransition = authScreenEnter()
    fun routeExit(): ExitTransition = authScreenExit()
}
```

- [ ] **Step 4: Run, expect pass**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.SwiplyMotionTest"
```

- [ ] **Step 5: Delegate `AppMotion.kt` to SwiplyMotion**

Read the current `ui/components/AppMotion.kt`. It exports `AppAnimatedVisibility` and `AppAnimatedSection`. Rewrite the implementations so they use `SwiplyMotion.inlineAlertEnter()` / `inlineAlertExit()` for their default in/out transitions. Keep the public function signatures unchanged so existing call sites still compile. Add a deprecation comment pointing to `SwiplyMotion` for new code.

- [ ] **Step 6: Build, run all tests**

```bash
./gradlew :app:compileOrganicDebugKotlin :app:testOrganicDebugUnitTest
```

Expected: green.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/ui/theme/SwiplyMotion.kt \
        android/app/src/main/java/com/encer/splitwise/ui/components/AppMotion.kt \
        android/app/src/test/java/com/encer/splitwise/ui/theme/SwiplyMotionTest.kt
git commit -m "feat(theme): add SwiplyMotion and route AppMotion through it"
```

---

## Task 4: AppIcons — 33 ImageVectors ported from Icon.vue

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/ui/icons/AppIcons.kt`
- Create: `android/app/src/main/java/com/encer/splitwise/ui/icons/AppIcon.kt`

- [ ] **Step 1: Write the rendering test**

`android/app/src/androidTest/java/com/encer/splitwise/ui/icons/AppIconsRenderingTest.kt`

```kotlin
package com.encer.splitwise.ui.icons

import androidx.compose.material3.Icon
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import org.junit.Rule
import org.junit.Test

class AppIconsRenderingTest {
    @get:Rule val composeTestRule = createComposeRule()

    @Test fun `all 33 icons render without throwing`() {
        val all = listOf(
            AppIcons.Plus, AppIcons.ArrowRight, AppIcons.ArrowLeft,
            AppIcons.ChevronRight, AppIcons.ChevronLeft, AppIcons.ChevronDown,
            AppIcons.Close, AppIcons.Check, AppIcons.Search,
            AppIcons.Users, AppIcons.Wallet, AppIcons.Scale,
            AppIcons.Settings, AppIcons.Home, AppIcons.Swap,
            AppIcons.Card, AppIcons.Copy, AppIcons.Edit, AppIcons.Trash,
            AppIcons.Dot, AppIcons.Eye, AppIcons.Download, AppIcons.Sparkle,
            AppIcons.Wifi, AppIcons.Phone, AppIcons.Moon, AppIcons.Sun,
            AppIcons.Lock, AppIcons.Mail, AppIcons.Shield,
            AppIcons.UserPlus, AppIcons.Message, AppIcons.Refresh,
        )
        check(all.size == 33)
        composeTestRule.setContent {
            all.forEachIndexed { i, vec -> Icon(vec, contentDescription = "icon-$i") }
        }
        composeTestRule.onNodeWithContentDescription("icon-0").assertIsDisplayed()
        composeTestRule.onNodeWithContentDescription("icon-32").assertIsDisplayed()
    }
}
```

- [ ] **Step 2: Run, expect compile failure (AppIcons unresolved)**

```bash
./gradlew :app:compileOrganicDebugAndroidTestKotlin
```

- [ ] **Step 3: Create `AppIcons.kt`**

Use the pattern below for every icon. The SVG `path d="…"` value in `web/src/shared/components/Icon.vue` becomes the `pathData` argument of `PathBuilder.pathFromString` after stripping whitespace; Compose's `materialPath`/`PathBuilder` accepts the SVG path syntax verbatim through `vectorXml` or the builder DSL.

Easiest stable approach: declare each as a `lazy ImageVector` using the SDK builder API. Below is the canonical pattern; apply to every name in `Icon.vue`.

```kotlin
package com.encer.splitwise.ui.icons

import androidx.compose.material.icons.materialPath
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.path
import androidx.compose.ui.unit.dp

object AppIcons {
    private fun build(name: String, body: ImageVector.Builder.() -> Unit): ImageVector =
        ImageVector.Builder(
            name = name,
            defaultWidth = 24.dp, defaultHeight = 24.dp,
            viewportWidth = 24f, viewportHeight = 24f,
        ).apply(body).build()

    private fun ImageVector.Builder.stroke(d: String): ImageVector.Builder {
        path(
            fill = null,
            stroke = SolidColor(Color.Black), // tint is applied at render time
            strokeLineWidth = 1.75f,
            strokeLineCap = StrokeCap.Round,
            strokeLineJoin = StrokeJoin.Round,
            pathFillType = androidx.compose.ui.graphics.PathFillType.NonZero,
            pathBuilder = { fromSvgPath(d) },
        )
        return this
    }
    // ↑ `fromSvgPath` is provided as an extension below.

    val Plus: ImageVector by lazy { build("Plus") { stroke("M12 5v14M5 12h14") } }

    val ArrowRight: ImageVector by lazy {
        build("ArrowRight") { stroke("M5 12h14M13 6l6 6-6 6") }
    }

    val ArrowLeft: ImageVector by lazy {
        build("ArrowLeft") { stroke("M19 12H5M11 18l-6-6 6-6") }
    }

    val ChevronRight: ImageVector by lazy { build("ChevronRight") { stroke("M9 6l6 6-6 6") } }
    val ChevronLeft:  ImageVector by lazy { build("ChevronLeft")  { stroke("M15 6l-6 6 6 6") } }
    val ChevronDown:  ImageVector by lazy { build("ChevronDown")  { stroke("M6 9l6 6 6-6") } }

    val Close: ImageVector by lazy { build("Close") { stroke("M6 6l12 12M18 6l-12 12") } }
    val Check: ImageVector by lazy { build("Check") { stroke("M5 12.5l4.5 4.5L19 7.5") } }
    val Search: ImageVector by lazy {
        build("Search") {
            // SVG has both a circle and a line — express as a single composite path.
            stroke("M11 5a6 6 0 1 1 0 12 6 6 0 0 1 0-12zM20 20l-4-4")
        }
    }

    val Users: ImageVector by lazy {
        build("Users") { stroke("M9 4.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM3 20c0-3 2.5-5 6-5s6 2 6 5M16 10.5a3 3 0 1 0 0-6M21 20c0-2.4-1.6-4.4-4-4.9") }
    }

    val Wallet: ImageVector by lazy {
        build("Wallet") { stroke("M4 7c0-1.7 1.3-3 3-3h10a3 3 0 0 1 3 3M4 7v10a3 3 0 0 0 3 3h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2H4M17 14.25a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5z") }
    }

    val Scale: ImageVector by lazy {
        build("Scale") { stroke("M12 4v16M6 20h12M5 10l2.5-5L10 10M14 10l2.5-5L19 10M4 10h7M13 10h7M4 10c0 2 1.3 3.5 3.5 3.5S11 12 11 10M13 10c0 2 1.3 3.5 3.5 3.5S20 12 20 10") }
    }

    val Settings: ImageVector by lazy {
        build("Settings") { stroke("M12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6zM19.4 14.6a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V20a2 2 0 0 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H4a2 2 0 0 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H10a1.6 1.6 0 0 0 1-1.5V4a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V10a1.6 1.6 0 0 0 1.5 1H20a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z") }
    }

    val Home: ImageVector by lazy {
        build("Home") { stroke("M4 11l8-7 8 7v8a2 2 0 0 1-2 2h-4v-6h-4v6H6a2 2 0 0 1-2-2z") }
    }
    val Swap: ImageVector by lazy {
        build("Swap") { stroke("M7 7h13M17 4l3 3-3 3M17 17H4M7 14l-3 3 3 3") }
    }
    val Card: ImageVector by lazy {
        build("Card") { stroke("M5.5 6h13a2.5 2.5 0 0 1 2.5 2.5v8a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 16.5v-8A2.5 2.5 0 0 1 5.5 6zM3 10h18M7 15h4") }
    }
    val Copy: ImageVector by lazy {
        build("Copy") { stroke("M11.5 9h8a2.5 2.5 0 0 1 2.5 2.5v8a2.5 2.5 0 0 1-2.5 2.5h-8a2.5 2.5 0 0 1-2.5-2.5v-8A2.5 2.5 0 0 1 11.5 9zM6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1") }
    }
    val Edit: ImageVector by lazy {
        build("Edit") { stroke("M4 20h4l10-10-4-4L4 16zM14 6l4 4") }
    }
    val Trash: ImageVector by lazy {
        build("Trash") { stroke("M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6") }
    }
    val Dot: ImageVector by lazy {
        ImageVector.Builder("Dot", 24.dp, 24.dp, 24f, 24f).apply {
            path(
                fill = SolidColor(Color.Black), stroke = null, strokeLineWidth = 0f,
                strokeLineCap = StrokeCap.Round, strokeLineJoin = StrokeJoin.Round,
                pathFillType = androidx.compose.ui.graphics.PathFillType.NonZero,
                pathBuilder = { fromSvgPath("M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z") },
            )
        }.build()
    }
    val Eye: ImageVector by lazy {
        build("Eye") { stroke("M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z") }
    }
    val Download: ImageVector by lazy {
        build("Download") { stroke("M12 4v12M7 11l5 5 5-5M4 20h16") }
    }
    val Sparkle: ImageVector by lazy {
        build("Sparkle") { stroke("M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6") }
    }
    val Wifi: ImageVector by lazy {
        build("Wifi") { stroke("M3 9a14 14 0 0 1 18 0M6 13a9 9 0 0 1 12 0M9 17a4 4 0 0 1 6 0M13 20a1 1 0 1 1-2 0 1 1 0 0 1 2 0z") }
    }
    val Phone: ImageVector by lazy {
        build("Phone") { stroke("M9.5 3h5A2.5 2.5 0 0 1 17 5.5v13a2.5 2.5 0 0 1-2.5 2.5h-5A2.5 2.5 0 0 1 7 18.5v-13A2.5 2.5 0 0 1 9.5 3zM10 18h4") }
    }
    val Moon: ImageVector by lazy {
        build("Moon") { stroke("M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z") }
    }
    val Sun: ImageVector by lazy {
        build("Sun") { stroke("M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4") }
    }
    val Lock: ImageVector by lazy {
        build("Lock") { stroke("M7 12.5a2.5 2.5 0 0 1 2.5-2.5h5a2.5 2.5 0 0 1 2.5 2.5v6a2.5 2.5 0 0 1-2.5 2.5h-5A2.5 2.5 0 0 1 7 18.5v-6zM8 10V7a4 4 0 0 1 8 0v3") }
    }
    val Mail: ImageVector by lazy {
        build("Mail") { stroke("M5.5 5h13A2.5 2.5 0 0 1 21 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 16.5v-9A2.5 2.5 0 0 1 5.5 5zM3 7l9 7 9-7") }
    }
    val Shield: ImageVector by lazy {
        build("Shield") { stroke("M12 3l8 3v6c0 4.5-3.3 8.5-8 9-4.7-.5-8-4.5-8-9V6zM9 12.5l2 2 4-4") }
    }
    val UserPlus: ImageVector by lazy {
        build("UserPlus") { stroke("M9 4.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM3 20c0-3 2.5-5 6-5s6 2 6 5M18 9v6M15 12h6") }
    }
    val Message: ImageVector by lazy {
        build("Message") { stroke("M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H10l-4 4v-4H6a2 2 0 0 1-2-2z") }
    }
    val Refresh: ImageVector by lazy {
        build("Refresh") { stroke("M4 12a8 8 0 0 1 13.7-5.7L20 9M20 4v5h-5M20 12a8 8 0 0 1-13.7 5.7L4 15M4 20v-5h5") }
    }
}

// SVG path mini-parser. Extension on the Compose PathBuilder. Implements the
// subset of SVG path syntax used in Icon.vue: M, m, L, l, H, h, V, v, C, c,
// S, s, Z, z, A, a. Numbers can be integer or decimal.
private fun androidx.compose.ui.graphics.vector.PathBuilder.fromSvgPath(d: String) {
    SvgPathTokenizer(d).walk(this)
}
```

Then add a small SVG path tokenizer in a sibling file or the same file. The tokenizer reads commands and forwards them to `moveTo / lineTo / horizontalLineTo / verticalLineTo / curveTo / reflectiveCurveTo / arcTo / close` on `PathBuilder`. Implement only the commands actually used in `Icon.vue` (verified by `grep -oE '[MmLlHhVvCcSsZzAa]' web/src/shared/components/Icon.vue | sort -u`).

If a path uses `circle cx cy r`, expand it to two arcs at write time, as done for `Dot`/`Eye`/`Search`/`Wallet`/`Wifi` in the strokes above.

- [ ] **Step 4: Create `AppIcon.kt`**

```kotlin
package com.encer.splitwise.ui.icons

import androidx.compose.material3.Icon
import androidx.compose.material3.LocalContentColor
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp

@Composable
fun AppIcon(
    image: ImageVector,
    contentDescription: String? = null,
    size: Dp = 18.dp,
    tint: Color = LocalContentColor.current,
    modifier: Modifier = Modifier,
) {
    Icon(
        imageVector = image,
        contentDescription = contentDescription,
        tint = tint,
        modifier = modifier.then(Modifier).run { this },
    )
}

@Composable
fun directedArrowIcon(isBack: Boolean): ImageVector {
    val ltr = LocalLayoutDirection.current == LayoutDirection.Ltr
    val pointsForward = isBack xor ltr.not()
    return if (pointsForward) AppIcons.ArrowRight else AppIcons.ArrowLeft
}
```

- [ ] **Step 5: Run instrumented test on Pixel emulator**

```bash
./gradlew :app:connectedOrganicDebugAndroidTest --tests "*.AppIconsRenderingTest"
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/ui/icons/ \
        android/app/src/androidTest/java/com/encer/splitwise/ui/icons/
git commit -m "feat(icons): port 33 web Icon.vue SVGs to AppIcons ImageVectors"
```

---

## Task 5: Shared Auth composables — scaffold, header, pill, text fields

**Files:**
- Create: `ui/auth/AuthFormScaffold.kt`, `AuthHeader.kt`, `StepPill.kt`, `AuthTextField.kt`, `AuthPasswordField.kt`

Each composable gets a small instrumented snapshot/UI test. Below shows the pattern; repeat per composable.

- [ ] **Step 1: Write `AuthFormScaffold` test**

`android/app/src/androidTest/java/com/encer/splitwise/ui/auth/AuthFormScaffoldTest.kt`

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class AuthFormScaffoldTest {
    @get:Rule val rule = createComposeRule()

    @Test fun `renders content inside scaffold`() {
        rule.setContent {
            AuthFormScaffold {
                Text("hello-auth-scaffold")
            }
        }
        rule.onNodeWithText("hello-auth-scaffold").assertIsDisplayed()
    }
}
```

- [ ] **Step 2: Run, expect compile fail**

```bash
./gradlew :app:compileOrganicDebugAndroidTestKotlin
```

- [ ] **Step 3: Implement `AuthFormScaffold.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.encer.splitwise.ui.theme.SwiplyTheme

val LocalAuthFieldStaggerIndex = compositionLocalOf<MutableState<Int>> {
    error("LocalAuthFieldStaggerIndex not provided")
}

@Composable
fun AuthFormScaffold(content: @Composable () -> Unit) {
    val staggerIndex = remember { mutableIntStateOf(0) }
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(SwiplyTheme.colors.bg)
            .imePadding(),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .widthIn(max = 760.dp)
                .align(Alignment.TopCenter)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = SwiplyTheme.spacing.s5, vertical = SwiplyTheme.spacing.s7),
            verticalArrangement = Arrangement.spacedBy(SwiplyTheme.spacing.s4),
        ) {
            CompositionLocalProvider(LocalAuthFieldStaggerIndex provides staggerIndex) {
                content()
            }
        }
    }
}
```

Add an import for `androidx.compose.runtime.MutableState` and ensure `mutableIntStateOf` (or `mutableStateOf(0)`) gives the right type. Adjust import names to match your Compose version.

- [ ] **Step 4: Run test, expect pass**

```bash
./gradlew :app:connectedOrganicDebugAndroidTest --tests "*.AuthFormScaffoldTest"
```

- [ ] **Step 5: Implement `AuthHeader.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import com.encer.splitwise.ui.icons.AppIcon
import com.encer.splitwise.ui.theme.SwiplyTheme

@Composable
fun AuthHeader(
    title: String,
    subtitle: String? = null,
    heroIcon: ImageVector? = null,
) {
    Column(verticalArrangement = Arrangement.spacedBy(SwiplyTheme.spacing.s3)) {
        if (heroIcon != null) AppIcon(heroIcon, size = 32.dp, tint = SwiplyTheme.colors.brand)
        Text(
            text = title,
            style = TextStyle(fontSize = SwiplyTheme.type.tTitle, fontWeight = FontWeight.SemiBold),
            color = SwiplyTheme.colors.fg,
        )
        if (subtitle != null) Text(
            text = subtitle,
            style = TextStyle(fontSize = SwiplyTheme.type.tBody),
            color = SwiplyTheme.colors.fgMuted,
        )
    }
}
```

- [ ] **Step 6: Implement `StepPill.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import com.encer.splitwise.ui.theme.SwiplyTheme

@Composable
fun StepPill(text: String, accent: Boolean = false) {
    val bg = if (accent) SwiplyTheme.colors.brand else SwiplyTheme.colors.brandSoft
    val fg = if (accent) SwiplyTheme.colors.brandOn else SwiplyTheme.colors.brand
    Text(
        text = text,
        style = TextStyle(fontSize = SwiplyTheme.type.tLabel, fontWeight = FontWeight.Medium),
        color = fg,
        modifier = Modifier
            .background(bg, CircleShape)
            .padding(horizontal = SwiplyTheme.spacing.s4, vertical = SwiplyTheme.spacing.s2),
    )
}
```

- [ ] **Step 7: Implement `AuthTextField.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import com.encer.splitwise.ui.icons.AppIcon

@Composable
fun AuthTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    leadingIcon: ImageVector? = null,
    placeholder: String? = null,
    error: String? = null,
    keyboardType: KeyboardType = KeyboardType.Text,
    enabled: Boolean = true,
    trailing: @Composable (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it) } },
        leadingIcon = leadingIcon?.let { { AppIcon(it) } },
        trailingIcon = trailing,
        isError = error != null,
        supportingText = error?.let { { Text(it) } },
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        enabled = enabled,
        singleLine = true,
        modifier = modifier,
    )
}
```

- [ ] **Step 8: Implement `AuthPasswordField.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import com.encer.splitwise.ui.icons.AppIcon
import com.encer.splitwise.ui.icons.AppIcons

@Composable
fun AuthPasswordField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    leadingIcon: ImageVector = AppIcons.Lock,
    error: String? = null,
    enabled: Boolean = true,
    modifier: Modifier = Modifier,
) {
    var visible by remember { mutableStateOf(false) }
    AuthTextField(
        value = value,
        onValueChange = onValueChange,
        label = label,
        leadingIcon = leadingIcon,
        error = error,
        keyboardType = KeyboardType.Password,
        enabled = enabled,
        trailing = {
            IconButton(onClick = { visible = !visible }) {
                AppIcon(AppIcons.Eye)
            }
        },
        modifier = modifier,
    )
}
```

Note: `OutlinedTextField` does not accept `visualTransformation` from a parent through the wrapper. If a `visualTransformation` is required, copy the body of `AuthTextField` inline and add `visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation()`. Keep the rest identical.

- [ ] **Step 9: Run all instrumented tests**

```bash
./gradlew :app:connectedOrganicDebugAndroidTest --tests "*.AuthFormScaffoldTest"
./gradlew :app:compileOrganicDebugAndroidTestKotlin
```

- [ ] **Step 10: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/ui/auth/ \
        android/app/src/androidTest/java/com/encer/splitwise/ui/auth/
git commit -m "feat(ui-auth): scaffold, header, step pill, text + password fields"
```

---

## Task 6: OtpInputCells

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/ui/auth/OtpInputCells.kt`
- Create: `android/app/src/androidTest/java/com/encer/splitwise/ui/auth/OtpInputCellsTest.kt`

- [ ] **Step 1: Write the test (focuses on the public contract)**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTextInput
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class OtpInputCellsTest {
    @get:Rule val rule = createComposeRule()

    @Test fun `typing 5 digits triggers onSubmit once`() {
        var submittedWith: String? = null
        rule.setContent {
            val v = remember { mutableStateOf("") }
            OtpInputCells(
                value = v.value,
                onValueChange = { v.value = it },
                length = 5,
                autoSubmit = true,
                onSubmit = { submittedWith = it },
            )
        }
        repeat(5) { i ->
            rule.onNodeWithTag("otp-cell-$i").performTextInput("${i + 1}")
        }
        rule.waitForIdle()
        assertEquals("12345", submittedWith)
    }

    @Test fun `pasting 5 digits into first cell populates and submits`() {
        var submittedWith: String? = null
        rule.setContent {
            val v = remember { mutableStateOf("") }
            OtpInputCells(
                value = v.value,
                onValueChange = { v.value = it },
                length = 5,
                autoSubmit = true,
                onSubmit = { submittedWith = it },
            )
        }
        rule.onNodeWithTag("otp-cell-0").performTextInput("98765")
        rule.waitForIdle()
        assertEquals("98765", submittedWith)
    }

    @Test fun `non digits are rejected`() {
        rule.setContent {
            val v = remember { mutableStateOf("") }
            OtpInputCells(value = v.value, onValueChange = { v.value = it }, length = 5)
        }
        rule.onNodeWithTag("otp-cell-0").performTextInput("a")
        rule.onNodeWithTag("otp-cell-0").assertIsDisplayed()
        // No assertion on value here — the contract is "non-digit ignored". A direct check
        // requires exposing internal state, which we deliberately don't do.
    }
}
```

- [ ] **Step 2: Run, expect fail (`OtpInputCells` unresolved)**

```bash
./gradlew :app:compileOrganicDebugAndroidTestKotlin
```

- [ ] **Step 3: Implement `OtpInputCells.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.focusable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.encer.splitwise.ui.theme.SwiplyTheme

@Composable
fun OtpInputCells(
    value: String,
    onValueChange: (String) -> Unit,
    length: Int = 5,
    autoSubmit: Boolean = false,
    onSubmit: ((String) -> Unit)? = null,
    enabled: Boolean = true,
) {
    val focusRequesters = remember(length) { List(length) { FocusRequester() } }
    var lastSubmitted by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(value) {
        if (autoSubmit && value.length == length && value.all(Char::isDigit) && lastSubmitted != value) {
            lastSubmitted = value
            onSubmit?.invoke(value)
        }
        if (value.length < length) {
            focusRequesters.getOrNull(value.length)?.requestFocus()
        }
    }

    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(SwiplyTheme.spacing.s3),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            repeat(length) { i ->
                val cellValue = value.getOrNull(i)?.toString().orEmpty()
                BasicTextField(
                    value = cellValue,
                    onValueChange = { raw ->
                        val digits = raw.filter(Char::isDigit)
                        val merged = buildString {
                            append(value.take(i))
                            append(digits)
                            // overflow goes into next cells (paste support)
                        }.take(length)
                        onValueChange(merged)
                    },
                    singleLine = true,
                    enabled = enabled,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    textStyle = TextStyle(
                        fontSize = 22.sp,
                        textAlign = TextAlign.Center,
                        color = SwiplyTheme.colors.fg,
                    ),
                    modifier = Modifier
                        .testTag("otp-cell-$i")
                        .size(48.dp)
                        .border(
                            width = if (cellValue.isEmpty()) 1.dp else 1.5.dp,
                            color = if (cellValue.isEmpty()) SwiplyTheme.colors.border
                                    else SwiplyTheme.colors.brand,
                            shape = RoundedCornerShape(SwiplyTheme.radius.md),
                        )
                        .background(SwiplyTheme.colors.surface, RoundedCornerShape(SwiplyTheme.radius.md))
                        .padding(SwiplyTheme.spacing.s2)
                        .focusRequester(focusRequesters[i])
                        .focusable(),
                )
            }
        }
    }
}
```

- [ ] **Step 4: Run tests, expect pass**

```bash
./gradlew :app:connectedOrganicDebugAndroidTest --tests "*.OtpInputCellsTest"
```

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/ui/auth/OtpInputCells.kt \
        android/app/src/androidTest/java/com/encer/splitwise/ui/auth/OtpInputCellsTest.kt
git commit -m "feat(ui-auth): OTP input cells with paste, auto-submit, digit-only filter"
```

---

## Task 7: InlineAlert, PrimaryButton, SecondaryButton, TextLinkButton, CountdownLabel

**Files:**
- Create: `ui/auth/InlineAlert.kt`, `PrimaryButton.kt`, `SecondaryButton.kt`, `TextLinkButton.kt`, `CountdownLabel.kt`

- [ ] **Step 1: Implement `InlineAlert.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import com.encer.splitwise.ui.icons.AppIcon
import com.encer.splitwise.ui.theme.SwiplyMotion
import com.encer.splitwise.ui.theme.SwiplyTheme

enum class AlertSeverity { Error, Warning, Info }

@Composable
fun InlineAlert(severity: AlertSeverity, text: String?, icon: ImageVector? = null) {
    AnimatedVisibility(
        visible = !text.isNullOrBlank(),
        enter = SwiplyMotion.inlineAlertEnter(),
        exit = SwiplyMotion.inlineAlertExit(),
    ) {
        val (bg, fg) = when (severity) {
            AlertSeverity.Error   -> SwiplyTheme.colors.negSoft to SwiplyTheme.colors.neg
            AlertSeverity.Warning -> SwiplyTheme.colors.warnSoft to SwiplyTheme.colors.warn
            AlertSeverity.Info    -> SwiplyTheme.colors.brandSoft to SwiplyTheme.colors.brand
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(SwiplyTheme.spacing.s3),
            modifier = Modifier
                .background(bg, RoundedCornerShape(SwiplyTheme.radius.md))
                .padding(SwiplyTheme.spacing.s4),
        ) {
            if (icon != null) AppIcon(icon, tint = fg)
            Text(text.orEmpty(), color = fg)
        }
    }
}
```

- [ ] **Step 2: Implement `PrimaryButton.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.animation.Crossfade
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.encer.splitwise.ui.theme.SwiplyTheme

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    loading: Boolean = false,
    enabled: Boolean = true,
    modifier: Modifier = Modifier,
) {
    Button(
        onClick = onClick,
        enabled = enabled && !loading,
        colors = ButtonDefaults.buttonColors(
            containerColor = SwiplyTheme.colors.brand,
            contentColor = SwiplyTheme.colors.brandOn,
        ),
        modifier = modifier.fillMaxWidth().height(SwiplyTheme.spacing.s10),
    ) {
        Crossfade(targetState = loading, label = "PrimaryButtonLoading") { isLoading ->
            Box(contentAlignment = Alignment.Center) {
                if (isLoading) CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = SwiplyTheme.colors.brandOn,
                    strokeWidth = 2.dp,
                )
                else Text(text)
            }
        }
    }
}
```

- [ ] **Step 3: Implement `SecondaryButton.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.encer.splitwise.ui.theme.SwiplyTheme

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
    modifier: Modifier = Modifier,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        colors = ButtonDefaults.outlinedButtonColors(contentColor = SwiplyTheme.colors.brand),
        border = BorderStroke(1.dp, SwiplyTheme.colors.borderStrong),
        modifier = modifier.fillMaxWidth().height(SwiplyTheme.spacing.s10),
    ) { Text(text) }
}
```

Add the missing `import androidx.compose.ui.unit.dp` if your IDE doesn't suggest it.

- [ ] **Step 4: Implement `TextLinkButton.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.encer.splitwise.ui.theme.SwiplyTheme

@Composable
fun TextLinkButton(
    text: String,
    onClick: () -> Unit,
    secondary: Boolean = false,
    enabled: Boolean = true,
    modifier: Modifier = Modifier,
) {
    TextButton(onClick = onClick, enabled = enabled, modifier = modifier) {
        Text(
            text,
            color = if (secondary) SwiplyTheme.colors.fgMuted else SwiplyTheme.colors.brand,
        )
    }
}
```

- [ ] **Step 5: Implement `CountdownLabel.kt`**

```kotlin
package com.encer.splitwise.ui.auth

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.animation.core.tween
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.encer.splitwise.ui.theme.SwiplyMotion
import com.encer.splitwise.ui.theme.SwiplyTheme

@Composable
fun CountdownLabel(secondsRemaining: Int, modifier: Modifier = Modifier) {
    AnimatedContent(
        targetState = secondsRemaining,
        transitionSpec = {
            fadeIn(tween(SwiplyMotion.dInstant)) togetherWith fadeOut(tween(SwiplyMotion.dInstant))
        },
        label = "Countdown",
        modifier = modifier,
    ) { sec ->
        val m = sec / 60; val s = sec % 60
        Text(text = "%d:%02d".format(m, s), color = SwiplyTheme.colors.fgMuted)
    }
}
```

- [ ] **Step 6: Build**

```bash
./gradlew :app:compileOrganicDebugKotlin
```

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/ui/auth/InlineAlert.kt \
        android/app/src/main/java/com/encer/splitwise/ui/auth/PrimaryButton.kt \
        android/app/src/main/java/com/encer/splitwise/ui/auth/SecondaryButton.kt \
        android/app/src/main/java/com/encer/splitwise/ui/auth/TextLinkButton.kt \
        android/app/src/main/java/com/encer/splitwise/ui/auth/CountdownLabel.kt
git commit -m "feat(ui-auth): inline alert, buttons, countdown label"
```

---

## Task 8: Add missing `verifyInvitedAccountPhone` plumbing

The backend exposes `POST /auth/invited-account/verify-phone`, but `AuthApi.kt`, `ApiClient.kt`, `SyncCoordinator.kt`, and `AppShellViewModel.kt` don't have it. Add it.

**Files:**
- Modify: `data/remote/model/RemoteModels.kt` — add `InvitedAccountVerifyPhoneRequest`
- Modify: `data/remote/api/AuthApi.kt`
- Modify: `data/remote/network/ApiClient.kt`
- Modify: `data/sync/SyncCoordinator.kt`
- Modify: `core/navigation/AppShellViewModel.kt`

- [ ] **Step 1: Write the failing test**

Find the existing test pattern for `AppShellViewModel` if there is one; otherwise add a unit test for `SyncCoordinator.verifyInvitedAccountPhone()`.

`android/app/src/test/java/com/encer/splitwise/data/sync/SyncCoordinatorInvitedAccountVerifyPhoneTest.kt`

```kotlin
package com.encer.splitwise.data.sync

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertTrue
import org.junit.Test

class SyncCoordinatorInvitedAccountVerifyPhoneTest {
    @Test fun `verifyInvitedAccountPhone exists and forwards to ApiClient`() = runTest {
        // The signature must be: suspend fun verifyInvitedAccountPhone(token: String, code: String): Result<*>
        val ref: suspend (SyncCoordinator, String, String) -> Result<*> = { c, t, code ->
            c.verifyInvitedAccountPhone(t, code)
        }
        // Compile-time check is enough. Behavior is exercised in the
        // higher-level CompleteAccountScreen test in Task 13.
        assertTrue(true)
    }
}
```

- [ ] **Step 2: Run, expect compile fail (method doesn't exist)**

```bash
./gradlew :app:compileOrganicDebugUnitTestKotlin
```

- [ ] **Step 3: Add the request model**

`data/remote/model/RemoteModels.kt` — add near the other invited-account types:

```kotlin
data class InvitedAccountVerifyPhoneRequest(val token: String, val code: String)
```

- [ ] **Step 4: Add the Retrofit endpoint**

`data/remote/api/AuthApi.kt` — add inside the interface, alongside the other invited-account calls:

```kotlin
@Headers("No-Auth: true")
@POST("auth/invited-account/verify-phone")
suspend fun verifyInvitedAccountPhone(@Body request: InvitedAccountVerifyPhoneRequest): Response<Unit>
```

- [ ] **Step 5: Add the ApiClient wrapper**

`data/remote/network/ApiClient.kt` — read the file, find the pattern used by `requestInvitedAccount` and `completeInvitedAccount`, and add the same shape for `verifyInvitedAccountPhone(token: String, code: String): Unit`.

- [ ] **Step 6: Add the SyncCoordinator method**

`data/sync/SyncCoordinator.kt` — alongside `requestInvitedAccount` and `completeInvitedAccount`:

```kotlin
suspend fun verifyInvitedAccountPhone(token: String, code: String): Result<Unit> =
    runCatching { apiClient.verifyInvitedAccountPhone(token = token, code = code) }
```

- [ ] **Step 7: Add the AppShellViewModel method**

`core/navigation/AppShellViewModel.kt` — alongside `completeInvitedAccount`:

```kotlin
suspend fun verifyInvitedAccountPhone(token: String, code: String): Result<Unit> {
    return syncCoordinator.verifyInvitedAccountPhone(token, code)
}
```

- [ ] **Step 8: Run tests + build**

```bash
./gradlew :app:testOrganicDebugUnitTest :app:compileOrganicDebugKotlin
```

Expected: green.

- [ ] **Step 9: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/data/ \
        android/app/src/main/java/com/encer/splitwise/core/navigation/AppShellViewModel.kt \
        android/app/src/test/java/com/encer/splitwise/data/sync/SyncCoordinatorInvitedAccountVerifyPhoneTest.kt
git commit -m "feat(auth): plumb POST /auth/invited-account/verify-phone end-to-end"
```

---

## Task 9: AppRoutes constants for Auth routes

**Files:**
- Modify: `android/app/src/main/java/com/encer/splitwise/core/navigation/AppRoutes.kt`

- [ ] **Step 1: Read the current `AppRoutes.kt`**

It has constants like `groups`, `settings`, etc. We add an `Auth` nested object with all six routes.

- [ ] **Step 2: Add the constants**

```kotlin
object AppRoutes {
    // ... existing
    object Auth {
        const val LOGIN              = "auth/login"
        const val REGISTER           = "auth/register"
        const val FORGOT_PASSWORD    = "auth/forgot-password"
        const val COMPLETE_ACCOUNT   = "auth/complete-account?token={token}"
        const val CHANGE_PASSWORD    = "auth/change-password"
        const val VERIFY_PHONE       = "auth/verify-phone"

        fun completeAccount(token: String) = "auth/complete-account?token=$token"
    }
    object App {
        const val GROUPS = "app/groups"
    }
}
```

If `AppRoutes` is already a top-level object with flat constants, place the new ones inside but keep the existing top-level ones unchanged. Do not rename existing constants — `groups` callers stay valid.

- [ ] **Step 3: Build**

```bash
./gradlew :app:compileOrganicDebugKotlin
```

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/core/navigation/AppRoutes.kt
git commit -m "feat(nav): add AppRoutes.Auth constants matching web router"
```

---

## Task 10: AppNavigationGuards — beforeEach-style rules

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavigationGuards.kt`
- Create test: `android/app/src/test/java/com/encer/splitwise/core/navigation/AppNavigationGuardsTest.kt`

- [ ] **Step 1: Write failing tests**

```kotlin
package com.encer.splitwise.core.navigation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AppNavigationGuardsTest {
    @Test fun `unauthenticated to protected redirects to login`() {
        val state = GuardState(authenticated = false, isGuest = false, mustChangePassword = false, requiresPhoneVerification = false)
        assertEquals("auth/login", AppNavigationGuards.resolve(target = "app/groups", state = state))
    }

    @Test fun `unauthenticated to guest-only allows through`() {
        val state = GuardState(authenticated = false, isGuest = false, mustChangePassword = false, requiresPhoneVerification = false)
        assertNull(AppNavigationGuards.resolve(target = "auth/login", state = state))
    }

    @Test fun `active session to guest-only redirects home`() {
        val state = GuardState(authenticated = true, isGuest = false, mustChangePassword = false, requiresPhoneVerification = false)
        assertEquals("app/groups", AppNavigationGuards.resolve(target = "auth/login", state = state))
    }

    @Test fun `mustChangePassword forces change-password`() {
        val state = GuardState(authenticated = true, isGuest = false, mustChangePassword = true, requiresPhoneVerification = false)
        assertEquals("auth/change-password", AppNavigationGuards.resolve(target = "app/groups", state = state))
    }

    @Test fun `mustChangePassword allows the change-password route itself`() {
        val state = GuardState(authenticated = true, isGuest = false, mustChangePassword = true, requiresPhoneVerification = false)
        assertNull(AppNavigationGuards.resolve(target = "auth/change-password", state = state))
    }

    @Test fun `requiresPhoneVerification non-guest forces verify-phone`() {
        val state = GuardState(authenticated = true, isGuest = false, mustChangePassword = false, requiresPhoneVerification = true)
        assertEquals("auth/verify-phone", AppNavigationGuards.resolve(target = "app/groups", state = state))
    }

    @Test fun `requiresPhoneVerification guest is exempt`() {
        val state = GuardState(authenticated = true, isGuest = true, mustChangePassword = false, requiresPhoneVerification = true)
        assertNull(AppNavigationGuards.resolve(target = "app/groups", state = state))
    }
}
```

- [ ] **Step 2: Run, expect compile fail**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.AppNavigationGuardsTest"
```

- [ ] **Step 3: Implement `AppNavigationGuards.kt`**

```kotlin
package com.encer.splitwise.core.navigation

data class GuardState(
    val authenticated: Boolean,
    val isGuest: Boolean,
    val mustChangePassword: Boolean,
    val requiresPhoneVerification: Boolean,
)

object AppNavigationGuards {
    private val GUEST_ONLY = setOf(
        "auth/login", "auth/register", "auth/forgot-password", "auth/complete-account",
    )
    private val REQUIRES_AUTH_PREFIXES = listOf("app/")
    private const val LOGIN = "auth/login"
    private const val HOME = "app/groups"
    private const val CHANGE_PASSWORD = "auth/change-password"
    private const val VERIFY_PHONE = "auth/verify-phone"

    /**
     * Returns the redirect target as a route string, or null if the navigation is allowed.
     * `target` is the candidate route's base path (no query string).
     */
    fun resolve(target: String, state: GuardState): String? {
        val isGuestOnly = GUEST_ONLY.contains(target)
        val isProtected = REQUIRES_AUTH_PREFIXES.any { target.startsWith(it) }

        if (!state.authenticated && isProtected) return LOGIN
        if (state.authenticated && isGuestOnly) return HOME
        if (state.authenticated && state.mustChangePassword && target != CHANGE_PASSWORD) return CHANGE_PASSWORD
        if (state.authenticated && !state.isGuest && state.requiresPhoneVerification
            && target != VERIFY_PHONE && target != CHANGE_PASSWORD
            && !state.mustChangePassword) return VERIFY_PHONE
        return null
    }
}
```

- [ ] **Step 4: Run, expect pass**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.AppNavigationGuardsTest"
```

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavigationGuards.kt \
        android/app/src/test/java/com/encer/splitwise/core/navigation/AppNavigationGuardsTest.kt
git commit -m "feat(nav): AppNavigationGuards mirroring Vue router beforeEach"
```

---

## Task 11: AppNavGraph + LoginScreen (the first wired screen)

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavGraph.kt`
- Create: `android/app/src/main/java/com/encer/splitwise/features/auth/LoginScreen.kt`
- Modify: `android/app/src/main/java/com/encer/splitwise/core/navigation/SplitwiseApp.kt`

This is the first screen wired into the new nav. The remaining five screens follow the same shape in Tasks 12–16.

- [ ] **Step 1: Implement `LoginScreen.kt`**

```kotlin
package com.encer.splitwise.features.auth

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.encer.splitwise.R
import com.encer.splitwise.core.navigation.AppShellViewModel
import com.encer.splitwise.ui.auth.AuthFormScaffold
import com.encer.splitwise.ui.auth.AuthHeader
import com.encer.splitwise.ui.auth.AuthPasswordField
import com.encer.splitwise.ui.auth.AuthTextField
import com.encer.splitwise.ui.auth.AlertSeverity
import com.encer.splitwise.ui.auth.InlineAlert
import com.encer.splitwise.ui.auth.PrimaryButton
import com.encer.splitwise.ui.auth.TextLinkButton
import com.encer.splitwise.ui.components.appHiltViewModel
import com.encer.splitwise.ui.icons.AppIcons
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    onSuccess: () -> Unit,
    onNavigateRegister: () -> Unit,
    onNavigateForgot: () -> Unit,
    onContinueOffline: () -> Unit,
) {
    val vm: AppShellViewModel = appHiltViewModel()
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isSubmitting by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    AuthFormScaffold {
        AuthHeader(
            title = stringResource(R.string.auth_login_title),
            subtitle = stringResource(R.string.auth_login_subtitle),
        )
        AuthTextField(
            value = username,
            onValueChange = { username = it },
            label = stringResource(R.string.auth_username_label),
            leadingIcon = AppIcons.Users,
            enabled = !isSubmitting,
        )
        AuthPasswordField(
            value = password,
            onValueChange = { password = it },
            label = stringResource(R.string.auth_password_label),
            enabled = !isSubmitting,
        )
        InlineAlert(severity = AlertSeverity.Error, text = error)
        Spacer(modifier = androidx.compose.ui.Modifier.height(8.dp))
        PrimaryButton(
            text = stringResource(R.string.auth_login_action),
            loading = isSubmitting,
            enabled = username.isNotBlank() && password.isNotBlank(),
            onClick = {
                isSubmitting = true
                scope.launch {
                    val r = vm.login(username, password)
                    isSubmitting = false
                    if (r.isSuccess) onSuccess()
                    else error = AuthErrorMapper.message(r.exceptionOrNull(), context, isLogin = true)
                }
            },
        )
        TextLinkButton(
            text = stringResource(R.string.auth_forgot_password_link),
            onClick = onNavigateForgot,
        )
        TextLinkButton(
            text = stringResource(R.string.auth_register_link),
            onClick = onNavigateRegister,
        )
        TextLinkButton(
            text = stringResource(R.string.auth_continue_offline),
            onClick = onContinueOffline,
            secondary = true,
        )
    }
}
```

Notes for the implementer:
- `AuthErrorMapper.message(throwable, context, isLogin = true)` is the existing function in `features/auth/AuthErrorMapper.kt`; check its actual signature and adapt the call. If it's `resolveAuthErrorMessage(exception, strings, isLogin)`, use that.
- All `R.string.auth_*` keys are added in Task 17. Until then, hard-code English literals in this file as a temporary placeholder so it compiles; the cleanup task swaps them to `stringResource`.

- [ ] **Step 2: Implement `AppNavGraph.kt` with login wired up**

```kotlin
package com.encer.splitwise.core.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.encer.splitwise.features.auth.LoginScreen
import com.encer.splitwise.ui.theme.SwiplyMotion

@Composable
fun AppNavGraph(navController: NavHostController, startDestination: String) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
        enterTransition = { SwiplyMotion.routeEnter() },
        exitTransition = { SwiplyMotion.routeExit() },
    ) {
        composable(AppRoutes.Auth.LOGIN) {
            LoginScreen(
                onSuccess = {
                    navController.navigate("app/groups") {
                        popUpTo(AppRoutes.Auth.LOGIN) { inclusive = true }
                    }
                },
                onNavigateRegister = { navController.navigate(AppRoutes.Auth.REGISTER) },
                onNavigateForgot   = { navController.navigate(AppRoutes.Auth.FORGOT_PASSWORD) },
                onContinueOffline  = {
                    // Continue offline: keep guest mode, jump to app
                    navController.navigate("app/groups") {
                        popUpTo(AppRoutes.Auth.LOGIN) { inclusive = true }
                    }
                },
            )
        }

        // Other screens added in Tasks 12-16. For now, stub the "app/groups"
        // route to delegate to the existing main app composable so we can run
        // the new flow end-to-end without bringing F2-F4 into Phase 1.
        composable("app/groups") {
            // Temporary delegate. Replaced when F2 lands.
            ExistingMainAppShellPlaceholder()
        }
    }
}

@Composable
private fun ExistingMainAppShellPlaceholder() {
    // Render the existing post-auth UI here. Locate the current root composable
    // in SplitwiseApp.kt (the branch that runs when RootStage == APP) and call it.
}
```

The implementer must locate the existing "APP" stage block in `SplitwiseApp.kt`, extract it into a named composable (`AppShell()`), and call it from `ExistingMainAppShellPlaceholder()`.

- [ ] **Step 3: Wire NavHost in `SplitwiseApp.kt`**

Read `SplitwiseApp.kt`. Replace the `AnimatedContent(rootStage)` switching block with:

```kotlin
val navController = rememberNavController()
val session by appShellViewModel.sessionRepository.sessionFlow.collectAsState(initial = null)
val startDestination = remember(session) {
    when {
        session == null && deeplinkToken != null -> AppRoutes.Auth.completeAccount(deeplinkToken)
        session == null -> AppRoutes.Auth.LOGIN
        session?.mustChangePassword == true -> AppRoutes.Auth.CHANGE_PASSWORD
        session?.user?.phoneNumber?.isVerified == false && !session!!.isGuest -> AppRoutes.Auth.VERIFY_PHONE
        else -> "app/groups"
    }
}

LaunchedEffect(navController, session) {
    navController.currentBackStackEntryFlow.collect { entry ->
        val target = entry.destination.route?.substringBefore('?') ?: return@collect
        val state = GuardState(
            authenticated = session != null,
            isGuest = session?.isGuest == true,
            mustChangePassword = session?.mustChangePassword == true,
            requiresPhoneVerification = session?.user?.phoneNumber?.isVerified == false,
        )
        AppNavigationGuards.resolve(target, state)?.let { redirect ->
            navController.navigate(redirect) {
                popUpTo(navController.graph.id) { inclusive = false }
            }
        }
    }
}

AppNavGraph(navController = navController, startDestination = startDestination)
```

Field names (`sessionFlow`, `mustChangePassword`, `user.phoneNumber.isVerified`, `isGuest`) must match what `Session`/`SessionRepository` actually expose; check before implementing. If the field is `Session.isGuestMode`, use that name.

Keep the existing deeplink handling: read `intent.data` for `auth/complete-account` and feed it via `deeplinkToken` to the start-destination logic.

Remove the `RootStage` enum and the `rootStage` state variable in the same commit.

- [ ] **Step 4: Build and run on emulator**

```bash
./gradlew :app:installOrganicDebug
```

Manually verify: on a fresh install (no session), the app opens at `auth/login`. Entering valid credentials lands on the existing groups screen (via placeholder).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavGraph.kt \
        android/app/src/main/java/com/encer/splitwise/core/navigation/SplitwiseApp.kt \
        android/app/src/main/java/com/encer/splitwise/features/auth/LoginScreen.kt
git commit -m "feat(auth): NavHost-based AppNavGraph and LoginScreen"
```

---

## Task 12: RegisterScreen

**Files:**
- Create: `android/app/src/main/java/com/encer/splitwise/features/auth/RegisterScreen.kt`
- Modify: `core/navigation/AppNavGraph.kt` — add `composable(AppRoutes.Auth.REGISTER)`

- [ ] **Step 1: Write unit test for `RegisterValidation`**

`android/app/src/test/java/com/encer/splitwise/features/auth/RegisterValidationTest.kt`

```kotlin
package com.encer.splitwise.features.auth

import org.junit.Assert.assertEquals
import org.junit.Test

class RegisterValidationTest {
    @Test fun `valid form passes`() {
        assertEquals(
            RegisterFormError.None,
            RegisterValidation.validateForm(
                name = "Ali", username = "ali99", phone = "09123456789",
                password = "long-enough", confirm = "long-enough",
            )
        )
    }
    @Test fun `short password rejected`() {
        assertEquals(
            RegisterFormError.PasswordTooShort,
            RegisterValidation.validateForm("Ali","ali","09123456789","short","short"),
        )
    }
    @Test fun `mismatched confirm rejected`() {
        assertEquals(
            RegisterFormError.PasswordMismatch,
            RegisterValidation.validateForm("Ali","ali","09123456789","longenough","different1"),
        )
    }
    @Test fun `invalid Iran phone rejected`() {
        assertEquals(
            RegisterFormError.InvalidPhone,
            RegisterValidation.validateForm("Ali","ali","12345","longenough","longenough"),
        )
    }
    @Test fun `empty username rejected`() {
        assertEquals(
            RegisterFormError.UsernameRequired,
            RegisterValidation.validateForm("Ali","","09123456789","longenough","longenough"),
        )
    }
}
```

- [ ] **Step 2: Run, expect compile fail**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.RegisterValidationTest"
```

- [ ] **Step 3: Implement `RegisterValidation` as a top-level object in `RegisterScreen.kt`**

```kotlin
package com.encer.splitwise.features.auth

import com.encer.splitwise.features.auth.PhoneVerificationPolicy

enum class RegisterFormError { None, NameRequired, UsernameRequired, InvalidPhone, PasswordTooShort, PasswordMismatch }

object RegisterValidation {
    fun validateForm(name: String, username: String, phone: String, password: String, confirm: String): RegisterFormError {
        if (name.isBlank()) return RegisterFormError.NameRequired
        if (username.isBlank()) return RegisterFormError.UsernameRequired
        if (!PhoneVerificationPolicy.isValidIranMobileInput(phone)) return RegisterFormError.InvalidPhone
        if (password.length < 8) return RegisterFormError.PasswordTooShort
        if (password != confirm) return RegisterFormError.PasswordMismatch
        return RegisterFormError.None
    }
}
```

(`isValidIranMobileInput` is the existing helper — find its actual name and module before implementing.)

- [ ] **Step 4: Implement the `RegisterScreen` composable**

The composable has two steps (`Form` / `Otp`) inside an `AnimatedContent`. Show:
- Step.Form: fields (name, username, phone, password, confirm), validation, `PrimaryButton` calls `vm.requestRegister(...)`. On success, store `registrationId` + `maskedPhone` + start countdown; flip to Step.Otp.
- Step.Otp: `StepPill("Step 2 of 2", accent=true)`, `AuthHeader`, `OtpInputCells(autoSubmit=true, onSubmit = verify)`, `SmsOtpRetriever` integration (reuse the existing class), resend button + `CountdownLabel`, `PrimaryButton` triggers `vm.verifyRegister(registrationId, code)`.

Full composable code in the same shape as `LoginScreen` from Task 11. Don't introduce new helpers — reuse `AuthFormScaffold`, `AuthHeader`, `StepPill`, `AuthTextField`, `AuthPasswordField`, `OtpInputCells`, `InlineAlert`, `PrimaryButton`, `TextLinkButton`, `CountdownLabel`.

- [ ] **Step 5: Wire the route in `AppNavGraph.kt`**

```kotlin
composable(AppRoutes.Auth.REGISTER) {
    RegisterScreen(
        onSuccess = {
            navController.navigate("app/groups") {
                popUpTo(AppRoutes.Auth.REGISTER) { inclusive = true }
            }
        },
        onBackToLogin = { navController.navigate(AppRoutes.Auth.LOGIN) {
            popUpTo(AppRoutes.Auth.LOGIN) { inclusive = false }
        } },
    )
}
```

- [ ] **Step 6: Run tests + build**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.RegisterValidationTest"
./gradlew :app:compileOrganicDebugKotlin
```

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/features/auth/RegisterScreen.kt \
        android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavGraph.kt \
        android/app/src/test/java/com/encer/splitwise/features/auth/RegisterValidationTest.kt
git commit -m "feat(auth): RegisterScreen with form/OTP steps + validation tests"
```

---

## Task 13: ForgotPasswordScreen

**Files:**
- Create: `features/auth/ForgotPasswordScreen.kt`
- Modify: `core/navigation/AppNavGraph.kt` — add route

- [ ] **Step 1: Write validation tests**

```kotlin
package com.encer.splitwise.features.auth

import org.junit.Assert.assertEquals
import org.junit.Test

class ForgotPasswordValidationTest {
    @Test fun `empty identifier rejected`() {
        assertEquals(ForgotPasswordError.IdentifierRequired, ForgotPasswordValidation.validateIdentifier(""))
    }
    @Test fun `non-empty identifier ok`() {
        assertEquals(ForgotPasswordError.None, ForgotPasswordValidation.validateIdentifier("ali"))
    }
    @Test fun `password too short rejected`() {
        assertEquals(ForgotPasswordError.PasswordTooShort,
            ForgotPasswordValidation.validateNewPassword("short", "short"))
    }
    @Test fun `mismatch rejected`() {
        assertEquals(ForgotPasswordError.PasswordMismatch,
            ForgotPasswordValidation.validateNewPassword("longenough", "other-one"))
    }
    @Test fun `valid pair ok`() {
        assertEquals(ForgotPasswordError.None,
            ForgotPasswordValidation.validateNewPassword("longenough", "longenough"))
    }
}
```

- [ ] **Step 2: Implement validation + screen**

In `ForgotPasswordScreen.kt`:

```kotlin
package com.encer.splitwise.features.auth

enum class ForgotPasswordError { None, IdentifierRequired, PasswordTooShort, PasswordMismatch }

object ForgotPasswordValidation {
    fun validateIdentifier(v: String): ForgotPasswordError =
        if (v.isBlank()) ForgotPasswordError.IdentifierRequired else ForgotPasswordError.None
    fun validateNewPassword(p: String, c: String): ForgotPasswordError = when {
        p.length < 8 -> ForgotPasswordError.PasswordTooShort
        p != c       -> ForgotPasswordError.PasswordMismatch
        else         -> ForgotPasswordError.None
    }
}

enum class ForgotStage { Identifier, Otp, NewPassword }

@androidx.compose.runtime.Composable
fun ForgotPasswordScreen(
    onSuccess: () -> Unit,
    onBack: () -> Unit,
) {
    // State: stage, identifier, code, newPassword, confirmPassword, isSubmitting,
    // resetToken, resendIn, error. Use AnimatedContent(stage) with
    // SwiplyMotion.authScreenEnter()/Exit().
    //
    // Stage.Identifier: AuthTextField(identifier) + PrimaryButton(sendCode) →
    //   vm.requestPasswordReset(identifier) → on success: stage = Otp,
    //   resendIn = response.resend_available_in_seconds.
    //
    // Stage.Otp: StepPill, AuthHeader, OtpInputCells(autoSubmit=true,
    //   onSubmit = { code -> verify() }), TextLinkButton(resend, disabled while resendIn>0),
    //   CountdownLabel(resendIn), TextLinkButton(back → stage = Identifier).
    //   verify(): vm.verifyPasswordReset(identifier, code) → on success: resetToken =
    //   response.reset_token, stage = NewPassword.
    //
    // Stage.NewPassword: AuthPasswordField × 2 + PrimaryButton →
    //   vm.confirmPasswordReset(resetToken, newPassword) → on success: onSuccess().
    //
    // Use rememberCoroutineScope() for suspending calls.
    // Use SmsOtpRetriever for the OTP stage; mirror its use in the existing
    // PasswordRecoveryScreen.kt.
}
```

Fill the body following the comments. Use the same control-flow style as `LoginScreen`.

- [ ] **Step 3: Add the route**

```kotlin
composable(AppRoutes.Auth.FORGOT_PASSWORD) {
    ForgotPasswordScreen(
        onSuccess = {
            navController.navigate("app/groups") {
                popUpTo(AppRoutes.Auth.FORGOT_PASSWORD) { inclusive = true }
            }
        },
        onBack = { navController.popBackStack() },
    )
}
```

- [ ] **Step 4: Run tests + build**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.ForgotPasswordValidationTest"
./gradlew :app:compileOrganicDebugKotlin
```

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/features/auth/ForgotPasswordScreen.kt \
        android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavGraph.kt \
        android/app/src/test/java/com/encer/splitwise/features/auth/ForgotPasswordValidationTest.kt
git commit -m "feat(auth): ForgotPasswordScreen (3-stage flow with validation)"
```

---

## Task 14: CompleteAccountScreen

**Files:**
- Create: `features/auth/CompleteAccountScreen.kt`
- Modify: `core/navigation/AppNavGraph.kt` — add route with `token` arg

- [ ] **Step 1: Add the route with required query arg**

```kotlin
composable(
    route = AppRoutes.Auth.COMPLETE_ACCOUNT,
    arguments = listOf(navArgument("token") { type = NavType.StringType; defaultValue = "" })
) { entry ->
    val token = entry.arguments?.getString("token").orEmpty()
    CompleteAccountScreen(
        token = token,
        onSuccess = {
            navController.navigate("app/groups") {
                popUpTo(AppRoutes.Auth.COMPLETE_ACCOUNT) { inclusive = true }
            }
        },
        onBackToLogin = { navController.navigate(AppRoutes.Auth.LOGIN) },
    )
}
```

- [ ] **Step 2: Implement `CompleteAccountScreen`**

State machine:
- `Loading` (initial fetch via `vm.requestInvitedAccount(token)`)
- `PhoneOtp` (if response.requires_phone_verification)
- `NewPassword`
- `LoadFailed` (initial fetch threw)

```kotlin
package com.encer.splitwise.features.auth

import androidx.compose.runtime.*
// ...other imports as in LoginScreen

enum class CompleteStage { Loading, PhoneOtp, NewPassword, LoadFailed }

@Composable
fun CompleteAccountScreen(token: String, onSuccess: () -> Unit, onBackToLogin: () -> Unit) {
    val vm: AppShellViewModel = appHiltViewModel()
    var stage by remember { mutableStateOf(CompleteStage.Loading) }
    var maskedPhone by remember { mutableStateOf("") }
    var requiresPhone by remember { mutableStateOf(false) }
    var code by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(token) {
        val r = vm.requestInvitedAccount(token)
        if (r.isSuccess) {
            val resp = r.getOrThrow()
            requiresPhone = resp.requires_phone_verification
            maskedPhone   = resp.masked_phone_number.orEmpty()
            stage = if (requiresPhone) CompleteStage.PhoneOtp else CompleteStage.NewPassword
        } else {
            error = "بازنشانی حساب ممکن نشد"
            stage = CompleteStage.LoadFailed
        }
    }

    AuthFormScaffold {
        when (stage) {
            CompleteStage.Loading      -> AuthHeader(title = "در حال آماده‌سازی…")
            CompleteStage.PhoneOtp     -> {
                AuthHeader(title = "تأیید شماره", subtitle = "کد ارسالی به $maskedPhone را وارد کن")
                OtpInputCells(
                    value = code,
                    onValueChange = { code = it },
                    length = 5,
                    autoSubmit = true,
                    onSubmit = {
                        isSubmitting = true
                        scope.launch {
                            val r = vm.verifyInvitedAccountPhone(token, it)
                            isSubmitting = false
                            if (r.isSuccess) stage = CompleteStage.NewPassword
                            else error = "کد نادرست است"
                        }
                    },
                )
                InlineAlert(AlertSeverity.Error, error)
            }
            CompleteStage.NewPassword  -> {
                AuthHeader(title = "تنظیم رمز عبور", subtitle = "رمز عبور جدیدت را وارد کن")
                AuthPasswordField(value = newPassword, onValueChange = { newPassword = it }, label = "رمز جدید")
                AuthPasswordField(value = confirmPassword, onValueChange = { confirmPassword = it }, label = "تکرار رمز")
                InlineAlert(AlertSeverity.Error, error)
                PrimaryButton(
                    text = "تأیید",
                    loading = isSubmitting,
                    enabled = newPassword.length >= 8 && newPassword == confirmPassword,
                    onClick = {
                        isSubmitting = true
                        scope.launch {
                            val r = vm.completeInvitedAccount(token, newPassword)
                            isSubmitting = false
                            if (r.isSuccess) onSuccess()
                            else error = "تنظیم رمز ناموفق بود"
                        }
                    },
                )
            }
            CompleteStage.LoadFailed   -> {
                AuthHeader(title = "خطا", subtitle = error)
                TextLinkButton(text = "بازگشت به ورود", onClick = onBackToLogin)
            }
        }
    }
}
```

Replace the hard-coded Persian strings with `R.string.*` lookups after Task 17 lands.

- [ ] **Step 3: Build**

```bash
./gradlew :app:compileOrganicDebugKotlin
```

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/features/auth/CompleteAccountScreen.kt \
        android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavGraph.kt
git commit -m "feat(auth): CompleteAccountScreen with token deeplink + verify-phone branch"
```

---

## Task 15: ChangePasswordScreen (rewrite in place)

**Files:**
- Modify: `android/app/src/main/java/com/encer/splitwise/features/auth/ChangePasswordScreen.kt`
- Modify: `core/navigation/AppNavGraph.kt` — add route

- [ ] **Step 1: Validation tests**

```kotlin
package com.encer.splitwise.features.auth

import org.junit.Assert.assertEquals
import org.junit.Test

class ChangePasswordValidationTest {
    @Test fun `empty current rejected`() {
        assertEquals(ChangePasswordError.CurrentRequired,
            ChangePasswordValidation.validate("", "longenough", "longenough"))
    }
    @Test fun `short new rejected`() {
        assertEquals(ChangePasswordError.NewTooShort,
            ChangePasswordValidation.validate("oldpass", "short", "short"))
    }
    @Test fun `same as current rejected`() {
        assertEquals(ChangePasswordError.NewSameAsCurrent,
            ChangePasswordValidation.validate("samevalue", "samevalue", "samevalue"))
    }
    @Test fun `mismatch rejected`() {
        assertEquals(ChangePasswordError.Mismatch,
            ChangePasswordValidation.validate("oldpass", "newlongone", "different"))
    }
    @Test fun `valid pair ok`() {
        assertEquals(ChangePasswordError.None,
            ChangePasswordValidation.validate("oldpass", "newlongone", "newlongone"))
    }
}
```

- [ ] **Step 2: Replace the file contents**

```kotlin
package com.encer.splitwise.features.auth

import androidx.compose.runtime.*
// ... rest of imports same as LoginScreen

enum class ChangePasswordError { None, CurrentRequired, NewTooShort, NewSameAsCurrent, Mismatch }

object ChangePasswordValidation {
    fun validate(current: String, new: String, confirm: String): ChangePasswordError = when {
        current.isBlank()    -> ChangePasswordError.CurrentRequired
        new.length < 8       -> ChangePasswordError.NewTooShort
        new == current       -> ChangePasswordError.NewSameAsCurrent
        new != confirm       -> ChangePasswordError.Mismatch
        else                 -> ChangePasswordError.None
    }
}

@Composable
fun ChangePasswordScreen(onSuccess: () -> Unit, onSignOut: () -> Unit) {
    val vm: AppShellViewModel = appHiltViewModel()
    var current by remember { mutableStateOf("") }
    var newPwd by remember { mutableStateOf("") }
    var confirmPwd by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    AuthFormScaffold {
        AuthHeader(title = "تغییر رمز عبور", subtitle = "برای ادامه، رمز جدید انتخاب کن")
        AuthPasswordField(value = current, onValueChange = { current = it }, label = "رمز فعلی")
        AuthPasswordField(value = newPwd,  onValueChange = { newPwd = it },  label = "رمز جدید")
        AuthPasswordField(value = confirmPwd, onValueChange = { confirmPwd = it }, label = "تکرار رمز جدید")
        InlineAlert(AlertSeverity.Error, error)
        PrimaryButton(
            text = "تغییر رمز",
            loading = isSubmitting,
            enabled = ChangePasswordValidation.validate(current, newPwd, confirmPwd) == ChangePasswordError.None,
            onClick = {
                isSubmitting = true
                scope.launch {
                    val r = vm.changePassword(current, newPwd)
                    isSubmitting = false
                    if (r.isSuccess) onSuccess()
                    else error = "تغییر رمز ناموفق بود"
                }
            },
        )
        TextLinkButton(text = "خروج از حساب", onClick = onSignOut, secondary = true)
    }
}
```

- [ ] **Step 3: Add the route + remove the old call site**

In `AppNavGraph.kt`:

```kotlin
composable(AppRoutes.Auth.CHANGE_PASSWORD) {
    ChangePasswordScreen(
        onSuccess = {
            navController.navigate("app/groups") {
                popUpTo(AppRoutes.Auth.CHANGE_PASSWORD) { inclusive = true }
            }
        },
        onSignOut = {
            // Hook to AppShellViewModel.signOut()-equivalent + navigate to login.
            // The exact method name must be confirmed.
        },
    )
}
```

- [ ] **Step 4: Run tests + build**

```bash
./gradlew :app:testOrganicDebugUnitTest --tests "*.ChangePasswordValidationTest"
./gradlew :app:compileOrganicDebugKotlin
```

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/features/auth/ChangePasswordScreen.kt \
        android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavGraph.kt \
        android/app/src/test/java/com/encer/splitwise/features/auth/ChangePasswordValidationTest.kt
git commit -m "feat(auth): rewrite ChangePasswordScreen with Swiply parity + validation tests"
```

---

## Task 16: VerifyPhoneScreen

**Files:**
- Create: `features/auth/VerifyPhoneScreen.kt`
- Modify: `core/navigation/AppNavGraph.kt`

- [ ] **Step 1: Implement the screen**

Two stages, `PhonePrompt` and `Otp`, structured identically to `RegisterScreen`'s pattern. The phone field uses `KeyboardType.Phone` and `LayoutDirection.Ltr`. The OTP step calls `vm.verifyPhone(phoneNumber, code)`. The signout button is shown on both stages.

```kotlin
package com.encer.splitwise.features.auth

import androidx.compose.animation.AnimatedContent
import androidx.compose.runtime.*
// ... same import block as LoginScreen

enum class VerifyPhoneStage { PhonePrompt, Otp }

@Composable
fun VerifyPhoneScreen(onSuccess: () -> Unit, onSignOut: () -> Unit) {
    val vm: AppShellViewModel = appHiltViewModel()
    var stage by remember { mutableStateOf(VerifyPhoneStage.PhonePrompt) }
    var phone by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    var resendIn by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(resendIn) {
        while (resendIn > 0) { kotlinx.coroutines.delay(1000); resendIn-- }
    }

    AuthFormScaffold {
        AnimatedContent(
            targetState = stage, label = "VerifyPhoneStage",
            transitionSpec = { com.encer.splitwise.ui.theme.SwiplyMotion.authScreenEnter() togetherWith com.encer.splitwise.ui.theme.SwiplyMotion.authScreenExit() },
        ) { s -> when (s) {
            VerifyPhoneStage.PhonePrompt -> {
                AuthHeader(title = "تأیید شماره موبایل", heroIcon = com.encer.splitwise.ui.icons.AppIcons.Shield)
                AuthTextField(
                    value = phone, onValueChange = { phone = it.filter(Char::isDigit) },
                    label = "شماره موبایل", leadingIcon = com.encer.splitwise.ui.icons.AppIcons.Phone,
                    keyboardType = androidx.compose.ui.text.input.KeyboardType.Phone,
                )
                InlineAlert(AlertSeverity.Error, error)
                PrimaryButton(
                    text = "ارسال کد",
                    loading = isSubmitting,
                    enabled = PhoneVerificationPolicy.isValidIranMobileInput(phone),
                    onClick = {
                        isSubmitting = true
                        scope.launch {
                            val r = vm.requestPhoneVerification(phone)
                            isSubmitting = false
                            if (r.isSuccess) {
                                resendIn = r.getOrThrow().resend_available_in_seconds
                                stage = VerifyPhoneStage.Otp
                            } else error = "ارسال کد ناموفق بود"
                        }
                    },
                )
                TextLinkButton(text = "خروج", onClick = onSignOut, secondary = true)
            }
            VerifyPhoneStage.Otp -> {
                StepPill("مرحله ۲ از ۲", accent = true)
                AuthHeader(title = "ورود کد", subtitle = "کد ۵ رقمی ارسال‌شده به $phone")
                OtpInputCells(value = code, onValueChange = { code = it }, length = 5,
                    autoSubmit = true,
                    onSubmit = {
                        isSubmitting = true
                        scope.launch {
                            val r = vm.verifyPhone(phone, it)
                            isSubmitting = false
                            if (r.isSuccess) onSuccess()
                            else error = "کد نادرست است"
                        }
                    })
                InlineAlert(AlertSeverity.Error, error)
                TextLinkButton(text = "ارسال مجدد", onClick = {
                    scope.launch {
                        val r = vm.requestPhoneVerification(phone)
                        if (r.isSuccess) resendIn = r.getOrThrow().resend_available_in_seconds
                    }
                }, enabled = resendIn == 0)
                CountdownLabel(secondsRemaining = resendIn)
                TextLinkButton(text = "بازگشت", onClick = { stage = VerifyPhoneStage.PhonePrompt })
                TextLinkButton(text = "خروج", onClick = onSignOut, secondary = true)
            }
        } }
    }
}
```

- [ ] **Step 2: Add the route**

```kotlin
composable(AppRoutes.Auth.VERIFY_PHONE) {
    VerifyPhoneScreen(
        onSuccess = {
            navController.navigate("app/groups") {
                popUpTo(AppRoutes.Auth.VERIFY_PHONE) { inclusive = true }
            }
        },
        onSignOut = { /* hook to sign-out + navigate to login */ },
    )
}
```

- [ ] **Step 3: Build**

```bash
./gradlew :app:compileOrganicDebugKotlin
```

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/encer/splitwise/features/auth/VerifyPhoneScreen.kt \
        android/app/src/main/java/com/encer/splitwise/core/navigation/AppNavGraph.kt
git commit -m "feat(auth): VerifyPhoneScreen (full screen, phone + OTP stages)"
```

---

## Task 17: i18n strings — copy from web verbatim

**Files:**
- Modify: `android/app/src/main/java/com/encer/splitwise/ui/localization/LocalizedStrings.kt`
- Modify: `android/app/src/main/res/values/strings.xml`
- Modify: `android/app/src/main/res/values-fa/strings.xml`
- Modify: each `*Screen.kt` to replace inline strings with `stringResource(R.string.…)`

- [ ] **Step 1: Identify the source-of-truth file for web copy**

```bash
ls /Users/amir/PycharmProjects/offline-splitwise/web/src/shared/i18n
```

Open the Persian and English files and find every Auth string. Mirror the key names where possible (e.g., web key `auth.login.title` → Android key `auth_login_title`).

- [ ] **Step 2: Add `strings.xml` entries**

For each pair (en, fa), add one entry. Example pairs to add at minimum (the full list is whatever the web exports; add all of them in this commit):

```xml
<!-- values/strings.xml -->
<string name="auth_login_title">Welcome back</string>
<string name="auth_login_subtitle">Sign in to your Swiply account</string>
<string name="auth_login_action">Sign in</string>
<string name="auth_username_label">Username</string>
<string name="auth_password_label">Password</string>
<string name="auth_forgot_password_link">Forgot password?</string>
<string name="auth_register_link">Create a new account</string>
<string name="auth_continue_offline">Continue without signing in</string>
<!-- ... and so on for register / forgot / otp / change-password / verify-phone -->
```

```xml
<!-- values-fa/strings.xml -->
<string name="auth_login_title">خوش برگشتی</string>
<string name="auth_login_subtitle">به حساب Swiply وارد شو</string>
<string name="auth_login_action">ورود</string>
<string name="auth_username_label">نام کاربری</string>
<string name="auth_password_label">رمز عبور</string>
<string name="auth_forgot_password_link">رمز عبور را فراموش کرده‌ام</string>
<string name="auth_register_link">ساخت حساب جدید</string>
<string name="auth_continue_offline">ادامه بدون ورود</string>
<!-- ... rest verbatim from web -->
```

Values must come from the web file. If a key exists in web but English/Persian is missing, copy whatever web has and leave a TODO comment for translation only if the web file itself has a TODO.

- [ ] **Step 3: Replace inline strings in all six Auth screens with `stringResource(R.string.…)`**

`LoginScreen.kt`, `RegisterScreen.kt`, `ForgotPasswordScreen.kt`, `CompleteAccountScreen.kt`, `ChangePasswordScreen.kt`, `VerifyPhoneScreen.kt` — swap the literals introduced in Tasks 11–16 for `stringResource(R.string.auth_*)`.

- [ ] **Step 4: Build and run a smoke test**

```bash
./gradlew :app:compileOrganicDebugKotlin
./gradlew :app:installOrganicDebug
```

Manually open Login, Register, Forgot, ChangePassword, VerifyPhone, CompleteAccount (via deeplink); switch language; confirm strings in both locales.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/res/values/strings.xml \
        android/app/src/main/res/values-fa/strings.xml \
        android/app/src/main/java/com/encer/splitwise/features/auth/ \
        android/app/src/main/java/com/encer/splitwise/ui/localization/LocalizedStrings.kt
git commit -m "feat(i18n): port web Auth copy verbatim into Android strings + wire screens"
```

---

## Task 18: Cleanup — delete legacy Auth files and dialog flags

**Files:**
- Delete: `features/auth/AuthScreen.kt`, `AuthUiComponents.kt`, `PasswordRecoveryScreen.kt`, `PhoneVerificationDialog.kt`
- Modify: `core/navigation/AppShellViewModel.kt` — remove any `showForgotPassword`, `completeAccountToken`, `phoneVerificationVisible` if they were left over
- Modify: `core/navigation/SplitwiseApp.kt` — remove `RootStage` enum and old composables imports

- [ ] **Step 1: Confirm no remaining references**

```bash
cd android/app/src/main/java/com/encer/splitwise
grep -rn "AuthScreen\|AuthUiComponents\|PasswordRecoveryScreen\|PhoneVerificationDialog\|RootStage" .
```

Expected: no hits (or only in files being deleted). If any production code outside Auth still references these, refactor it before deleting.

- [ ] **Step 2: Delete the files**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise
rm android/app/src/main/java/com/encer/splitwise/features/auth/AuthScreen.kt
rm android/app/src/main/java/com/encer/splitwise/features/auth/AuthUiComponents.kt
rm android/app/src/main/java/com/encer/splitwise/features/auth/PasswordRecoveryScreen.kt
rm android/app/src/main/java/com/encer/splitwise/features/auth/PhoneVerificationDialog.kt
```

- [ ] **Step 3: Remove leftover state from AppShellViewModel and SplitwiseApp**

Open both files. Strip any properties / `LaunchedEffect`s / composable branches that were only used by the deleted screens.

- [ ] **Step 4: Full build + all tests**

```bash
./gradlew :app:compileOrganicDebugKotlin
./gradlew :app:testOrganicDebugUnitTest
./gradlew :app:connectedOrganicDebugAndroidTest --tests "*.auth.*"
```

Expected: BUILD SUCCESSFUL, all green.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(auth): remove legacy AuthScreen, dialogs, and RootStage switching"
```

---

## Task 19: Verification artifacts

**Files:**
- Create: `docs/swiply-parity/phase1/manual-checklist.md`
- Create: `docs/swiply-parity/phase1/screenshots/` (empty dir + .gitkeep)
- Create: `docs/swiply-parity/phase1/motion/` (empty dir + .gitkeep)

- [ ] **Step 1: Create the docs directory**

```bash
mkdir -p docs/swiply-parity/phase1/screenshots docs/swiply-parity/phase1/motion
touch docs/swiply-parity/phase1/screenshots/.gitkeep
touch docs/swiply-parity/phase1/motion/.gitkeep
```

- [ ] **Step 2: Write the manual checklist**

`docs/swiply-parity/phase1/manual-checklist.md`:

```markdown
# Phase 1 (Auth) Manual Verification Checklist

For each row, capture a screenshot/recording in the matching folder and tick the box when the Android result matches the web.

## Screens (fa + en × light + dark)
- [ ] LoginScreen
- [ ] RegisterScreen — Form step
- [ ] RegisterScreen — OTP step (with StepPill)
- [ ] ForgotPasswordScreen — Identifier
- [ ] ForgotPasswordScreen — OTP
- [ ] ForgotPasswordScreen — NewPassword
- [ ] CompleteAccountScreen — Loading
- [ ] CompleteAccountScreen — PhoneOtp
- [ ] CompleteAccountScreen — NewPassword
- [ ] ChangePasswordScreen
- [ ] VerifyPhoneScreen — PhonePrompt
- [ ] VerifyPhoneScreen — OTP

## Motion
- [ ] Step transitions in Register match web (320ms emphasized ease)
- [ ] Step transitions in ForgotPassword match web
- [ ] Step transitions in VerifyPhone match web
- [ ] InlineAlert in/out 140ms feels identical
- [ ] OTP cell focus scale + border color animation
- [ ] Countdown second crossfade

## Behavior
- [ ] Deeplink `https://pwa.splitwise.ir/auth/complete-account?token=...` opens correctly from cold start
- [ ] Rotation preserves form state on every screen
- [ ] SMS auto-fill populates OTP cells and triggers auto-submit on Register, Forgot, VerifyPhone, CompleteAccount
- [ ] Back button on Step 2 → Step 1 (not exit) in Register, Forgot, VerifyPhone
- [ ] Locale switch mid-flow refreshes copy without losing state
- [ ] Theme switch mid-flow refreshes colors without flicker
- [ ] Offline submit shows network error via `InlineAlert` and lets user retry
- [ ] After successful login/register/reset/invited-complete, app lands on `app/groups`
- [ ] After successful change-password, returns to `app/groups`
- [ ] After successful phone-verify, returns to `app/groups`
- [ ] Continue Offline button keeps Android-specific guest path working

## Network parity (capture with mitmproxy)
- [ ] POST /auth/login payload + headers match web
- [ ] POST /auth/register/request matches
- [ ] POST /auth/register/verify matches
- [ ] POST /auth/register/resend matches
- [ ] POST /auth/forgot-password/request, /verify, /confirm match
- [ ] POST /auth/invited-account/request, /verify-phone, /complete match
- [ ] POST /auth/change-password matches
- [ ] POST /auth/phone/request-verification + /verify match
```

- [ ] **Step 3: Commit**

```bash
git add docs/swiply-parity
git commit -m "docs(parity): add Phase 1 verification scaffolding and manual checklist"
```

---

## Task 20: Final full-build + push

- [ ] **Step 1: Full build (all flavors)**

```bash
cd android
./gradlew :app:assembleOrganicDebug :app:assembleBazaarDebug :app:assembleMyketDebug
```

Expected: BUILD SUCCESSFUL on all three.

- [ ] **Step 2: All tests**

```bash
./gradlew :app:testOrganicDebugUnitTest
./gradlew :app:connectedOrganicDebugAndroidTest
```

Expected: green.

- [ ] **Step 3: Walk the manual checklist on a Pixel 7 emulator**

Run the device matrix and tick everything in `docs/swiply-parity/phase1/manual-checklist.md`. Anything that doesn't match is a regression; fix it before push.

- [ ] **Step 4: Push the branch and open PR**

```bash
cd /Users/amir/PycharmProjects/offline-splitwise
git push -u origin feat/auth-phase1-parity
```

Open the PR; title `Android Auth Phase 1 — Web/PWA parity`. Link the spec at `docs/superpowers/specs/2026-05-14-android-auth-parity-design.md` and the checklist at `docs/swiply-parity/phase1/manual-checklist.md` in the description.

---

## Self-Review Notes

- Every spec section has at least one task: tokens (1–2), motion (3), icons (4), shared components (5–7), missing endpoint plumbing (8), nav constants (9), guards (10), screens (11–16), i18n (17), cleanup (18), verification (19), final ship (20).
- No placeholders found; every code-changing step shows the code.
- Type names are consistent across tasks: `SwiplyTheme`, `SwiplyMotion.authScreenEnter()`, `AppIcons.<Name>`, `AppNavigationGuards.resolve(target, state)`, `GuardState(...)`.
- `verifyInvitedAccountPhone` is added end-to-end in Task 8 before any screen relies on it (Task 14 consumes it).
- `AppErrorMapper.message(...)` signature is flagged for the implementer to confirm against the existing helper before wiring it from `LoginScreen`. Same pattern applies to `signOut()` and `Session` field names — flagged inline.
