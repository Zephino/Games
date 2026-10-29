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

Every idea becomes a GitHub Issue in this repository titled `[Game idea] …`, so they all land in one inbox: [open game ideas](https://github.com/Zephino/Games/issues?q=is%3Aissue+is%3Aopen+%22%5BGame+idea%5D%22+in%3Atitle). Ideas are never shown publicly on the homepage. The Worker also tries to add a `game-idea` label. Create it once under [Issues → Labels](https://github.com/Zephino/Games/labels). If GitHub doesn't apply it, the idea still arrives with the title prefix.

The form sends ideas straight to a small Cloudflare Worker in `ideas-api/`, so visitors never need an account or leave the page. It's built like Wave Defence's `leaderboard-api` suggestions endpoint: strict length limits, a hidden spam trap, 3 ideas per visitor per day, 50 per day in total, escaped text and defused `@mentions`. Visitors' IP addresses are only stored as one-day hashes, never in issues. People already on GitHub can also use the **Suggest a game** issue form (`.github/ISSUE_TEMPLATE/game-idea.yml`).

### Setting up the ideas Worker (one time, all in the browser)

1. **GitHub token.** Go to [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new). Name it `zephino-game-ideas`. Under **Repository access**, choose **Only select repositories → Zephino/Games**. Under **Permissions → Repository permissions**, set **Issues** to **Read and write**. Generate it and copy the token. Don't share it with anyone, including in chat.
2. **KV storage** (for the daily limits). In the [Cloudflare dashboard](https://dash.cloudflare.com/), open **Storage & Databases → KV** and create a namespace called `IDEAS_KV`.
3. **Create the Worker.** Open **Compute (Workers) → Workers & Pages → Create → Worker**, start from **Hello World**, name it `zephino-game-ideas` and deploy. Click **Edit code**, replace everything with the contents of [`ideas-api/src/index.mjs`](ideas-api/src/index.mjs), and click **Deploy**.
4. **Connect the storage.** In the Worker's **Settings → Bindings**, add a **KV namespace** binding. Set the variable name to `IDEAS_KV` and pick the `IDEAS_KV` namespace.
5. **Add the token.** In **Settings → Variables and Secrets**, add a variable of type **Secret** named `GITHUB_TOKEN` and paste the token from step 1.
6. **Check it.** Open `https://zephino-game-ideas.<your-subdomain>.workers.dev/ideas`. It should show `{"accepting":true}`.
7. **Connect the homepage.** Put that Worker address (without `/ideas`) into `IDEAS_API` at the top of `ideas.js` and commit. The address isn't secret.

Until step 7 is done, the form says it couldn't reach the suggestion box.

If you prefer the command line, `ideas-api/` also works with Wrangler: `npm install`, `npx wrangler login`, `npx wrangler kv namespace create IDEAS_KV` (paste the id into `wrangler.toml`), `npx wrangler secret put GITHUB_TOKEN`, then `npm run deploy`.

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
