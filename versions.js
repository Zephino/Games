/**
 * Live versions for the games listed on Zephino Games.
 *
 * Source of truth: each game's VERSION file on the default main branch.
 * A fresh request is made when the page is opened and every 5 minutes while
 * it is visible. No GitHub token, server, manual edit, or rebuild is needed.
 *
 * These are source repository versions; a web build may still be deploying.
 */
(() => {
  "use strict";

  const VERSION_URLS = Object.freeze({
    Mythriven: "https://raw.githubusercontent.com/Zephino/Mythriven/main/VERSION",
    WaveDefence: "https://raw.githubusercontent.com/Zephino/WaveDefence/main/VERSION"
  });
  const REFRESH_INTERVAL_MS = 5 * 60 * 1000;
  const VERSION_PATTERN = /^v?\d+(?:\.\d+){1,4}(?:[-+][a-zA-Z0-9.-]+)?$/;

  const badges = Array.from(document.querySelectorAll("[data-version-repo]"));
  let lastRefresh = 0;

  async function updateBadge(badge) {
    const repo = badge.dataset.versionRepo;
    const sourceUrl = VERSION_URLS[repo];
    if (!sourceUrl) return;

    try {
      // Bypass browser caches so releases appear without redeploying Games.
      const response = await fetch(sourceUrl, { cache: "no-store", mode: "cors" });
      if (!response.ok) throw new Error("GitHub returned " + response.status);

      const version = (await response.text()).trim();
      if (!VERSION_PATTERN.test(version)) throw new Error("Invalid VERSION file");

      // Always use textContent for externally fetched data.
      const label = "Version " + version;
      if (badge.textContent !== label) badge.textContent = label;
      badge.dataset.versionState = "loaded";
      badge.title = "Latest version on " + repo + "'s GitHub main branch (web deployment may take longer)";
    } catch (error) {
      // Preserve an already-loaded version if a later refresh goes offline.
      if (badge.dataset.versionState !== "loaded") {
        badge.textContent = "Version unavailable";
        badge.dataset.versionState = "unavailable";
        badge.title = "Could not read the VERSION file from GitHub; check your connection";
      }
      console.warn("Failed to load " + repo + " VERSION:", error);
    }
  }

  function refreshVersions() {
    if (document.visibilityState === "hidden") return;
    lastRefresh = Date.now();
    for (const badge of badges) void updateBadge(badge);
  }

  // Initial render: fetch fresh values from each game's own repo.
  refreshVersions();

  // If the user leaves this page open, keep the versions current.
  window.setInterval(refreshVersions, REFRESH_INTERVAL_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" &&
        Date.now() - lastRefresh >= REFRESH_INTERVAL_MS) {
      refreshVersions();
    }
  });
})();
