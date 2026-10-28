# Baebugs Vercel production audit — October 28, 2026

**Repository:** biobitworks/baebugs (PUBLIC).
**Project:** Vercel biobitworks / baebugs-lab-workcell.
**Predecessor production deployment:** dpl_9uPwejHcas2Sivwj9h6SR7BohSgZ.
**Predecessor source commit:** db5846500b1c53796813d732afe46d62ec5c55d2.
**Merged slideshow PR #34:** 96b15c908c6a9ee4687999644ce2362c693e911d.

## Controls observed

- Previous Vercel production state READY, verified domain with HTTPS/HSTS.
- Vercel runtime errors: zero error clusters reported for prior 24 hours.
  Static routing and browser failures require separate verification.
- Local static site: 10 routes HTTP 200; 63 internal href/src references checked,
  zero broken; zero mobile horizontal overflow.
- Automated axe-core WCAG A/AA baseline: home two color contrast violations,
  protocols one accessible-name mismatch, twin six contrast nodes. Repaired in
  source; successor local scan across 10 routes: zero violations.
- Full source suite after installing audit dependencies in an isolated Python
  3.12 environment: 153 passed, 2 skipped, 1 expected failure, 0 unexpected.
  Predecessor test-environment dependency failures were not project defects.
- Existing published multimedia includes four videos and printable STLs.
  Slideshow PR #34 brings four original PowerPoint files. Their SHA-256 values
  match recorded README values; 40 embedded JPEGs have no EXIF; no macros,
  external OOXML relationships or embedded active content were found.
- One approved team photo (slide 32 of full 32-slide deck) is extracted as its
  exact original JPEG, with independent image/source package hash identities.
- Approval originates in the user's October 28 statement, "The team pic is
  approved". This is USER_ASSERTED_NOT_SIGNED. Independent releases from every
  depicted individual and commercial reuse terms remain NOT_VERIFIED.
- Vercel project environment variable listing returned HTTP 403. No secret
  names or values were retrieved. Drains inventory returned 404: UNKNOWN.
- Vercel web headers lacked explicit nosniff, CSP, referrer and feature policies.
  Versioned site/mvp/vercel.json introduces these, subject to staged verification.

## Custody

The slideshow merge, policy code, photographs and audit records are new source
atoms. Existing DAISY, FCO and detection observations are not rewritten.
Merkle roots represent exact source identities. They do not establish scientific
truth, biological classification, physical robotic recovery, person-release
signatures, or new MMR commitments. Physical recovery remains NOT_TESTED.

## Release gates

1. Commit and review the source branch.
2. Merge into main, compile the source-pinned output and verify all file digests.
3. If authenticated Vercel access is available, stage a production build without
   switching the alias, run security and browser checks, then promote that exact
   build and rehash production responses.
4. If deployment authority is unavailable, retain a NOT_DEPLOYED state and report
   the blocker rather than claim publication or signatures.
