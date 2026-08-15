# Rejection triage

Use this file in two situations: pre-submission risk scan, and after a rejection
when the user pastes the review message.

## 1. Reading a rejection notice

Apple cites a guideline number; Google cites a policy name. Always map the message
to the exact clause before proposing a fix — the same wording ("we noticed an issue
with your app") sits on top of very different clauses.

Then decide between three responses:

| Situation | Response |
|---|---|
| The reviewer is right | Fix, resubmit, and say what changed in the review notes |
| The reviewer missed a feature | Reply in Resolution Center / Play appeal with **exact steps** and a screen recording. Do not resubmit the same binary silently |
| The rule genuinely doesn't apply | Explain factually, cite the guideline, request escalation. Apple has an App Review Board; Play has an appeal form |

Never argue tone. Reviewers process hundreds of appeals; the ones that succeed are
short, specific, and include a reproduction path.

## 2. High-frequency causes, ranked by how often they bite

1. **Reviewer cannot get in.** No demo account, credentials expired, OTP goes to a
   phone number in one country only, or the backend blocks the reviewer's region.
2. **Privacy declaration mismatch.** Labels/Data safety contradict the SDKs present.
3. **Missing account deletion** when sign-up exists.
4. **Permission with no visible purpose**, or a permission requested at launch before
   any context.
5. **Placeholder or broken content.** Dead links, lorem ipsum, empty states that look
   like errors, a support page returning 404.
6. **Minimum functionality.** A webview wrapper, or an app whose value is entirely
   outside the app.
7. **Payments.** Digital goods routed outside IAP/Play Billing, or steering UI.
8. **Crash on the reviewer's device.** Often an older device, a fresh install with no
   data, or a permission denied at first prompt.
9. **Metadata violations.** Competitor names, unsupported claims, wrong age rating.
10. **Design and layout.** Unusable on iPad, content under the notch/dynamic island,
    broken RTL, no support for the largest accessibility text size.

## 3. Pre-submission self-check on a clean device

Do this on a factory-reset or fresh-install device, not on the dev machine:

- [ ] Install the exact build being submitted (TestFlight / internal testing track)
- [ ] Launch offline — no crash, an intelligible message
- [ ] Deny every permission at first prompt — app remains usable, no crash
- [ ] Complete signup, then delete the account, from inside the app
- [ ] Navigate every screen once; check for placeholders and dead links
- [ ] Rotate, switch to the largest text size, switch device language to an RTL locale
- [ ] Test on the oldest OS version the app claims to support
- [ ] Confirm the demo account still works today

## 4. Escalation timelines

- Apple: standard review is usually short; appeals and Review Board take longer.
  Expedited review exists for critical bugs or time-sensitive events — it is granted
  sparingly, so save it for a real emergency and explain the impact concretely.
- Google: appeals go through a form; account-level suspensions are handled by a
  different team and take significantly longer than app-level rejections.
- Build the timeline assuming at least one rejection round on first submission.
