# store-ready

**Catch App Store and Google Play rejections before you submit.**

`store-ready` is a portable agent skill. It reads your project's actual
`Info.plist`, `AndroidManifest.xml`, `build.gradle` and dependency files, checks
them against current store requirements, and produces a report you can act on:
blockers, warnings, items you must verify in App Store Connect or Play Console,
and a copy-pasteable submission checklist.

Most rejections are not about code. They come from a privacy declaration that
contradicts the SDKs actually in the binary, a permission with no visible
feature, a missing reviewer demo account, or a build targeting an API level the
store no longer accepts. This skill catches those *before* submission.

Supports Flutter, React Native, Expo, Capacitor/Ionic, native iOS, native
Android, Kotlin Multiplatform and Unity — with Claude, ChatGPT, Gemini, Cursor,
and any agent that reads `AGENTS.md`.

---

## What it checks

**Read from your repository, mechanically:**

- Bundle / application ID, version and build number
- iOS purpose strings against the APIs and plugins actually used
- Privacy manifest presence
- Android target and minimum SDK, sensitive permissions, `android:exported`,
  debuggable and cleartext-traffic flags
- Release signing configuration and hard-coded keystore passwords
- Credentials committed to source
- Account creation with no account-deletion path

**Flagged for manual verification** — these live in the consoles, not in your repo:

- App Privacy labels and the Data safety form, against your real dependency list
- Reviewer demo account and review notes
- Screenshots, icons, description, localisation
- Content rating, trader status, testing-track requirements

---

## Install

### Any agent — one command

```bash
npx skills add medlzd/store-ready
```

Installs into the current project for the agent you're using. Inspect it first,
target a specific agent, or install user-wide:

```bash
npx skills add medlzd/store-ready --list      # inspect, install nothing
npx skills add medlzd/store-ready --agent cursor
npx skills add medlzd/store-ready --global
```

Claude Code lands in `.claude/skills/store-ready`, Cursor and Codex in
`.agents/skills/store-ready`. Both carry `references/` and `scripts/`, so the
pre-flight script runs immediately after install. Works with Claude Code,
Cursor, Codex, OpenCode and 50+ other agents through the
[Skills CLI](https://github.com/vercel-labs/skills).

### Claude Code, without Node

```bash
git clone https://github.com/medlzd/store-ready.git \
  ~/.claude/skills/store-ready
```

Restart Claude Code. The skill triggers on its own as soon as you mention
publishing, a rejection, store metadata or signing.

To scope it to one project, clone into `.claude/skills/store-ready` inside that
project instead.

### Claude Desktop / claude.ai

Skills are uploaded as a `.zip` whose root contains exactly one `store-ready/`
folder:

```bash
git clone https://github.com/medlzd/store-ready.git
zip -r store-ready.zip store-ready -x '*.git*' '*__pycache__*'
```

Upload `store-ready.zip` under Settings → Capabilities → Skills. Enable code
execution in the same panel if you want `preflight.py` to run.

### ChatGPT custom GPTs, Gemini Gems, or any system prompt

These hosts cannot read a folder. Flatten the skill into a single file:

```bash
python3 scripts/bundle.py
```

Paste `dist/store-ready-prompt.md` into your GPT's instructions or your Gem. Add
`scripts/preflight.py` to the GPT's knowledge base if you want it to run the
script through Code Interpreter.

### No agent — just the script

```bash
python3 scripts/preflight.py /path/to/your/app
```

---

## Updating

Skills install as a copy, so a new release here does not reach your agent until
you refresh it:

```bash
npx skills update store-ready
```

Add `--global` for a user-wide install, `--project` for a project one.
Re-running `npx skills add` also re-fetches the latest.

---

## Usage

Once installed, say what you actually want:

- *"My Flutter app is ready — will it pass App Store review?"*
- *"Prepare the Play Store submission, we're shipping in the EU too."*
- *"Here's Apple's rejection message. What do I fix?"*
- *"Generate the submission checklist for both stores."*

The agent detects your stack, runs the pre-flight, reads the reference files
that apply to your case, and produces the report.

### Running the script on its own

```
$ python3 scripts/preflight.py ~/dev/receipts
========================================================================
  store-ready pre-flight — receipts
  stack: flutter
========================================================================

Detected:
  stack                      flutter
  version                    1.0.0+1
  android_permissions        android.permission.CAMERA, android.permission.QUERY_ALL_PACKAGES
  target_sdk                 33
  min_sdk                    21
  application_id             com.example.receipts
  ios_usage_descriptions     NSCameraUsageDescription

Findings: 7 blocker(s), 3 warning(s), 3 note(s)

[BLOCKER] <receiver> .BootReceiver declares an intent-filter but no android:exported
        where: android/app/src/main/AndroidManifest.xml:8
        fix:   Set android:exported explicitly; required since Android 12.

[BLOCKER] Placeholder applicationId: com.example.receipts
        where: android/app/build.gradle
        fix:   The applicationId is permanent after first upload. Change it now.

[BLOCKER] Release build type uses the debug signing config
        where: android/app/build.gradle
        fix:   Configure a release keystore and enable Play App Signing.

[BLOCKER] NSCameraUsageDescription has a placeholder or too-short purpose string
        where: ios/Runner/Info.plist
        fix:   Explain the user benefit concretely, e.g. 'Take a photo of your receipt to attach it'.
...
```

Exit codes: `0` no blockers, `1` at least one blocker, `2` not a recognisable
mobile project. Pass `--json` for machine-readable output.

The script is **read-only** — it never writes to your project — and uses only
the Python standard library.

---

## What's in here

```
store-ready/
├── SKILL.md                    the workflow and the report format
├── AGENTS.md                   entry point for non-Claude agents
├── references/
│   ├── apple-app-store.md      accounts, build, Info.plist, privacy manifest
│   ├── google-play.md          AAB, target SDK, permissions, Data safety
│   ├── privacy-and-data.md     data inventory, consent, GDPR
│   ├── assets-and-metadata.md  icons, screenshots, copy, localisation, RTL
│   ├── rejections.md           rejection triage and appeals
│   └── alternative-stores.md   Huawei, Samsung, Amazon, F-Droid, EU distribution
└── scripts/
    ├── preflight.py            the automated audit, read-only
    └── bundle.py               builds the single-file version
```

---

## Design principle: verify, never recite

Store requirements change on a fixed annual cadence, and any hard number written
into a document goes stale fast. Nothing in `references/` is treated as a source
of truth for current values — the reference files say **what to check**, and the
skill requires the agent to fetch the current value from official documentation
or mark it explicitly as unverified.

A confidently stated but outdated target SDK level costs you a rejected build
and a week of review time. That is the whole reason for the rule.

---

## Requirements

Python 3.9 or newer. No third-party packages.

## Contributing

Store requirements move constantly. The most useful pull requests are the ones
that correct a rule that has gone stale, or add a rejection cause you hit for
real. Please include a link to the official documentation for the change.

## License

MIT — see [LICENSE](LICENSE).
