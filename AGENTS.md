# AGENTS.md — store-ready

Entry point for any coding agent that follows the `AGENTS.md` convention
(Cursor, Windsurf, Codex, Gemini CLI, Cline, Aider, Copilot Workspace, and others).

## What this repository gives you

A procedure for auditing a mobile app before submitting it to the Apple App Store,
Google Play, or an alternative store, plus a read-only script that inspects the
project's manifests.

## When to apply it

Apply it whenever the user's request touches publishing, releasing, submitting or
uploading an app; App Store Connect or Play Console; TestFlight or testing tracks;
an app rejection; store metadata, screenshots or icons; privacy manifests, App
Privacy labels or the Data safety form; signing, AAB or IPA builds; or target SDK
and minimum OS requirements.

## How to apply it

1. Read `SKILL.md` in this repository. It contains the full workflow and the
   report format. Follow it exactly.
2. Read only the files under `references/` that the current task needs — the table
   in `SKILL.md` step 3 says which.
3. Run `python3 scripts/preflight.py <project-path>` for the mechanical audit.
   It is read-only and has no dependencies beyond the Python standard library.
4. Produce the report in the exact structure given in `SKILL.md` step 4.

## Non-negotiables

- **Never state a store requirement value from memory.** Target SDK levels,
  screenshot dimensions, minimum Xcode versions and deadline dates change on an
  annual cadence. Fetch them from the official documentation, or mark them clearly
  as unverified. A confidently wrong number costs the user a rejected build.
- **Never guess a declaration.** If something lives in App Store Connect or Play
  Console and cannot be read from the repository, list it under *To verify
  manually* instead of assuming.
- **Never modify signing configuration, bundle identifiers or credentials**
  without explicit user confirmation. Those changes are irreversible from the
  store's side.
- Derive the app's data collection from the dependency lockfiles, not from what
  the developer remembers installing.

## Single-file version

If your host cannot read multiple files, run `python3 scripts/bundle.py` to
produce `dist/store-ready-prompt.md`, a single flattened document containing the
skill and all references. Paste that into a custom GPT, a Gemini Gem, a system
prompt, or a project's instructions.
