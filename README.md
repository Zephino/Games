# Zephino Games

**Pick a world. Make it yours.**

The responsive home for independently developed games by Zephino.

**🎮 [Visit Zephino Games](https://zephino.github.io/Games/)**

## Available games

| Game | Play online | Project |
| --- | --- | --- |
| **Mythriven** — mythology-inspired roguelike survivor | [▶ Play Mythriven](https://zephino.github.io/Mythriven/) | [Repository](https://github.com/Zephino/Mythriven) |
| **Wave Defence** — endless maze-building tower defence | [▶ Play Wave Defence](https://zephino.github.io/WaveDefence/) | [Repository](https://github.com/Zephino/WaveDefence) |

Both games are under active development. The launcher links directly to each game's authorized web build. It does not copy, host or embed the game executables. Each card's decorative vector artwork is an original illustration, not a screenshot from the game.

## Publishing

The source is a lightweight static website with `index.html`, `style.css`, `versions.js`, `ideas.js` and the `social.png` link-preview image at the repository root. The optional suggestion Worker in `ideas-api/` is deployed separately to Cloudflare. There are no build dependencies, API keys, user trackers or external fonts.

If GitHub Pages is already set to **Deploy from a branch (main / root)**, GitHub will deploy the index file when the branch updates. If it is set to **GitHub Actions**, the included `.github/workflows/pages.yml` automatically builds and publishes the site on every push to `main`. The workflow also supports manual runs.

Check publishing status at [Actions](https://github.com/Zephino/Games/actions) or [Settings → Pages](https://github.com/Zephino/Games/settings/pages). Successful hosting should appear at <https://zephino.github.io/Games/>.

## Automatic game versions

The homepage reads the version number directly from each public game's `VERSION` file on the `main` branch:

- [Mythriven/VERSION](https://github.com/Zephino/Mythriven/blob/main/VERSION)
- [WaveDefence/VERSION](https://github.com/Zephino/WaveDefence/blob/main/VERSION)

`versions.js` requests those files from GitHub when the homepage opens, then checks again every five minutes while the page is visible. It deliberately bypasses the browser cache and uses plain text for display. **You do not need to update or redeploy the Games homepage when a game's VERSION file changes.** No API key or backend is needed. If GitHub cannot be reached, the card says `Version unavailable` (or keeps the last successfully loaded version for that visit).

The displayed number is the version **on the game's GitHub `main` branch**. The playable web build may temporarily be older while its GitHub Pages deployment runs.

## Game suggestions

Anyone can pitch a game idea from the homepage. The **💡 Suggest a game** button is in the header, the top section and under the game cards, and it opens a pop-up form. Linking to `https://zephino.github.io/Games/#suggest` opens the pop-up straight away, which is handy for sharing.

Every idea becomes a GitHub Issue in this repository labelled `game-idea`, so they all land in one inbox: [open game ideas](https://github.com/Zephino/Games/issues?q=is%3Aissue+is%3Aopen+label%3Agame-idea). Ideas are never shown publicly on the homepage. Create the `game-idea` label once under [Issues → Labels](https://github.com/Zephino/Games/labels). If it's missing, ideas still arrive, just unlabelled.

- **Before the Worker is set up**, the form opens a prefilled GitHub issue (`.github/ISSUE_TEMPLATE/game-idea.yml`). That works right away, but visitors need a free GitHub account.
- **After the Worker is set up**, ideas are sent without any account, the same way Wave Defence's in-game *Suggest a Feature* works. See the steps below.

### Setting up the no-account Worker

The Worker lives in `ideas-api/` and is built like Wave Defence's `leaderboard-api` suggestions endpoint: strict length limits, a hidden spam trap, 3 ideas per visitor per day, 50 per day in total, escaped text and defused `@mentions`. Visitors' IP addresses are only stored as one-day hashes, never in issues.

1. Create a fine-grained GitHub token with **Issues: Read and write** on `Zephino/Games` only.
2. From `ideas-api/`:

   ```bash
   npm install
   npx wrangler login
   npx wrangler kv namespace create IDEAS_KV
   # paste the id into wrangler.toml and uncomment the [[kv_namespaces]] block
   npx wrangler secret put GITHUB_TOKEN
   npm run deploy
   ```

3. Open `https://<your-worker>.workers.dev/ideas`. It should say `{"accepting":true}`.
4. Paste that Worker URL (without `/ideas`) into `IDEAS_API` at the top of `ideas.js`, then commit.

Run the Worker tests with `npm test` in `ideas-api/`. They also run in GitHub Actions whenever `ideas-api/` changes.

## Adding more games

In `index.html`, duplicate one of the `<article class="card ...">` elements within `<div class="cards">`. Update the displayed game name, genre, status, description, tags, the **Plays on** line (devices and controls), illustration and links to the **official web build** and GitHub repository. The existing responsive styling in `style.css` applies automatically.

A few other places mention the games and need updating too:

- The `02` game count in the hero (`.facts`).
- The `description` and `og:description` meta tags in `<head>`, which name each game.
- `VERSION_URLS` in `versions.js`, plus a `data-version-repo` badge on the new card.
- `social.png`, the 1200×630 preview image shown when the link is shared (Discord, iMessage, X and similar). Regenerate it to include the new game.

## License and copyright

**© 2026 Zephino. All rights reserved.** As with Mythriven and Wave Defence, this project is **source-available, not open-source**. Public visibility does not grant permission to copy, modify, redistribute or commercially exploit the code or assets. See [LICENSE](LICENSE). Individual games keep their own respective licenses.
