# Alternative stores and distribution

Worth reading when the user targets markets where Google Play is absent or weak, or
wants EU alternative distribution.

## Huawei AppGallery
- Google Play Services are unavailable. Replace GMS dependencies with HMS
  equivalents (Push Kit, Map Kit, Location Kit, Account Kit) or use a fallback
  abstraction that degrades gracefully.
- Firebase features that depend on GMS (FCM, some Analytics paths) will not work.
- **Check the HarmonyOS generation before you budget anything.** HarmonyOS 4 and
  EMUI still run Android APKs on the ART runtime, so a port is a build flavour.
  HarmonyOS 5 / NEXT dropped the AOSP compatibility layer entirely — no ART, no
  Java SDK, APKs do not install. It takes a HAP package rebuilt in DevEco Studio
  with ArkTS/ArkUI (or the C/C++ NDK, or Cangjie). Scope that as a rewrite, not a
  flavour, and qualify "strong in China" accordingly.
- Review includes an installation and functional test; a build that silently fails
  its push registration is rejected.
- Strong in China, MENA, parts of Europe, Latin America.

## Samsung Galaxy Store
- APK, targets Samsung devices, lighter review than Play.
- Useful for reaching users who avoid Play, and for Galaxy-specific features.

## Amazon Appstore — Fire OS only
- **Not a route to Android phones.** Amazon stopped accepting new submissions
  targeting Android devices on 20 February 2025 and shut the Android storefront on
  20 August 2025. Only Fire tablets and Fire TV remain.
  (`https://developer.amazon.com/apps-and-games/blogs/2025/02/upcoming-changes-to-amazon-appstore-for-android-devices-and-coins-program`)
- APK; target Fire OS device compatibility, not general Android.
- Uses its own IAP API — Play Billing calls must be abstracted behind an interface.
- Worth it only if Fire tablets or Fire TV are a real market for the app. Otherwise
  it is engineering effort for a channel that no longer reaches phone users.

## F-Droid
- Fully open-source apps only; builds are reproduced from source by F-Droid.
- No proprietary dependencies, no tracking libraries, no GMS.
- Requires a build recipe in the F-Droid metadata repository.

## Direct APK / enterprise distribution
- Android: signed APK plus a clear install path; expect `REQUEST_INSTALL_PACKAGES`
  friction and Play Protect warnings for unknown signers.
- ⏱ **Developer verification reaches sideloading too.** On certified Android
  devices (Android 7+), apps from unverified developers stop installing through the
  normal flow — Brazil, Indonesia, Singapore and Thailand from 30 September 2026,
  wider rollout from 2027, with an advanced flow for power users. Distributing
  outside Play no longer means distributing without registering. Verify the current
  dates for your markets. (`https://developer.android.com/developer-verification`)
- iOS: Ad Hoc (device UDIDs, limited count), Enterprise programme (internal use only,
  strictly enforced), or the EU alternative-distribution routes.

## EU alternative distribution (iOS)
- Requires notarization by Apple and specific entitlements; terms, fees and
  eligibility have changed repeatedly since introduction.
- Verify the current terms directly with Apple before committing engineering time —
  this area moves faster than any other in this document.

## Practical architecture advice
If more than one store is on the roadmap, isolate store-specific code behind
interfaces from day one:
- `PushService` → FCM / HMS Push / APNs
- `BillingService` → StoreKit / Play Billing / Amazon IAP / Huawei IAP
- `MapService`, `AnalyticsService`, `AuthService` likewise

Use build flavours (Android) and schemes/configurations (iOS) rather than runtime
branching, so each store's binary contains only the SDKs it needs — which also keeps
the privacy declarations per-store honest.
