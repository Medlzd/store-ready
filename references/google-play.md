# Google Play — audit reference

> ⏱ marks values on Google's annual cadence. Around **31 August**, new apps and app
> updates must target the new API level or the upload is blocked. The later date,
> around **1 November**, is *not* an automatic grace period — it is an extension you
> must request through a form in Play Console, and the August date binds until you
> do. Fetch both current dates and the required API level before stating either:
> `https://support.google.com/googleplay/android-developer/answer/11926878`

## Contents
1. Account prerequisites
2. Build and packaging requirements
3. Manifest audit
4. Play Console declarations
5. Testing requirements before production
6. Policy areas that cause suspensions
7. Release strategy

---

## 1. Account prerequisites

- Google Play Developer account, one-time registration fee, identity verified.
- **Personal accounts created on or after 13 November 2023** must run a closed test
  with **at least 12 testers, each opted in continuously for at least 14 days**,
  before applying for production access. These are exact minimums, not estimates:
  a tester who opts out and back in must accumulate 14 *consecutive* days to count.
  Organization accounts are exempt. This is a calendar gate no code fix shortens —
  put it in the timeline before anything else.
  (`https://support.google.com/googleplay/android-developer/answer/14151465`)
- **Play app registration / Android developer verification.** Every package must be
  registered to a verified developer. Google auto-registered about 99% of existing
  apps — check Play Console Home for any that were not; unregistered apps face
  removal. ⏱ The enforcement calendar is regional and moving: certified Android
  devices in Brazil, Indonesia, Singapore and Thailand from 30 September 2026,
  wider rollout from 2027. Confirm the current dates for your markets.
  (`https://developer.android.com/developer-verification`)
- Organization accounts need a verifiable D-U-N-S number.
- Verified contact address and phone; unverified accounts get apps blocked.
- EU trader status declaration, same as Apple: publicly displayed contact details.
- Payments profile completed if the app is paid or has IAP.

## 2. Build and packaging requirements

- **Android App Bundle (`.aab`)** is mandatory for new apps. APKs are only for
  sideloading and alternative stores.
- ⏱ **Target API level**: new apps and updates must target the required level.
  Set `targetSdk` in `android/app/build.gradle` (or `build.gradle.kts`).
- ⏱ **16 KB memory page size support**: apps with native code (`.so` libraries)
  targeting recent Android versions must be built with 16 KB-aligned ELF segments.
  This affects Flutter, React Native, Unity, and anything using NDK libraries —
  update the NDK/AGP and rebuild, then verify alignment on the extracted libs.
- 64-bit native libraries are required alongside 32-bit; 64-bit-only is acceptable.
- App signing: use **Play App Signing**. Keep the upload key backed up — losing it
  is recoverable through Google support only if Play App Signing is enabled.
  Losing the app signing key without Play App Signing is unrecoverable and forces
  a new listing under a new package name.
- `applicationId` is permanent. Verify it before the first upload, not after.
- `versionCode` must strictly increase across every uploaded bundle.
- Check the download size and the `resizeableActivity` / large-screen behaviour;
  Play now surfaces large-screen quality warnings on the listing.

## 3. Manifest audit

Read `android/app/src/main/AndroidManifest.xml` plus any library manifests merged in
(`./gradlew :app:processReleaseManifest` then inspect the merged output — permissions
are frequently injected by SDKs without the developer knowing).

High-scrutiny permissions, each needing an in-console declaration form:

| Permission | Requirement |
|---|---|
| `QUERY_ALL_PACKAGES` | Declaration; almost always refused — use `<queries>` instead |
| `MANAGE_EXTERNAL_STORAGE` | Declaration + demo video; use scoped storage or SAF instead |
| `SYSTEM_ALERT_WINDOW` | Justification |
| `REQUEST_INSTALL_PACKAGES` | Declaration |
| `ACCESS_BACKGROUND_LOCATION` | Declaration + video showing the background use |
| `READ_SMS` / `RECEIVE_SMS` / call log | Restricted to default handlers; OTP autofill must use the SMS Retriever API |
| `USE_FULL_SCREEN_INTENT` | Only for calls/alarms |
| `FOREGROUND_SERVICE_*` | Each foreground service needs a declared type matching real use |
| `POST_NOTIFICATIONS` | Runtime request required on Android 13+ |
| `SCHEDULE_EXACT_ALARM` | Restricted; use inexact alarms unless it's a real alarm/calendar app |
| `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` | Only when the Android photo picker cannot deliver core functionality, and only with an approved declaration. A custom picker does not qualify on its own. One-time or occasional access must migrate to `PickVisualMedia`. Full enforcement since 28 May 2025 — non-compliant apps are removed. If the permission arrives from a dependency's merged manifest, strip it with `tools:node="remove"` rather than declaring it |

