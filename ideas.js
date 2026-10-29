/**
 * "Suggest a game" form for Zephino Games.
 *
 * Submissions: if IDEAS_API is set and the Worker reports it is accepting,
 * ideas are sent there (no account needed) and become GitHub Issues labelled
 * `game-idea`. Otherwise the form opens a prefilled GitHub issue instead.
 */
(() => {
  "use strict";

  // Paste the deployed Worker URL here (no trailing slash), e.g.
  // "https://zephino-game-ideas.example.workers.dev". See README.
  const IDEAS_API = "";
  const REPO = "Zephino/Games";

  const form = document.querySelector("[data-idea-form]");

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
})();
