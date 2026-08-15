# Assets and store listing — audit reference

> ⏱ Exact pixel dimensions and required device classes change. Confirm current specs
> in App Store Connect / Play Console before generating final assets.

## 1. Icons

| Target | Notes |
|---|---|
| iOS | Single high-resolution source, no alpha channel, no transparency, no rounded corners baked in (the system masks it) |
| Android | Adaptive icon: separate foreground and background layers, keep content inside the safe zone or it gets cropped on round-mask launchers; also provide a monochrome layer for themed icons |
| Play listing | High-res square icon, distinct from the launcher icon in resolution |

Fails to avoid: text in the icon that becomes unreadable at 48 px; an icon that
resembles a system app or another brand; different icons on the two platforms for
the same product.

## 2. Screenshots

- Must be captured from the real, current app. Device frames, background colours and
  short captions are allowed; invented UI is not.
- The first two screenshots do almost all the conversion work — they appear in search
  results. Lead with the core value, not with the login screen.
- Localise screenshots for markets where you localise the app. A French listing with
  English screenshots reads as abandoned.
- Provide the required size for each device class you support; missing an iPad or
  tablet set blocks submission if the app declares support for it.
- Play also wants a feature graphic; a video is optional but noticeably lifts installs.

## 3. Text

| Field | Discipline |
|---|---|
| Title | Real product name. No keyword stuffing, no "#1", no competitor names |
| Short description / subtitle | One sentence that says what the app does for whom |
| Full description | First three lines are visible before "read more" — put the value there |
| Keywords (Apple) | Comma-separated, no spaces, no plurals of words already used, no brand names you don't own |
| What's new | Actual changes. "Bug fixes and improvements" on every release is a soft negative signal |

Prohibited across both stores: pricing claims in the title, references to other
platforms ("also on Android"), unsubstantiated superlatives, fake urgency, and any
mention of beta status in a production listing.

## 4. Localisation

- Translate the listing for each language you claim to support. A store listing in a
  language the app does not actually support is a rejection.
- RTL languages (Arabic, Hebrew): verify the **app** handles mirroring, not just the
  listing — layout direction, icon mirroring, number formatting, and text alignment.
  A reviewer switching the device to Arabic and finding a broken layout will reject.
- Check that translated strings do not overflow buttons; German and Arabic frequently
  break layouts tuned in English.

## 5. Automation

Generating screenshots by hand does not survive the third release. Use:
- `fastlane snapshot` / `screengrab`, or Flutter integration tests driving screenshots
- `fastlane deliver` / `supply` to upload metadata and binaries from CI
- Keep listing text in version control (`fastlane/metadata/`) so changes are reviewable

## 6. Checklist

- [ ] Icons at every required density, no transparency on iOS, adaptive + monochrome on Android
- [ ] Screenshots for every declared device class, from the current build
- [ ] Feature graphic (Play)
- [ ] Title, subtitle/short description, full description free of prohibited claims
- [ ] Keywords tuned, no brand infringement
- [ ] Support and marketing URLs live and about this app
- [ ] Privacy policy URL live
- [ ] Listing localised for every claimed language, RTL verified in-app
- [ ] Release notes describe real changes
