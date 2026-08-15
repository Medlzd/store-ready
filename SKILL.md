---
name: store-ready
description: Audit and prepare a mobile app for submission to the Apple App Store, Google Play, and alternative stores (Huawei AppGallery, Samsung, Amazon, F-Droid). Use this skill whenever the user mentions publishing, shipping, submitting, releasing or uploading an app, App Store Connect, Google Play Console, TestFlight, internal/closed testing, app rejection, app review, store metadata, screenshots, privacy manifests, Data Safety, App Privacy labels, signing, AAB/IPA builds, target SDK or minimum OS requirements — even when they don't use the word "compliance". Works for Flutter, React Native, native iOS/Android, Kotlin Multiplatform, Expo, Capacitor and Unity projects.
license: MIT
---

# Store Ready

Goal: take an app from "it works on my machine" to "accepted on first review".

Most rejections are not about the code. They are about missing metadata, a privacy
declaration that contradicts the actual SDKs in the binary, a permission with no
justification, or a build that targets an OS level the store no longer accepts.
This skill exists to catch those before submission, not after.

---

## Golden rule: verify, never recite

Store requirements change on a fixed annual cadence and dates in any document go
stale fast. Everything in `references/` is a **checklist of what to check**, not a
source of truth for current values.

Before giving the user any hard number (target SDK level, minimum Xcode version,
screenshot dimensions, deadline dates), fetch the current value from the official
source if you have web access:

- Apple: `https://developer.apple.com/app-store/review/guidelines/`
- Apple submission requirements: `https://developer.apple.com/news/upcoming-requirements/`
- Google Play policy center: `https://support.google.com/googleplay/android-developer/answer/9859455`
- Google Play target API level: `https://support.google.com/googleplay/android-developer/answer/11926878`

If you have no web access, say so explicitly and mark those numbers as
"to be verified" rather than stating them with confidence. A wrong target SDK
number costs the user a rejected build and a week of review time.

---

## Workflow

### Step 1 — Identify the project

Detect the stack before anything else, because the audit paths differ:

| Signal file | Stack |
|---|---|
| `pubspec.yaml` | Flutter |
| `package.json` with `react-native` | React Native |
| `app.json` / `app.config.js` with `expo` | Expo |
| `capacitor.config.*` | Capacitor / Ionic |
| `*.xcodeproj` / `*.xcworkspace` only | Native iOS |
| `settings.gradle` + `app/build.gradle` only | Native Android |
| `ProjectSettings/ProjectSettings.asset` | Unity |

Then ask the user only what you cannot detect:

1. Which stores? (App Store, Google Play, both, others)
2. First submission or an update to a live app?
3. Does the app have accounts, payments, ads, user-generated content, or health data?
4. Which countries/regions? (EU changes the requirements meaningfully)

Do not ask questions whose answers are already in the repository. Read first, ask second.

### Step 2 — Run the automated pre-flight

```bash
python3 scripts/preflight.py /path/to/project
```

It parses the manifests and config files and reports what it can determine
mechanically: bundle/application ID, versions, target and min SDK, declared
permissions, iOS usage-description strings, presence of a privacy manifest,
signing configuration, and obvious blockers.

It prints findings as `BLOCKER`, `WARN`, or `INFO`. It never modifies the project.
Treat its output as evidence to interpret, not as a verdict — it cannot see
metadata that lives in App Store Connect or Play Console.

### Step 3 — Read the relevant reference file(s)

Load only what applies to the current job:

| File | Read it when |
|---|---|
| `references/apple-app-store.md` | Targeting iOS/iPadOS/macOS/visionOS |
| `references/google-play.md` | Targeting Google Play |
| `references/privacy-and-data.md` | Any app that collects, transmits or stores user data (i.e. almost all) |
| `references/assets-and-metadata.md` | Preparing icons, screenshots, descriptions, store listing |
| `references/rejections.md` | The app was already rejected, or you want the high-risk list |
| `references/alternative-stores.md` | Huawei, Samsung, Amazon, F-Droid, EU alternative distribution |

### Step 4 — Produce the report

Always use this exact structure. It is the deliverable the user acts on.

```markdown
# Store Readiness Report — <App name>

**Stack:** <detected>  ·  **Targets:** <App Store / Play / …>  ·  **Date:** <date>

## Verdict
<One sentence: ready to submit / N blockers to fix first.>

## Blockers — submission will be rejected
| # | Issue | Where | Fix |
|---|-------|-------|-----|

## Warnings — likely to trigger reviewer questions
| # | Issue | Where | Fix |
|---|-------|-------|-----|

## To verify manually
<Items that live in App Store Connect / Play Console and cannot be read from the repo.>

## Submission checklist
- [ ] …
```

Rules for the report:

- Every blocker names the **exact file and line or console screen** to change. "Fix your permissions" is useless; "`android/app/src/main/AndroidManifest.xml:12` declares `READ_CONTACTS` but no code path uses it — remove it or file a Permissions Declaration" is actionable.
- Sort by cost of being wrong, not by ease of fixing.
- If something cannot be determined from the repository, put it under *To verify manually* rather than guessing. Silent guesses are how people get rejected.
- Keep the checklist copy-pasteable into an issue tracker.

### Step 5 — Offer to fix

After the report, offer to apply the mechanical fixes (missing usage strings,
version bumps, manifest cleanup, generating a privacy manifest stub, resizing
icons). Never apply changes to signing configuration, bundle identifiers, or
anything that touches credentials without explicit confirmation — those break
existing installs and cannot be undone from the store side.

---

## Things that get people rejected and that agents routinely miss

- **The privacy declaration contradicts the binary.** Analytics or ad SDKs pull in data collection the developer forgot to declare. Audit the actual dependency list, not the developer's memory.
- **Login required to see anything.** Both stores expect a demo account or a way for a reviewer to see the app's value. Missing reviewer credentials is a top-three rejection cause.
- **Account creation without account deletion.** Both stores now require an in-app path to delete the account, not just an email address.
- **Permissions with no visible feature.** Every permission needs a user-facing reason the reviewer can find in under a minute.
- **Placeholder content.** Lorem ipsum, test data, dead links in the description, a support URL returning 404.
- **External payment links** for digital goods, outside the narrow exceptions.
- **Screenshots that don't match the app**, are marketing renders, or show a UI that no longer exists.

---

## Multi-agent compatibility

This skill works standalone. If the host agent cannot read `references/` on demand,
inline the relevant file's content before starting rather than working from memory.
`AGENTS.md` at the repository root points non-Claude agents here.
