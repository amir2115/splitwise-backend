# مستند فیچرهای پروژه اندروید Offline Splitwise

## منبع این داکیومنت
- `agent.md` در ریشه پروژه خوانده شد.
- فایل `claude.md` در این ورک‌اسپیس پیدا نشد.
- این داکیومنت بر اساس سورس واقعی اندروید در `android/` تهیه شده، نه صرفاً README.

## خلاصه محصول
این اپ یک Splitwise آفلاین-اول است. کاربر می‌تواند بدون لاگین گروه، عضو، خرج و تسویه ثبت کند و بعد از ورود، داده‌ها را با بک‌اند سینک کند. UI با Jetpack Compose نوشته شده و لایه داده از Room، Retrofit و Hilt استفاده می‌کند.

## استک و تنظیمات مهم
- زبان و UI: Kotlin + Jetpack Compose
- ذخیره‌سازی محلی: Room
- شبکه: Retrofit/OkHttp
- DI: Hilt
- همگام‌سازی: `SyncCoordinator`
- حداقل SDK: 24
- `targetSdk`: 36
- Flavors توزیع: `bazaar`, `myket`, `organic`
- آدرس API از `BuildConfig.API_BASE_URL`
- لینک استور پیش‌فرض از `BuildConfig.DEFAULT_STORE_URL`
- زبان‌های فعال UI: فارسی و انگلیسی
- تم‌های فعال: روشن و تیره

## نقشه ناوبری
مسیرهای اصلی در `android/app/src/main/java/com/encer/splitwise/core/navigation/AppRoutes.kt` تعریف شده‌اند:
- `groups`
- `settings`
- `group/{groupId}`
- `members/{groupId}`
- `expense/{groupId}?expenseId={expenseId}`
- `settlement/{groupId}?settlementId={settlementId}&fromMemberId={fromMemberId}&toMemberId={toMemberId}&amount={amount}`
- `balances/{groupId}`
- `expenseDetail/{groupId}/{expenseId}`

## فیچرها

### 1. احراز هویت و ورود آفلاین
فایل‌های اصلی:
- `features/auth/AuthScreen.kt`
- `data/sync/SyncCoordinator.kt`
- `data/remote/network/ApiClient.kt`
- `data/preferences/SessionRepository.kt`

قابلیت‌ها:
- لاگین با `username/password`
- ثبت‌نام با `name/username/password`
- امکان ورود به حالت مهمان با `Continue Offline`
- نمایش خطای کاربرپسند برای خطاهای لاگین/ثبت‌نام
- نگهداری امن توکن‌ها در SharedPreferences رمزگذاری‌شده با Android Keystore
- Refresh خودکار توکن هنگام `401`

رفتار مهم:
- اگر کاربر مهمان باشد، می‌تواند با داده محلی کار کند ولی سینک فعال نیست.
- اگر کاربر عوض شود، داده محلی برای جلوگیری از تداخل مالکیت پاک می‌شود.

### 2. مدیریت گروه‌ها
فایل‌های اصلی:
- `features/groups/GroupsScreen.kt`
- `features/groups/GroupsViewModel.kt`
- `data/repository/DefaultGroupRepository.kt`

قابلیت‌ها:
- ساخت گروه جدید
- ویرایش نام گروه
- حذف گروه
- خروج از گروه در حالت لاگین
- جست‌وجوی گروه وقتی تعداد گروه‌ها زیاد شود
- Pull to refresh برای همگام‌سازی

رفتار مهم:
- لیست گروه‌ها از Room مشاهده می‌شود و UI واکنشی است.
- ریفرش فقط وقتی سشن معتبر وجود داشته باشد فعال است.

### 3. دعوت به گروه
فایل‌های اصلی:
- `features/groups/GroupsScreen.kt`
- `features/groups/GroupsViewModel.kt`
- `data/remote/api/GroupInvitesApi.kt`

قابلیت‌ها:
- نمایش دعوت‌های دریافتی
- قبول دعوت
- رد دعوت
- ریفرش دعوت‌ها بعد از تغییر سشن یا اجرای سینک

رفتار مهم:
- دعوت‌ها فقط برای کاربر لاگین‌شده معنا دارند.
- بعد از قبول دعوت، سینک اجباری اجرا می‌شود تا داده گروه وارد دستگاه شود.

