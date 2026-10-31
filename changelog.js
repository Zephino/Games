/**
 * Changelog pop-up for the games on Zephino Games.
 *
 * Source of truth: each game's CHANGELOG.md on its main branch (the same
 * place versions.js reads VERSION from), so new entries show up without
 * touching this site. [data-open-log="<Repo>"] opens it, as does visiting
 * the page with #changelog-<repo> (for example #changelog-mythriven).
 *
 * Changelog text is rendered with textContent only, never as HTML.
 */
(() => {
  "use strict";

  const GAMES = Object.freeze({
    Mythriven: "Mythriven",
    WaveDefence: "Wave Defence",
  });
  const PAGE_SIZE = 8;

  const modal = document.querySelector("[data-log-modal]");
  if (!modal || typeof modal.showModal !== "function") return;
  const list = modal.querySelector("[data-log-list]");
  const more = modal.querySelector("[data-log-more]");
  const status = modal.querySelector("[data-log-status]");

  const cache = {}; // repo -> Promise<entries[]>
  let current = null; // { repo, entries, shown }

  const rawUrl = (repo) => `https://raw.githubusercontent.com/Zephino/${repo}/main/CHANGELOG.md`;
  const pageUrl = (repo) => `https://github.com/Zephino/${repo}/blob/main/CHANGELOG.md`;

  /* ---------- Parsing ---------- */

  // Entries look like: "## Version X", "Date: …", "Time: …", then
  // "### Changes" / "### Reason" sections of bullets or paragraphs.
  function parseChangelog(text) {
    const entries = [];
    let entry = null;
    let section = null;
    for (const line of text.replace(/\r\n?/g, "\n").split("\n")) {
      const version = /^##\s+Version\s+(.+?)\s*$/.exec(line);
      if (version) {
        entry = { version: version[1], date: "", time: "", sections: [] };
        entries.push(entry);
        section = null;
        continue;
      }
      if (!entry) continue;
      const meta = /^(Date|Time):\s*(.+?)\s*$/.exec(line);
      if (meta && !section) {
        entry[meta[1].toLowerCase()] = meta[2];
        continue;
      }
      const heading = /^###\s+(.+?)\s*$/.exec(line);
      if (heading) {
        section = { title: heading[1], blocks: [] };
        entry.sections.push(section);
        continue;
      }
      if (!line.trim()) continue;
      if (!section) {
        section = { title: "", blocks: [] };
        entry.sections.push(section);
      }
      const bullet = /^(\s*)[-*]\s+(.*)$/.exec(line);
      const last = section.blocks[section.blocks.length - 1];
      if (bullet) {
        section.blocks.push({ type: "item", depth: Math.floor(bullet[1].length / 2), text: bullet[2] });
      } else if (last && /^\s/.test(line)) {
        last.text += " " + line.trim(); // wrapped continuation line
      } else {
        section.blocks.push({ type: "para", text: line.trim() });
      }
    }
    return entries;
  }

  /* ---------- Rendering (text only) ---------- */

  // Supports **bold** and `code`; [text](url) links show their text only.
  function appendInline(parent, text) {
    const plain = text.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1");
    const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let index = 0;
    for (const match of plain.matchAll(pattern)) {
      if (match.index > index) parent.append(plain.slice(index, match.index));
      const token = match[0];
      const el = document.createElement(token.startsWith("**") ? "strong" : "code");
      el.textContent = token.startsWith("**") ? token.slice(2, -2) : token.slice(1, -1);
      parent.append(el);
      index = match.index + token.length;
    }
    if (index < plain.length) parent.append(plain.slice(index));
  }

  function renderBlocks(blocks) {
    const frag = document.createDocumentFragment();
    const stack = []; // open <ul> per depth
    for (const block of blocks) {
      if (block.type === "para") {
        stack.length = 0;
        const p = document.createElement("p");
        appendInline(p, block.text);
        frag.append(p);
        continue;
      }
      const depth = Math.min(block.depth, stack.length); // never skip a level
      if (stack.length > depth + 1) stack.length = depth + 1; // close deeper lists
      if (!stack[depth]) {
        const ul = document.createElement("ul");
        if (depth === 0) frag.append(ul);
        else stack[depth - 1].lastElementChild.append(ul);
        stack[depth] = ul;
      }
      const li = document.createElement("li");
      appendInline(li, block.text);
      stack[depth].append(li);
    }
    return frag;
  }

  function renderEntry(entry, isLatest) {
    const article = document.createElement("article");
    article.className = "log-entry";
    const head = document.createElement("header");
    const h3 = document.createElement("h3");
    h3.textContent = "Version " + entry.version;
    if (isLatest) {
      const tag = document.createElement("span");
      tag.className = "log-latest";
      tag.textContent = "Latest";
      h3.append(" ", tag);
    }
    head.append(h3);
    const when = [entry.date, entry.time].filter(Boolean).join(" · ");
    if (when) {
      const time = document.createElement("p");
      time.className = "log-when";
      time.textContent = when;
      head.append(time);
    }
    article.append(head);
    for (const section of entry.sections) {
      const box = document.createElement("div");
      box.className = "log-section" + (/^reason$/i.test(section.title) ? " log-reason" : "");
      if (section.title) {
        const h4 = document.createElement("h4");
        h4.textContent = /^reason$/i.test(section.title) ? "Why" : section.title;
        box.append(h4);
      }
      box.append(renderBlocks(section.blocks));
      article.append(box);
    }
    return article;
  }

  function showMore() {
    const next = current.entries.slice(current.shown, current.shown + PAGE_SIZE);
    list.append(...next.map((entry, i) => renderEntry(entry, current.shown + i === 0)));
    current.shown += next.length;
    more.hidden = current.shown >= current.entries.length;
  }

  function load(repo) {
    if (!cache[repo]) {
      cache[repo] = fetch(rawUrl(repo), { cache: "no-cache" })
        .then((response) => {
          if (!response.ok) throw new Error("GitHub returned " + response.status);
          return response.text();
        })
        .then(parseChangelog);
      cache[repo].catch(() => { delete cache[repo]; }); // let a later open retry
    }
    return cache[repo];
  }

  async function fill(repo) {
    list.replaceChildren();
    more.hidden = true;
    status.textContent = "Loading updates…";
    status.dataset.state = "busy";
    try {
      const entries = await load(repo);
      if (!current || current.repo !== repo) return; // closed or switched meanwhile
      if (!entries.length) throw new Error("no entries found");
      current.entries = entries;
      status.textContent = "";
      status.dataset.state = "";
      showMore();
    } catch (error) {
      if (!current || current.repo !== repo) return;
      status.textContent = "Couldn't load the changelog right now. You can still read it on GitHub below.";
      status.dataset.state = "error";
      console.warn("Failed to load " + repo + " changelog:", error);
    }
  }

  /* ---------- Opening and closing ---------- */

  let closeToken = 0; // Bumped on open so a pending close is abandoned.

  function openLog(repo) {
    if (!GAMES[repo]) return;
    closeToken++;
    modal.classList.remove("closing");
    current = { repo, entries: [], shown: 0 };
    modal.querySelector("[data-log-title]").textContent = GAMES[repo];
    modal.querySelector("[data-log-full]").href = pageUrl(repo);
    modal.querySelector(".modal-inner").scrollTop = 0;
    if (!modal.open) modal.showModal();
    modal.querySelector(".modal-close").focus();
    fill(repo);
  }

  function closeLog() {
    if (!modal.open || modal.classList.contains("closing")) return;
    modal.classList.add("closing");
    const token = closeToken;
    const finish = () => {
      if (token !== closeToken || !modal.classList.contains("closing")) return;
      modal.classList.remove("closing");
      modal.close();
      current = null;
    };
    modal.addEventListener("animationend", finish, { once: true });
    setTimeout(finish, 300);
  }

  for (const trigger of document.querySelectorAll("[data-open-log]")) {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      openLog(trigger.dataset.openLog);
    });
  }
  modal.querySelector("[data-close-log]").addEventListener("click", closeLog);
  // A click on the dialog element itself (not its content) is the backdrop.
  modal.addEventListener("click", (event) => { if (event.target === modal) closeLog(); });
  modal.addEventListener("cancel", (event) => { event.preventDefault(); closeLog(); });
  more.addEventListener("click", showMore);

  const hashRepo = Object.keys(GAMES).find((repo) => location.hash.toLowerCase() === "#changelog-" + repo.toLowerCase());
  if (hashRepo) openLog(hashRepo);
})();
