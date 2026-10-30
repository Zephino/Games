# Zephino Games: working rules for Claude

Adapted from the owner's `co-engineering-partner` and `verifiable-accuracy` rules. The original Antigravity, Obsidian-vault and CAD-specific parts are left out because they don't exist in this project.

## How to work

- **Truth before comfort.** If a request or plan has a flaw (a broken assumption, an edge case, something that will force rework), say so first, with evidence, and offer a path that still reaches the owner's goal. Don't silently water down a request to make it easier.
- **Verify load-bearing facts before building on them.** Check files, run tests, query GitHub. If something can't be checked from here (Cloudflare or GitHub settings, the live site), say so and list it as open. Never guess.
- **No invented facts.** Controls, platforms, limits, versions and sizes on the page or in docs must come from code, a game's own repo, or the owner. If one is missing, write `[TBD: <what>]` and tell the owner. Use the `claim-verification` skill for README and page copy.
- **Fail closed.** If a file read, fetch or command needed for a fact fails, stop and report exactly what was blocked. Don't fill the gap.
- **Root causes, small diffs.** No swallowed errors or arbitrary retries. Change only what the request needs, match the surrounding style, and flag unrelated problems instead of fixing them on the side.
- **Don't break what works.** Before a change, check it against the protected list below. If it would weaken one of those items, stop and say so.

## Verifying changes

There is no bubblewrap or btrfs sandbox here, so the "dry run" is:

- Worker: `cd ideas-api && node --test test/*.test.mjs`
- Page: serve the repo (`python3 -m http.server`) and drive it with Playwright (pre-installed). Check at 320, 375 and 1440 px wide, confirm no horizontal scroll, and look at screenshots before calling a visual change done.
- Docs and copy: the `claim-verification` skill.

## Publishing

- Merging to `main` publishes the site (GitHub Pages) and redeploys the ideas Worker (Cloudflare Git build, root `ideas-api`). Work on a branch and **ask the owner before merging to `main`** unless they've said to in that request.
- Never commit tokens. `GITHUB_TOKEN` lives only in the Worker's Cloudflare secrets.

## Project State Ledger

### Concept (locked)
A homepage that showcases Zephino's browser games and lets anyone suggest a game idea from a pop-up, without an account or leaving the page.

### Protected (verified; don't regress)
- **PROTOCOL-01:** The "Suggest a game" buttons (header, hero, "More worlds" box) open the `#suggest` pop-up. `/#suggest` and the old `/#ideas` open it on load.
- **PROTOCOL-02:** Ideas post only to `https://zephino-game-ideas.thebotcoder.workers.dev/ideas`. There is no GitHub redirect fallback (owner's request), and visitor-written ideas are never shown publicly on the site.
- **PROTOCOL-03:** `ideas-api/wrangler.toml` must keep the `IDEAS_KV` binding (id `428917680488477f94f0763b8bce1108`). Without it, each Git deploy drops the binding and the Worker stops accepting ideas.
- **PROTOCOL-04:** Worker protections: field limits, honeypot, 3 ideas per visitor per day, 50 per day in total, escaped Markdown, `@` mentions defused.
- **SOLVED-01:** End-to-end submission works. The owner's test idea arrived as issue #4 with the `game-idea` label (checked through the GitHub API).
- **SOLVED-02:** Game versions load live from each game's `VERSION` file (`versions.js`).

### Open
- **OPEN-01 [LOAD-BEARING]:** `[TBD: GITHUB_TOKEN expiry date]`. Fine-grained GitHub tokens expire. When this one does, every submission fails with a GitHub 401 and nobody is notified. The owner should check the expiry, and a token renewal reminder or health check is worth adding.
- **OPEN-02 [ISOLATED]:** Every push to `main` runs two Pages deployments ("pages build and deployment" from branch mode, plus "Deploy Zephino Games" from Actions). Set Pages → Source to one of them.
- **OPEN-03 [ISOLATED]:** Pages publishes the whole repo, including `ideas-api/`, `README.md` and `.claude/`. That's harmless (no secrets), but it's public.
- **OPEN-04 [ISOLATED]:** The game cards use illustrations, not real screenshots. Adding one per game is the biggest visual improvement left.
- **OPEN-05 [ISOLATED]:** The "02 games" count and the meta descriptions are hardcoded. Update them when adding a game (see README → Adding more games).
- **OPEN-06 [ISOLATED]:** `[TBD: Cloudflare "Preview builds" setting]`. If it's on, branch pushes create preview Worker versions.