### 4. داشبورد گروه
فایل‌های اصلی:
- `features/group_dashboard/GroupDashboardScreen.kt`
- `features/group_dashboard/GroupDashboardViewModel.kt`
- `domain/usecase/ObserveGroupSummaryUseCase.kt`

قابلیت‌ها:
- نمایش خلاصه گروه
- نمایش تعداد اعضا
- نمایش مجموع هزینه‌ها
- نمایش مجموع تسویه‌ها
- نمایش تعداد بالانس‌های باز
- اکشن‌های سریع برای:
  - اعضا
  - خرج جدید
  - تسویه جدید
  - مشاهده بالانس‌ها
- نمایش آخرین خرج‌ها
- نمایش آخرین تسویه‌ها
- Pull to refresh

رفتار مهم:
- اگر گروه فقط یک عضو داشته باشد، ساخت خرج و تسویه غیرفعال می‌شود.
- پیام راهنما برای نیاز به عضو دوم نمایش داده می‌شود.

### 5. مدیریت اعضا
فایل‌های اصلی:
- `features/members/MembersScreen.kt`
- `features/members/MembersViewModel.kt`
- `data/repository/DefaultMemberRepository.kt`
- `data/remote/network/ApiClient.kt`

قابلیت‌ها:
- افزودن عضو جدید با نام کاربری
- ویرایش عضو
- حذف عضو
- اطمینان از وجود self member برای کاربر جاری در هر گروه
- نمایش اعضایی که نام کاربری معتبر سمت سرور ندارند

رفتار مهم:
- یوزرنیم هنگام ویرایش trim و lowercase می‌شود.
- در حالت سینک، اگر یوزرنیم عضو در بک‌اند وجود نداشته باشد، `invalidMemberUsernames` تولید می‌شود.
- این موضوع یعنی مدل عضو هم نقش محلی دارد هم نقش bridge به کاربر سروری.

### 6. کارت بانکی گروه
فایل‌های اصلی:
- `features/group_dashboard/GroupCardsSection.kt`
- `features/group_dashboard/GroupDashboardViewModel.kt`
- `data/remote/api/GroupCardsApi.kt`

قابلیت‌ها:
- نمایش کارت‌های بانکی گروه
- ثبت کارت جدید برای یک عضو
- ویرایش کارت
- حذف کارت
- کپی شماره کارت

رفتار مهم:
- این بخش فعلاً مستقیم از API می‌آید، نه از Room.
- بعد از سینک یا تغییر سشن دوباره از سرور لود می‌شود.
- مدیریت خطا و snackbar جداگانه دارد.

### 7. ثبت و ویرایش خرج
فایل‌های اصلی:
- `features/expense_editor/ExpenseEditorScreen.kt`
- `features/expense_editor/ExpenseEditorViewModel.kt`
- `features/expense_editor/ExpenseEditorCalculations.kt`
- `domain/usecase/ValidateExpenseInputUseCase.kt`

قابلیت‌ها:
- ایجاد خرج جدید
- ویرایش خرج موجود
- حذف خرج
- ثبت عنوان، توضیح و مبلغ
- انتخاب نوع تقسیم:
  - `EQUAL`
  - `EXACT`
- تعریف payerها
- تعریف shareها
- پیشنهاد خودکار مبلغ باقی‌مانده payer/share
- امکان assign full amount به یک payer
- محاسبه زنده جمع پرداخت و سهم
- جلوگیری از save با mismatch

قابلیت‌های پیشرفته:
- فعال‌کردن مالیات درصدی
- افزودن service chargeهای متعدد
- تخصیص service charge به اعضای منتخب
- پیش‌نمایش سهم پایه، سهم مالیات، سهم service charge و سهم نهایی هر عضو

رفتار مهم:
- اگر مالیات یا service charge فعال باشد، نوع split ذخیره‌شده عملاً `EXACT` می‌شود.
- metadata مالیات/service charge هنوز persisted نمی‌شود؛ فقط اثر نهایی آن روی shareها ذخیره می‌شود.
- اعداد فارسی هم در ورودی مبلغ پشتیبانی می‌شوند.

