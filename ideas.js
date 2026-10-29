/**
 * "Suggest a game" form and public idea board for Zephino Games.
 *
 * Submissions: if IDEAS_API is set and the Worker reports it is accepting,
 * ideas are sent there (no account needed) and become GitHub Issues labelled
 * `game-idea`. Otherwise the form opens a prefilled GitHub issue instead.
 *
 * Board: only issues the developer has labelled `idea-board` are shown, most
 * 👍 reactions first, so nothing unreviewed ever appears on the homepage.
 */
(() => {
  "use strict";

  // Paste the deployed Worker URL here (no trailing slash), e.g.
  // "https://zephino-game-ideas.example.workers.dev". See README.
  const IDEAS_API = "";
  const REPO = "Zephino/Games";
  const BOARD_LABEL = "idea-board";
  const PLANNED_LABEL = "planned";
  const BOARD_SIZE = 6;
  const BOARD_URL = "https://api.github.com/search/issues?q=" +
    encodeURIComponent(`repo:${REPO} is:issue is:open label:${BOARD_LABEL}`) +
    `&sort=reactions-%2B1&order=desc&per_page=${BOARD_SIZE}`;

  const form = document.querySelector("[data-idea-form]");
  const board = document.querySelector("[data-idea-board]");

  /* ---------- Submitting ideas ---------- */

  let apiReady = null; // Promise<boolean>, resolved once per visit.
  function checkApi() {
    if (!IDEAS_API) return Promise.resolve(false);
    if (!apiReady) {
      apiReady = fetch(IDEAS_API + "/ideas", { cache: "no-store" })
        .then((r) => r.ok ? r.json() : {})
        .then((d) => d.accepting === true)
        .catch(() => false);
    }
    return apiReady;
  }

  function githubIssueUrl(data) {
    const params = new URLSearchParams({
      template: "game-idea.yml",
      title: "[Game idea] " + data.title,
      genre: data.genre,
      idea: data.description,
    });
    return `https://github.com/${REPO}/issues/new?` + params.toString();
  }

  function setStatus(text, state) {
    const status = form.querySelector("[data-idea-status]");
    status.textContent = text;
    status.dataset.state = state;
  }

  async function submitIdea(event) {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const fields = form.elements;
    const data = {
      title: fields.title.value.trim(),
      genre: fields.genre.value,
      description: fields.description.value.trim(),
      name: fields.name.value.trim(),
      website: fields.website.value,
    };
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    setStatus("Sending…", "busy");

    try {
      // Without a Worker, open GitHub before any await so Safari treats the
      // new tab as part of the click and doesn't block it.
      if (!IDEAS_API || !(await checkApi())) {
        const url = githubIssueUrl(data);
        window.open(url, "_blank", "noopener");
        setStatus("GitHub opened in a new tab. Press “Create” there to send your idea. ", "ok");
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Didn't open? Click here.";
        form.querySelector("[data-idea-status]").append(link);
        return;
      }
      const response = await fetch(IDEAS_API + "/ideas", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json().catch(() => ({}));
      if (response.status === 201 && result.accepted) {
        form.reset();
        updateCounter();
        setStatus("Thanks! Your idea was sent. I read every one.", "ok");
      } else {
        setStatus("Couldn't send: " + (result.error || "please try again later") + ".", "error");
      }
    } catch {
      setStatus("Couldn't reach the suggestion box. Check your connection and try again.", "error");
    } finally {
      button.disabled = false;
    }
  }

  function updateCounter() {
    const area = form.elements.description;
    form.querySelector("[data-idea-count]").textContent =
      area.value.length + " / " + area.maxLength;
  }

  async function describeRoute() {
    const note = form.querySelector("[data-idea-route]");
    note.textContent = (await checkApi())
      ? "No account needed. Please don't include personal info."
      : "This opens GitHub to post your idea (free account needed).";
  }

  if (form) {
    form.addEventListener("submit", submitIdea);
    form.elements.description.addEventListener("input", updateCounter);
    updateCounter();
    describeRoute();
  }

  /* ---------- Idea board ---------- */

  function genreOf(body) {
    // Worker issues use "**Genre:** X"; GitHub form issues use "### Genre\n\nX".
    const match = /\*\*Genre:\*\*\s*([^\n]+)/.exec(body || "") ||
      /###\s*Genre\s*\n+\s*([^\n]+)/.exec(body || "");
    return match ? match[1].trim().slice(0, 30) : "";
  }

  function renderIdea(issue) {
    const item = document.createElement("li");
    const text = document.createElement("div");
    const title = document.createElement("strong");
    // Always textContent: issue text comes from visitors.
    title.textContent = issue.title.replace(/^\[Game idea\]\s*/i, "");
    text.append(title);

    const meta = document.createElement("span");
    meta.className = "idea-meta";
    const genre = genreOf(issue.body);
    if (genre) meta.append(genre);
    if (issue.labels.some((l) => l.name === PLANNED_LABEL)) {
      const tag = document.createElement("b");
      tag.textContent = "Planned";
      meta.append(tag);
    }
    if (meta.childNodes.length) text.append(meta);

    const vote = document.createElement("a");
    vote.className = "idea-vote";
    vote.href = issue.html_url;
    vote.target = "_blank";
    vote.rel = "noopener noreferrer";
    const votes = issue.reactions ? issue.reactions["+1"] : 0;
    vote.textContent = "👍 " + votes;
    vote.setAttribute("aria-label", `${votes} votes. Vote for this idea on GitHub`);

    item.append(text, vote);
    return item;
  }

  async function loadBoard() {
    try {
      const response = await fetch(BOARD_URL, { headers: { Accept: "application/vnd.github+json" } });
      if (!response.ok) throw new Error("GitHub returned " + response.status);
      const { items = [] } = await response.json();
      board.replaceChildren(...items.map(renderIdea));
      board.dataset.state = items.length ? "loaded" : "empty";
    } catch (error) {
      board.dataset.state = "unavailable";
      console.warn("Failed to load idea board:", error);
    }
  }

  if (board) loadBoard();
})();