Also verify:
- `android:exported` set explicitly on every activity, service and receiver with an
  intent filter (build fails on Android 12+ otherwise, but merged library components
  can slip through).
- No `android:debuggable="true"`, no `usesCleartextTraffic` unless justified with a
  network security config.
- Deep links: `android:autoVerify="true"` with a live `assetlinks.json`.
- Advertising ID permission declared if any SDK uses it (`AD_ID`).

## 4. Play Console declarations

- **Data safety form** — the single most audited item. It must match what the app
  and its SDKs actually do. Enumerate every dependency's data practices; ad,
  analytics, crash-reporting and attribution SDKs all collect something.
- Privacy policy URL — mandatory, reachable, specific to this app.
- **Account deletion**: if the app supports account creation, provide an in-app
  deletion path **and** a publicly reachable web URL for deletion requests.
- **Health apps declaration** — required on the App content page for **every** app,
  including apps with no health features at all, which must certify that none are
  offered. It also applies to apps only on closed or open testing. An incomplete
  form blocks submitting any change for review, which is why it surfaces as a
  mysterious "you must complete the Health declaration" error rather than as a
  policy rejection. Apps reading or writing Health Connect data must justify each
  data type, and high-sensitivity types carry extra rules.
  (`https://support.google.com/googleplay/android-developer/answer/14738291`)
- **AI-generated content** — apps that generate content with AI need in-app
  reporting or flagging of offensive output, without leaving the app, plus a
  declaration in Play Console and labelling where required.
  (`https://support.google.com/googleplay/android-developer/answer/14094294`)
- Content rating questionnaire (IARC) — answer honestly; a mismatch discovered later
  triggers removal, not a warning.
- Target audience and content: declaring any child audience pulls the app into
  Families policy, with stricter SDK, ads and data rules.
- Ads declaration; news, finance, health, gambling, VPN, or accessibility-API use each
  have their own declaration and often require documentation.
- Government/health/finance apps may need proof of licensing in each country —
  relevant for fintech, where the licence document is usually requested.
- App access instructions: credentials for any gated area, otherwise the reviewer
  sees a login screen and rejects.

## 5. Testing requirements before production

- Internal testing: up to 100 testers, instant, no review — use it for CI builds.
- Closed testing: required for the tester-count rule above; also the safest place to
  catch install-time failures on real devices.
- Open testing: public but flagged as a test.
- Pre-launch report: run it and read it. It catches crashes on device configurations
  you don't own, plus accessibility and security warnings, before a human reviewer does.

## 6. Policy areas that cause suspensions

Suspensions are harsher than rejections — repeated ones terminate the account.

- **Deceptive behaviour**: functionality that differs from the description, hidden
  features, or an app that changes behaviour after review.
- **Device and network abuse**: self-updating code, downloading executable code at
  runtime (this includes some dynamic-delivery misuse and JS bundle patterns —
  interpreted code is allowed, native code download is not).
- **Permissions and sensitive data**: collecting more than declared.
- **Impersonation**: icons, names or listings resembling another brand.
- **User-generated content**: needs reporting, blocking and moderation, plus a stated
  moderation policy, or the app is removed.
- **Financial services**: personal-loan apps face strict rules on contact/photo access
  and APR disclosure; several countries require licence proof.
- **Repackaging / low-value apps**: thin webview wrappers around a website.

## 7. Release strategy

- Use **staged rollout** (5% → 20% → 50% → 100%) and watch the vitals dashboard.
  Halt rollout is instant; a full rollout with a crash is not.
- Watch ANR and crash rate against the bad-behaviour thresholds — exceeding them
  demotes the app in Play search well before anyone files a complaint.
- Keep the previous bundle available: you cannot un-publish a version, only roll
  forward with a higher `versionCode`.
- Review times vary from hours to a week; first submissions and account-verification
  events take longest. Never schedule a marketing launch on an unapproved build.
