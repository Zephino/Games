/**
 * Anonymous "Suggest a game" box for the Zephino Games homepage.
 *
 * Each accepted idea becomes a GitHub Issue in Zephino/Games labelled
 * `game-idea`, created with a server-side token. Visitors need no account,
 * email or token. Ideas are never shown on the homepage.
 *
 * Defence in depth: strict field limits, a honeypot field, per-IP and global
 * daily caps. Cloudflare KV caps are best-effort, not atomic bot protection.
 */
export const GENRES = Object.freeze([
  "Action", "Adventure", "Roguelike", "Tower defence", "Strategy", "Puzzle",
  "Platformer", "RPG", "Racing", "Sports", "Simulation", "Horror", "Other",
]);

const MAX_BODY_BYTES = 6000;
const MAX_TITLE = 80;
const MAX_DESCRIPTION = 1500;
const MAX_NAME = 24;
const DAILY_IP_LIMIT = 3;
const DAILY_GLOBAL_LIMIT = 50;
const IDEA_LABEL = "game-idea";

const jsonHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Accept",
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
};

function reply(value, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: jsonHeaders });
}

/**
 * Treat all visitor text as untrusted. Keep natural language (quotes,
 * semicolons) but remove non-printing and text-direction spoofing controls,
 * and defuse @mentions so a suggestion can't notify GitHub users.
 */
function clean(value) {
  if (typeof value !== "string") return "";
  return value.normalize("NFC")
    .replace(/\r\n?|\u2028|\u2029/g, "\n")
    .replace(/\t/g, " ")
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g, "")
    .replace(/@/g, "\uff20")
    .trim();
}

export function validateIdea(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return { error: "invalid suggestion" };
  }
  // Invisible spam trap; the homepage form always sends an empty string.
  if (body.website !== undefined && body.website !== "") {
    return { error: "invalid suggestion" };
  }
  const title = clean(body.title).replace(/\s+/g, " ");
  const genre = clean(body.genre);
  const description = clean(body.description);
  const name = clean(body.name).replace(/\s+/g, " ");
  if (!GENRES.includes(genre)) return { error: "please pick a genre" };
  if (title.length < 3 || title.length > MAX_TITLE) {
    return { error: `the idea's name must be 3–${MAX_TITLE} characters` };
  }
  if (description.length < 20 || description.length > MAX_DESCRIPTION) {
    return { error: `the description must be 20–${MAX_DESCRIPTION} characters` };
  }
  if ((description.match(/https?:\/\//gi) || []).length > 2) {
    return { error: "too many links" };
  }
  // Display names are optional and allowlisted: letters, digits, space, _ . -
  if (name && (name.length > MAX_NAME || !/^[\p{L}\p{N} _.-]+$/u.test(name))) {
    return { error: `names can use letters, numbers, spaces, _ . - (max ${MAX_NAME})` };
  }
  return { title, genre, description, name };
}

/** Escape visitor content before inserting it in a GitHub Markdown issue. */
function escapeIssueText(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/([\\\x60*_{}\[\]()#+.!|~-])/g, "\\$1");
}

function markdownQuote(text) {
  return escapeIssueText(text).split("\n").map((line) => "> " + line).join("\n");
}

async function keyFor(ip, env, day) {
  // Hash identifiers in KV so raw IP addresses aren't stored as keys.
  const input = new TextEncoder().encode(`${day}:${ip}:${env.GITHUB_TOKEN}`);
  const digest = await crypto.subtle.digest("SHA-256", input);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

export function ideasStatus(env) {
  return reply({ accepting: Boolean(env.GITHUB_TOKEN && env.IDEAS_KV) });
}

/**
 * Request handler, factored so tests can inject a fake GitHub fetch.
 * A GitHub 201 response is the only success: never claim an idea was
 * delivered when GitHub rejected it or the Worker is unconfigured.
 */
export async function handleIdeaPost(request, env, ip, githubFetch = fetch) {
  if (!env.GITHUB_TOKEN || !env.IDEAS_KV) {
    return reply({ error: "suggestion service not configured" }, 503);
  }
  const declared = Number(request.headers.get("content-length") || 0);
  if (declared > MAX_BODY_BYTES) return reply({ error: "message too large" }, 413);
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > MAX_BODY_BYTES) {
    return reply({ error: "message too large" }, 413);
  }
  let incoming;
  try { incoming = JSON.parse(raw); }
  catch { return reply({ error: "invalid json" }, 400); }

  const checked = validateIdea(incoming);
  if (checked.error) return reply({ error: checked.error }, 400);

  const day = new Date().toISOString().slice(0, 10);
  const ipKey = "idea:ip:" + await keyFor(ip, env, day);
  const globalKey = "idea:global:" + day;
  const [ipCount, globalCount] = await Promise.all([
    env.IDEAS_KV.get(ipKey),
    env.IDEAS_KV.get(globalKey),
  ]);
  if (Number(ipCount || 0) >= DAILY_IP_LIMIT || Number(globalCount || 0) >= DAILY_GLOBAL_LIMIT) {
    return reply({ error: "daily suggestion limit reached; try again tomorrow" }, 429);
  }

  const owner = env.GITHUB_OWNER || "Zephino";
  const repo = env.GITHUB_REPO || "Games";
  const issue = {
    title: `[Game idea] ${checked.title}`,
    labels: [IDEA_LABEL],
    body: [
      "Anonymous game idea from the **Zephino Games** homepage.",
      "",
      `**Genre:** ${checked.genre}`,
      `**Suggested by:** ${checked.name ? escapeIssueText(checked.name) : "Anonymous"}`,
      "",
      "**The idea:**",
      markdownQuote(checked.description),
      "",
      "*Submitted without an account. Please do not post personal information.*",
    ].join("\n"),
  };
  const createIssue = (payload) => githubFetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      "User-Agent": "zephino-game-ideas-worker",
    },
    body: JSON.stringify(payload),
  });

  let response;
  try {
    response = await createIssue(issue);
    // A token without label rights gets 403/422; still deliver the idea.
    if (response.status === 403 || response.status === 422) {
      const { labels, ...unlabelled } = issue;
      response = await createIssue(unlabelled);
    }
  } catch {
    return reply({ error: "could not reach the suggestion service" }, 502);
  }
  if (response.status !== 201) {
    // Log only the status; never echo the token or GitHub's response body.
    console.log("Create GitHub issue failed:", response.status);
    return reply({ error: "GitHub could not save the idea (status " + response.status + "). Please try again later." }, 502);
  }

  // Caps are intentionally best-effort: KV read-modify-write is not atomic.
  try {
    await Promise.all([
      env.IDEAS_KV.put(ipKey, String(Number(ipCount || 0) + 1), { expirationTtl: 90000 }),
      env.IDEAS_KV.put(globalKey, String(Number(globalCount || 0) + 1), { expirationTtl: 90000 }),
    ]);
  } catch (err) {
    console.log("Idea rate counter write failed:", String(err));
  }
  const result = await response.json().catch(() => ({}));
  return reply({ accepted: true, issue_number: Number(result.number || 0) }, 201);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: jsonHeaders });
    const url = new URL(request.url);
    if (url.pathname !== "/ideas") return reply({ error: "not found" }, 404);
    if (request.method === "GET") return ideasStatus(env);
    if (request.method !== "POST") return reply({ error: "method not allowed" }, 405);
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    try {
      return await handleIdeaPost(request, env, ip);
    } catch (err) {
      console.log("Idea handler failed:", String(err));
      return reply({ error: "something went wrong; please try again later" }, 500);
    }
  },
};
