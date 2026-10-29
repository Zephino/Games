/**
 * "Suggest a game" pop-up for Zephino Games.
 *
 * Any [data-open-ideas] link opens the dialog, as does visiting the page with
 * #suggest (or the older #ideas) in the URL.
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

  const modal = document.querySelector("[data-idea-modal]");
  if (!modal || typeof modal.showModal !== "function") return;
  const form = modal.querySelector("[data-idea-form]");

  /* ---------- Opening and closing ---------- */

  function showView(name) {
    for (const view of modal.querySelectorAll("[data-view]")) {
      view.hidden = view.dataset.view !== name;
    }
    if (name !== "form") modal.querySelector(`[data-view="${name}"] h2`).focus();
  }

  let closeToken = 0; // Bumped on open so a pending close is abandoned.

  function openModal() {
    closeToken++;
    if (modal.classList.contains("closing")) {
      // Reopened mid close animation: just stay open.
      modal.classList.remove("closing");
      return;
    }
    if (modal.open) return;
    showView("form");
    setStatus("", "");
    modal.showModal();
    // Skip auto-focusing the text box on touch screens so the keyboard
    // doesn't cover the window the moment it opens.
    if (window.matchMedia("(pointer: fine)").matches) form.elements.title.focus();
    else modal.querySelector(".modal-close").focus();
  }

  function closeModal() {
    if (!modal.open || modal.classList.contains("closing")) return;
    modal.classList.add("closing");
    const token = closeToken;
    const finish = () => {
      if (token !== closeToken || !modal.classList.contains("closing")) return;
      modal.classList.remove("closing");
      modal.close();
    };
    modal.addEventListener("animationend", finish, { once: true });
    setTimeout(finish, 300);
  }

  for (const trigger of document.querySelectorAll("[data-open-ideas]")) {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      openModal();
    });
  }
  for (const button of modal.querySelectorAll("[data-close-ideas]")) {
    button.addEventListener("click", closeModal);
  }
  // A click on the dialog element itself (not its content) is the backdrop.
  modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
  modal.addEventListener("cancel", (event) => { event.preventDefault(); closeModal(); });
  modal.querySelector("[data-idea-again]").addEventListener("click", () => {
    showView("form");
    form.elements.title.focus();
  });

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

  function resetForm() {
    form.reset();
    updateCounter();
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
        modal.querySelector("[data-github-link]").href = url;
        setStatus("", "");
        resetForm();
        showView("github");
        return;
      }
      const response = await fetch(IDEAS_API + "/ideas", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json().catch(() => ({}));
      if (response.status === 201 && result.accepted) {
        setStatus("", "");
        resetForm();
        showView("sent");
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
      : "Opens GitHub to post it (free account needed).";
  }

  form.addEventListener("submit", submitIdea);
  form.elements.description.addEventListener("input", updateCounter);
  updateCounter();
  describeRoute();

  if (location.hash === "#suggest" || location.hash === "#ideas") openModal();
})();
