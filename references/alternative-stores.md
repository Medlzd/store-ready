# Alternative stores and distribution

Worth reading when the user targets markets where Google Play is absent or weak, or
wants EU alternative distribution.

## Huawei AppGallery
- Google Play Services are unavailable. Replace GMS dependencies with HMS
  equivalents (Push Kit, Map Kit, Location Kit, Account Kit) or use a fallback
  abstraction that degrades gracefully.
- Firebase features that depend on GMS (FCM, some Analytics paths) will not work.
- Submits an **APK**, not an AAB.
- Review includes an installation and functional test; a build that silently fails
  its push registration is rejected.
- Strong in China, MENA, parts of Europe, Latin America.

## Samsung Galaxy Store
- APK, targets Samsung devices, lighter review than Play.
- Useful for reaching users who avoid Play, and for Galaxy-specific features.

## Amazon Appstore
- APK; Amazon device compatibility (Fire tablets) matters most.
- Uses its own IAP API — Play Billing calls must be abstracted behind an interface.

## F-Droid
- Fully open-source apps only; builds are reproduced from source by F-Droid.
- No proprietary dependencies, no tracking libraries, no GMS.
- Requires a build recipe in the F-Droid metadata repository.

## Direct APK / enterprise distribution
- Android: signed APK plus a clear install path; expect `REQUEST_INSTALL_PACKAGES`
  friction and Play Protect warnings for unknown signers.
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
