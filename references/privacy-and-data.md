# Privacy and data — audit reference

The recurring failure is not "we didn't write a privacy policy". It is that the
declaration, the policy, and the binary say three different things. Reviewers now
compare them automatically.

## 1. Build a real data inventory first

Do not ask the developer what the app collects. Derive it:

1. List every dependency (`pubspec.yaml`, `package.json`, `Podfile.lock`,
   `build.gradle`, `Package.resolved`).
2. For each, classify: analytics, crash reporting, ads, attribution, push,
   auth, payments, maps, chat/support, A/B testing.
3. Every item in those categories collects something — usually device identifiers,
   coarse location, and usage events at minimum.
4. Add what your own backend stores.

Frequent blind spots: Firebase Analytics (collects and by default enables ad ID
signals), Crashlytics (device + crash context), Sentry (may capture PII in
breadcrumbs and request bodies), Facebook SDK, AppsFlyer/Adjust, Google/Meta ad
SDKs, embedded webviews loading third-party trackers, and any "free" map or font CDN.

## 2. Map the inventory to each store's form

| Concept | Apple | Google |
|---|---|---|
| Declaration surface | App Privacy labels + `PrivacyInfo.xcprivacy` | Data safety form |
| Distinguishes | Linked to user / Not linked / Used to track | Collected vs Shared, ephemeral processing |
| Tracking consent | ATT prompt required | Ad ID policy + user consent |
| SDK-level file | Privacy manifest + SDK signature | None, but SDK behaviour still counts |

Rule: if a data type appears in the inventory, it must appear in **both** forms,
in the privacy policy, and in the privacy manifest. Silence is treated as a false
declaration, not as an omission.

## 3. Privacy policy — minimum contents

- Identity and contact of the data controller (a real address; for EU distribution
  this is already public via trader status).
- Categories of data, purposes, and legal basis.
- Third parties receiving data, named, with links to their policies.
- Retention periods.
- User rights and **how to exercise them**, including deletion.
- Children's data statement.
- International transfers.
- Last-updated date.

The URL must be live, HTTPS, publicly reachable without login, and about **this**
app. A generic template with `[COMPANY NAME]` left in it is an instant rejection.

## 4. Consent, when it is actually required

- **EU/UK (GDPR)**: consent before non-essential tracking; a CMP that is
  Google-certified if you serve Google ads in the EEA. Consent must be as easy to
  refuse as to accept.
- **Apple ATT**: required before IDFA access regardless of GDPR consent.
- **US state laws**: opt-out signals for sale/share of personal information.
- **Children**: COPPA in the US, Families policy on Play, Kids Category on Apple —
  no behavioural ads, restricted SDK list, verifiable parental consent.

Implement consent **before** the first SDK initialisation, not after. Firing an
analytics event on app launch and asking for consent on screen two is a violation
that a reviewer can observe with a proxy.

## 5. Deletion and portability

Both stores require, when accounts exist:

- An in-app path: Settings → Account → Delete account, reachable without contacting
  support.
- A web URL for users who have uninstalled the app.
- Clear statement of what is deleted immediately, what is retained, and for how long
  (legal retention is acceptable if stated).
- Deletion must actually delete backend data, not just deactivate the login.

## 6. Security expectations reviewers check

- HTTPS everywhere; no cleartext exceptions without a documented reason.
- No secrets, API keys or credentials in the shipped binary — they are trivially
  extractable from an IPA or AAB. Move them server-side or scope them tightly.
- Tokens in Keychain / EncryptedSharedPreferences, never in plain
  `UserDefaults` / `SharedPreferences`.
- No PII in logs, crash breadcrumbs, or analytics event names.
- Backups: exclude sensitive files (`allowBackup`, iOS backup exclusion attributes).

## 7. Pre-submission verification

- [ ] Dependency inventory built from lockfiles, not from memory
- [ ] Apple App Privacy answers match the generated privacy report
- [ ] `PrivacyInfo.xcprivacy` present, with required-reason API codes
- [ ] All listed third-party SDKs updated to versions that ship manifest + signature
- [ ] Play Data safety form matches the same inventory
- [ ] Privacy policy live, specific, and consistent with both forms
- [ ] Consent gate fires before any tracking SDK initialises
- [ ] In-app and web account deletion both work end to end
- [ ] Traffic captured through a proxy on a clean device shows no undeclared endpoint
