---
name: claim-verification
description: >-
  Check that facts in docs or page copy (numbers, limits, sizes, file names,
  commands, controls, platforms) are backed by the code or another real source
  before publishing. Use when writing or editing README.md, index.html text,
  issue templates, or any claim about how the site, the ideas Worker, or the
  games behave.
---

# Claim Verification

Adapted for Zephino Games from the owner's `claim-verification` skill and the `verifiable-accuracy` rule.

## Pre-flight

1. **Pick real sources.** Ground truth is the code and config in this repo (`index.html`, `ideas.js`, `versions.js`, `style.css`, `ideas-api/src/index.mjs`, `ideas-api/wrangler.toml`, `.github/**`), each game's own repo (for example `Zephino/Mythriven` README), and what the owner says. Prose written earlier by an AI (including this repo's README) is **not** a source. Verify it, don't cite it.
2. **Never pass the target as its own source.**
3. **Fail closed.** If a source can't be read (blocked network, missing file), stop and say which resource was blocked. Don't fill the gap from memory.

## Procedure

1. Write the draft. Where a fact is needed but not in any source, write `[TBD: <what is missing>]` instead of guessing (for example `[TBD: Wave Defence gamepad support]`).
2. Run the verifier (read-only: it reads files and runs `git status`):
   ```bash
   python3 -I .claude/skills/claim-verification/scripts/verify_claims.py \
     --target README.md \
     --sources index.html ideas.js versions.js style.css ideas-api/src/index.mjs \
       ideas-api/wrangler.toml ideas-api/package.json .github/workflows/pages.yml \
       .github/workflows/ideas-checks.yml .github/ISSUE_TEMPLATE/game-idea.yml LICENSE
   ```
3. For each **unbacked claim**, do one of three things: bind it to a source you forgot to pass and re-run, replace it with `[TBD: ...]`, or delete it.
4. **Check plain-prose numbers by hand.** The script only checks backticked names, numbers with units and a few designators. Sentences like "3 ideas per visitor per day" pass through unchecked. Compare them with the constants in the code (`DAILY_IP_LIMIT`, `REFRESH_INTERVAL_MS`, `expirationTtl`, image sizes and so on).

## Done when

- Every flagged item is bound, tagged `[TBD: ...]`, or removed, and any that stay flagged on purpose (for example a placeholder like `<article class="card ...">`) are listed with the reason.
- Open `[TBD]` items are listed for the owner at the end of the turn.

## Stop and ask the owner if

- Two sources disagree (for example a game's README versus its card on the homepage). Show both values; don't pick one.
- A claim depends on something only the owner can see (Cloudflare or GitHub settings, token expiry and so on).
