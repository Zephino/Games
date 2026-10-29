/**
 * "Suggest a game" pop-up for Zephino Games.
 *
 * Any [data-open-ideas] link opens the dialog, as does visiting the page with
 * #suggest (or the older #ideas) in the URL.
 *
 * Submissions go straight to the ideas Worker (no account needed), which
 * files each one as a GitHub Issue labelled `game-idea`. See README.
 */
(() => {
  "use strict";

  // Paste the deployed Worker URL here (no trailing slash), e.g.
  // "https://zephino-game-ideas.example.workers.dev". See README.
  const IDEAS_API = "https://zephino-game-ideas.thebotcoder.workers.dev";

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
      if (!IDEAS_API) throw new Error("IDEAS_API is not set");
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

  form.addEventListener("submit", submitIdea);
  form.elements.description.addEventListener("input", updateCounter);
  updateCounter();

  if (location.hash === "#suggest" || location.hash === "#ideas") openModal();
})();
