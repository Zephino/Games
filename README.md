# Zephino Games

**The home for games by Zephino.** This repository hosts a lightweight, responsive game launcher at [zephino.github.io/Games](https://zephino.github.io/Games/) once GitHub Pages has been enabled.

## Games

| Game | Browser build | Source / information |
| --- | --- | --- |
| **Mythriven** | [Play Mythriven](https://zephino.github.io/Mythriven/) | [Zephino/Mythriven](https://github.com/Zephino/Mythriven) |
| **Wave Defence** | [Play Wave Defence](https://zephino.github.io/WaveDefence/) | [Zephino/WaveDefence](https://github.com/Zephino/WaveDefence) |

Both are works in progress. Their browser builds are hosted in their respective repositories; the launcher does not copy or embed the game files.

## Publish the launcher

1. Open [Settings → Pages](https://github.com/Zephino/Games/settings/pages).
2. Under **Build and deployment**, choose **GitHub Actions** as the source.
3. The included `.github/workflows/pages.yml` deploys the static site whenever `main` is updated, or when started manually from the **Actions** tab.
4. Visit <https://zephino.github.io/Games/> after a successful deployment.

The site is plain HTML/CSS; no package installs, build dependencies, API keys, trackers, or external fonts are required.

## Add more games

Copy a `<article class="game-card ...">` block in `index.html` into the `#games` grid, then update the title, description, tags, illustration reference, and **official play** and **repository** URLs. Add a new SVG illustration in `assets/` (or use existing art you have the rights to use), and add a matching `game-card--...` CSS accent style if desired. Keep links pointing to the game's authorized hosted build rather than storing game builds in this repository.

The artwork in this repo is stylized, original decorative **portal artwork**, not screenshots of the live games.

## Copyright and licensing

**© 2026 Zephino. All rights reserved.** This is a publicly viewable, source-available project, **not** an open-source grant. You can visit and use the official hosted site, but cannot copy, modify, redistribute, or commercially exploit its code, design, or assets without permission. See [LICENSE](LICENSE). The games linked from this site remain under their respective licenses.
