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

The source is a lightweight static website with `index.html` and `style.css` at the repository root. There are no build dependencies, API keys, user trackers or external fonts.

If GitHub Pages is already set to **Deploy from a branch (main / root)**, GitHub will deploy the index file when the branch updates. If it is set to **GitHub Actions**, the included `.github/workflows/pages.yml` automatically builds and publishes the site on every push to `main`. The workflow also supports manual runs.

Check publishing status at [Actions](https://github.com/Zephino/Games/actions) or [Settings → Pages](https://github.com/Zephino/Games/settings/pages). Successful hosting should appear at <https://zephino.github.io/Games/>.

## Automatic game versions

The homepage reads the version number directly from each public game's `VERSION` file on the `main` branch:

- [Mythriven/VERSION](https://github.com/Zephino/Mythriven/blob/main/VERSION)
- [WaveDefence/VERSION](https://github.com/Zephino/WaveDefence/blob/main/VERSION)

`versions.js` requests those files from GitHub when the homepage opens, then checks again every five minutes while the page is visible. It deliberately bypasses the browser cache and uses plain text for display. **You do not need to update or redeploy the Games homepage when a game's VERSION file changes.** No API key or backend is needed. If GitHub cannot be reached, the card says `Version unavailable` (or keeps the last successfully loaded version for that visit).

The displayed number is the version **on the game's GitHub `main` branch**. The playable web build may temporarily be older while its GitHub Pages deployment runs.

## Adding more games

In `index.html`, duplicate one of the `<article class="card ...">` elements within `<div class="cards">`. Update the displayed game name, description, features, illustration and links to the **official web build** and GitHub repository. The existing responsive styling in `style.css` applies automatically.

## License and copyright

**© 2026 Zephino. All rights reserved.** As with Mythriven and Wave Defence, this project is **source-available, not open-source**. Public visibility does not grant permission to copy, modify, redistribute or commercially exploit the code or assets. See [LICENSE](LICENSE). Individual games keep their own respective licenses.
