# Apple App Store — audit reference

> Values marked ⏱ change on Apple's annual cadence. Fetch the current value from
> `developer.apple.com/news/upcoming-requirements/` before stating it.

## Contents
1. Account and legal prerequisites
2. Build requirements
3. Info.plist and entitlements
4. Privacy manifest and SDK signatures
5. App Store Connect metadata
6. App Review preparation
7. Common technical blockers

---

## 1. Account and legal prerequisites

- Apple Developer Program membership, active and paid (annual renewal — an expired
  membership silently removes your apps from sale).
- Individual vs Organization: Organization requires a D-U-N-S number. An Individual
  account publishes under your legal name, which is public. Changing between them
  later is slow.
- **EU trader status** (DSA): apps distributed in the EU must declare trader status
  with a verified address, phone and email that become **publicly visible** on the
  listing. Non-declaration removes the app from EU storefronts.
- Tax and banking forms completed in App Store Connect, or paid apps cannot go live.
- Export compliance: if the app uses encryption beyond standard HTTPS, either declare
  it or set `ITSAppUsesNonExemptEncryption` in Info.plist. Most apps using only HTTPS
  set it to `false` — but verify this is actually true for your app.

## 2. Build requirements

- ⏱ Minimum Xcode / iOS SDK version for new submissions. Apple raises this roughly
  every spring; builds made with older SDKs are rejected at upload, not at review.
- Bundle identifier is permanent. It cannot be changed after first submission.
- Version (`CFBundleShortVersionString`) must increase for each public release;
  build number (`CFBundleVersion`) must increase for each upload, even within the
  same version.
- Archive must be built for `Release`, with bitcode considerations irrelevant on
  current toolchains, and must not contain simulator slices.
- No private API usage. Symbol checks run at upload time and are unforgiving.
- App thinning: check the final download size per device. Cellular download limits
  affect conversion, and very large apps invite scrutiny.

## 3. Info.plist and entitlements

Every permission the app requests needs a purpose string that explains the benefit
**to the user**, not to the developer. "We need camera access" is rejected;
"Take a photo of your receipt to attach it to an expense" passes.

Required keys when the corresponding API is present anywhere in the binary
(including inside third-party SDKs):

| Key | Triggered by |
|---|---|
| `NSCameraUsageDescription` | Camera |
| `NSMicrophoneUsageDescription` | Audio recording |
| `NSPhotoLibraryUsageDescription` / `NSPhotoLibraryAddUsageDescription` | Photos read / write |
| `NSLocationWhenInUseUsageDescription` | Foreground location |
| `NSLocationAlwaysAndWhenInUseUsageDescription` | Background location |
| `NSContactsUsageDescription` | Contacts |
| `NSCalendarsUsageDescription` / `NSRemindersUsageDescription` | Calendar / reminders |
| `NSBluetoothAlwaysUsageDescription` | Bluetooth |
| `NSFaceIDUsageDescription` | Face ID |
| `NSUserTrackingUsageDescription` | ATT / IDFA |
| `NSHealthShareUsageDescription` / `NSHealthUpdateUsageDescription` | HealthKit |
| `NSSpeechRecognitionUsageDescription` | Speech |
| `NSLocalNetworkUsageDescription` | Local network discovery |

Also check:
- `UIBackgroundModes` — each declared mode must correspond to real functionality.
  Declaring `location` or `audio` without using it is a classic rejection.
- `LSApplicationQueriesSchemes` — needed for `canOpenURL` checks.
- Associated domains / universal links entitlement matches a live `apple-app-site-association`.
- Push notification entitlement present if the app registers for remote notifications.
- Sign in with Apple **is required** if the app offers any third-party social login
  (Google, Facebook, X…) as its only alternative — with narrow exceptions for apps
  that use an existing enterprise or education identity system.

## 4. Privacy manifest and SDK signatures

- `PrivacyInfo.xcprivacy` is required for the app and for third-party SDKs on Apple's
  "commonly used SDKs" list. It declares:
  - collected data types and whether they are linked to identity or used for tracking,
  - **required-reason APIs** with an approved reason code — file timestamps
    (`NSPrivacyAccessedAPICategoryFileTimestamp`), `UserDefaults`, disk space,
    active keyboards, system boot time.
- Third-party SDKs on that list must ship a **signature** as well as a manifest.
  An unsigned listed SDK blocks the upload.
- Xcode can aggregate the app's and SDKs' manifests into a privacy report — generate
  it and check that it matches the App Privacy answers in App Store Connect. A
  mismatch between these two is now a routine rejection.
- ATT prompt: required before accessing IDFA or tracking across apps. It must not be
  gated, incentivised, or shown with a custom pre-prompt that misrepresents the choice.

## 5. App Store Connect metadata

- App name (30 chars) and subtitle (30 chars) — no competitor names, no pricing
  claims, no "best" superlatives that can't be substantiated.
- Promotional text (170 chars, updatable without review), description (4000),
  keywords (100, comma-separated, no spaces).
- Support URL (must be reachable and about this app), marketing URL, privacy policy
  URL (**mandatory**, must be reachable, must actually describe this app's practices).
- ⏱ Screenshots: Apple has consolidated required sizes. Check the current required
  device classes before generating. Screenshots must show the real app; framing and
  captions are allowed, fabricated UI is not.
- App Privacy answers ("nutrition labels") — filled per data type, per purpose.
- **Age rating questionnaire — a submission gate, not just a rating.** Apple added
  13+, 16+ and 18+ alongside 4+ and 9+, with new required questions (in-app
  controls, capabilities, medical or wellness topics, violent themes, social media
  features). Every existing app had to re-answer by 31 January 2026 — **that date
  has passed**, so an app whose App Information still carries the old answers
  cannot submit updates in App Store Connect at all. Treat an unconfirmed
  questionnaire as a blocker for any existing app, and note that AI assistants and
  chatbots count toward how often sensitive content can appear.
  (`https://developer.apple.com/news/upcoming-requirements/?id=07242025a`)
- Content rights: declare third-party content and be ready to prove licensing.
- In-app purchases: created, submitted **with the build**, with screenshot and review
  notes. IAPs submitted separately are a common source of "waiting for review" limbo.

## 6. App Review preparation

- Demo account with a working password, and a note if it needs specific data seeded.
- Review notes explaining anything non-obvious: hardware requirements, region-locked
  features, how to reach a feature buried three taps deep.
- If the app requires a physical device or backend that reviewers cannot reach,
  provide a video walkthrough link.
- Account deletion must be reachable **inside the app** if account creation is offered.
- TestFlight external testing itself goes through a lighter review — budget for it.

## 7. Common technical blockers

- Crash on launch on the reviewer's device — usually a missing runtime permission
  guard or a hard dependency on a service that is geo-blocked.
- App renders unusably on iPad when the app is submitted as universal. Either support
  iPad properly or set the device family to iPhone only.
- Broken links anywhere in the app or the listing.
- Login walls, beta/"coming soon" markers, or placeholder screens in the shipped build.
- Web-view-only apps with no native functionality ("minimum functionality" rejection).
- Payments for digital content routed outside In-App Purchase, or UI that steers users
  to an external purchase flow beyond what current rules permit in your region.
