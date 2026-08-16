# Roadmap

What is deliberately not in v1, and why. Each item is real work that was scoped
and deferred, not an oversight.

## v1.1 — tooling confidence

**Golden tests in CI.** `scripts/preflight.py` is a pile of heuristics, and CI
currently compiles it without ever running it. Add `tests/fixtures/` with a
deliberately broken app and a clean one, then assert exit `1` and exit `0`
respectively, plus a `--json` shape check. Every check that produces a BLOCKER
should have a fixture that fires it and a fixture that must stay silent — a false
blocker is the failure mode that costs this project its credibility, so it is the
one that deserves a regression test. Run the matrix on Python 3.9 through 3.13,
on Linux and macOS.

**Project root auto-detection.** `detect_stack()` only looks at the directory it
is handed. A Turborepo or Expo monorepo therefore exits `2` with "no recognisable
mobile project" while `package.json` sits right there, and a Flutter app under
`apps/mobile/` can be mislabelled `native-ios` because some `.xcodeproj` exists
somewhere in the tree. Search a few levels down for a signal file, re-root on a
single unambiguous match, and list candidates instead of failing when there are
several.

**Findings that point at the triggering line.** iOS usage-description findings
report the `Info.plist` path, because the check runs over one concatenated blob of
every source file. `SKILL.md` promises "the exact file and line". Make
`read_source_files()`'s per-file structure reach the finding.

**Merged-manifest awareness.** The Android audit reads `AndroidManifest.xml` as
written, so permissions and components injected by dependencies are invisible —
which is exactly where surprise permissions come from. At minimum, say so in the
output and point at `./gradlew :app:processReleaseManifest`.

## v1.2 — workflow depth

**A timeline section in the report.** The readiness verdict can say "ready to
submit" to a solo developer who is two weeks away from being *allowed* to request
production access, because Play's closed-testing rule for personal accounts is a
calendar gate, not a code fix. Step 1 now asks for the account type and any launch
deadline; the report should turn that into an earliest realistic live date, and
rank a deadline conflict above every code blocker.

**Store listing generation.** Writing the title, subtitle, description, keywords
and release notes is adjacent work the skill currently only audits. The
constraints already live in `references/assets-and-metadata.md`.

**Update-vs-first-submission branching.** The workflow assumes a first
submission. An update has a different risk profile: version codes, staged
rollout, what changed since the last review, and which declarations need
re-answering.

## Not planned

**A `.claude-plugin/` marketplace manifest.** `npx skills add` already handles
discovery, installation and updates across Claude Code, Cursor, Codex and others
from a single source of truth. A second distribution manifest would be a second
thing to keep in sync for no reach the CLI does not already provide. Revisit only
if the plugin marketplace gains something the CLI lacks.