### 8. جزئیات خرج
فایل‌های اصلی:
- `features/expense_details/ExpenseDetailScreen.kt`
- `features/expense_details/ExpenseDetailsViewModel.kt`

قابلیت‌ها:
- مشاهده جزئیات خرج
- نمایش payers و shares با اعضای متناظر
- حذف خرج از صفحه جزئیات

### 9. ثبت و ویرایش تسویه
فایل‌های اصلی:
- `features/settlement_editor/SettlementEditorScreen.kt`
- `features/settlement_editor/SettlementEditorViewModel.kt`
- `domain/usecase/SimplifyDebtsUseCase.kt`

قابلیت‌ها:
- ایجاد تسویه جدید
- ویرایش تسویه
- حذف تسویه
- انتخاب بدهکار و بستانکار
- ورود مبلغ و توضیح
- پیشنهاد خودکار pair مناسب برای تسویه
- پیشنهاد خودکار مبلغ تسویه بر اساس ساده‌سازی بدهی‌ها

رفتار مهم:
- دو عضو نمی‌توانند یکسان باشند.
- اگر زوج مناسب از بالانس‌ها پیدا شود، فرم به‌صورت هوشمند prefill می‌شود.
- اگر مبلغ دستی وارد نشده باشد، suggested amount به کاربر کمک می‌کند سریع‌تر تسویه ثبت کند.

### 10. بالانس‌ها و ساده‌سازی بدهی
فایل‌های اصلی:
- `features/balances/BalancesScreen.kt`
- `features/balances/BalancesViewModel.kt`
- `domain/usecase/ObserveGroupBalancesUseCase.kt`
- `domain/usecase/SimplifyDebtsUseCase.kt`
- `domain/usecase/BalanceCalculator.kt`

قابلیت‌ها:
- نمایش paid/owed/net برای هر عضو
- نمایش simplified transfers
- استفاده از محاسبه دامنه‌ای جدا از UI

رفتار مهم:
- بالانس‌ها بر اساس خرج‌ها و تسویه‌ها محاسبه می‌شوند.
- تسویه‌پیشنهادی در ادیتور تسویه از همین منطق استفاده می‌کند.

### 11. تنظیمات اپ
فایل‌های اصلی:
- `features/settings/SettingsScreen.kt`
- `data/preferences/SettingsRepository.kt`
- `core/navigation/AppShellViewModel.kt`

قابلیت‌ها:
- نمایش وضعیت حساب
- ورود یا خروج از حساب
- اجرای دستی Sync
- نمایش آخرین زمان Sync
- نمایش وضعیت online/offline و reachability API
- تغییر زبان
- تغییر تم

رفتار مهم:
- اگر کاربر لاگین نباشد، دکمه Sync به Sign In تبدیل می‌شود.
- تشخیص مشکل اتصال و مشکل سرور از هم تفکیک شده است.

### 12. همگام‌سازی آفلاین-اول
فایل‌های اصلی:
- `data/sync/SyncCoordinator.kt`
- `data/local/dao/*`
- `data/remote/model/RemoteModels.kt`
- `data/remote/mapper/*`

قابلیت‌ها:
- نگهداری داده‌ها در Room
- import اولیه داده محلی بعد از اولین لاگین
- incremental sync
- ارسال تغییرات pending به سرور
- دریافت تغییرات جدید از سرور
- tombstone برای حذف‌ها
- ذخیره `lastSyncedAt`
- اجرای sync دستی
- اجرای sync بعد از برخی عملیات مثل قبول دعوت

رفتار مهم:
- اگر `lastSyncedAt == null` و داده محلی موجود باشد، ابتدا import اولیه تلاش می‌شود.
- اگر import اولیه به خاطر وضعیت سرور مجاز نباشد، fallback به incremental sync انجام می‌شود.
- روی خطاهای `invalid_member_usernames` جزئیات از payload سرور parse می‌شود.

### 13. مانیتورینگ شبکه و سلامت API
فایل‌های اصلی:
- `data/sync/NetworkMonitor.kt`
- `data/preferences/HealthStatusRepository.kt`
- `data/remote/api/HealthApi.kt`

قابلیت‌ها:
- تشخیص وجود اینترنت
- تشخیص reachability API
- ثبت آخرین health موفق یا ناموفق
- استفاده از این وضعیت‌ها در صفحه Settings و سیاست آپدیت

### 14. آپدیت اپ
فایل‌های اصلی:
- `data/update/AppUpdateChecker.kt`
- `features/settings/SettingsScreen.kt`
- `core/navigation/SplitwiseApp.kt`

قابلیت‌ها:
- دریافت policy آپدیت از health endpoint
- تشخیص:
  - `NONE`
  - `SOFT`
  - `HARD`
- نمایش دیالوگ آپدیت
- هدایت به URL استور یا دانلود

رفتار مهم:
- در `SOFT` کاربر می‌تواند دیالوگ را dismiss کند.
- در `HARD` dismiss وجود ندارد.
- fallback لینک استور از flavor جاری گرفته می‌شود.

### 15. بومی‌سازی و UX
فایل‌های اصلی:
- `ui/localization/Localization.kt`
- `ui/theme/*`
- `ui/components/*`

قابلیت‌ها:
- پشتیبانی فارسی و انگلیسی
- تغییر LayoutDirection برای فارسی به RTL
- تم روشن و تیره
- کامپوننت‌های reusable
- انیمیشن‌های ورودی و section transitions
- فرمت مبلغ و تاریخ برای نمایش

## مدل داده و مفاهیم دامنه
مفاهیم اصلی موجود در لایه domain:
- `Group`
- `Member`
- `Expense`
- `ExpenseShare`
- `Settlement`
- `GroupCard`
- `GroupInvite`
- `MemberBalance`
- `GroupSummary`

## امکاناتی که به‌صورت مشخص در سورس دیده می‌شوند
- guest mode
- secure token storage
- token refresh
- offline create/update/delete
- initial import after auth
- incremental sync
- group invites
- group cards
- equal/exact split
- tax and service charge in expense editor
- debt simplification
- Persian digit amount entry
- RTL support
- soft/hard app update policy
- store-channel flavors

## محدودیت‌ها و نکات مهم فعلی
- Group cardها فعلاً local cache مجزا در Room ندارند و بیشتر API-driven هستند.
- metadata مالیات و service charge در مدل persisted نشده؛ خروجی نهایی shareها ذخیره می‌شود.
- `localeFilters` فقط `fa` را در Gradle محدود کرده، ولی خود اپ strings انگلیسی هم دارد؛ برای انتشار باید این تصمیم با QA بررسی شود.
- طبق کد، Sync برای کاربران مهمان غیرفعال است و فقط بعد از auth قابل استفاده است.

## فایل‌های مرجع اصلی برای توسعه
- `android/app/build.gradle.kts`
- `android/app/src/main/java/com/encer/splitwise/core/navigation/SplitwiseApp.kt`
- `android/app/src/main/java/com/encer/splitwise/data/sync/SyncCoordinator.kt`
- `android/app/src/main/java/com/encer/splitwise/features/groups/GroupsViewModel.kt`
- `android/app/src/main/java/com/encer/splitwise/features/group_dashboard/GroupDashboardViewModel.kt`
- `android/app/src/main/java/com/encer/splitwise/features/expense_editor/ExpenseEditorViewModel.kt`
- `android/app/src/main/java/com/encer/splitwise/features/settlement_editor/SettlementEditorViewModel.kt`

## جمع‌بندی
اپ اندروید این پروژه فقط یک CRUD ساده خرج نیست. در وضعیت فعلی این قابلیت‌های محصولی را واقعاً دارد:
- مدیریت گروه و عضو
- دعوت و عضویت گروهی
- ثبت خرج با split پیشرفته
- ثبت تسویه
- محاسبه بالانس و ساده‌سازی بدهی
- کار آفلاین کامل
- سینک بعد از احراز هویت
- مدیریت کارت بانکی گروه
- تنظیمات زبان/تم
- سیاست آپدیت نرم/سخت

اگر بخواهی، قدم بعدی را هم می‌توانم انجام بدهم:
- این داکیومنت را به نسخه PRD/Product Spec تبدیل کنم
- فیچرها را به صورت چک‌لیست تست QA دربیاورم
- یا ماژول‌به‌ماژول debt فنی و جاهای ناقص پروژه اندروید را هم استخراج کنم
