import { test } from "node:test";
import assert from "node:assert/strict";
import worker, { handleIdeaPost, ideasStatus, validateIdea } from "../src/index.mjs";

const payload = {
  title: "Space station builder",
  genre: "Simulation",
  description: "Build and run a space station, keep the crew alive and trade with passing ships.",
  name: "Sam",
  website: "",
};
function env() {
  const data = new Map();
  return {
    GITHUB_TOKEN: "test-token",
    GITHUB_OWNER: "Zephino",
    GITHUB_REPO: "Games",
    IDEAS_KV: {
      async get(key) { return data.get(key) ?? null; },
      async put(key, value) { data.set(key, value); },
    },
    _data: data,
  };
}
function request(p = payload) {
  return new Request("https://example.workers.dev/ideas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(p),
  });
}
function github(status = 201, calls = []) {
  return async (url, init) => {
    calls.push({ url, body: JSON.parse(init.body) });
    return new Response(JSON.stringify({ number: 7 }), { status });
  };
}

test("validates genre, title, description, name, honeypot and links", () => {
  assert.equal(validateIdea(payload).error, undefined);
  assert.equal(validateIdea({ ...payload, name: "" }).error, undefined);
  assert.ok(validateIdea({ ...payload, genre: "Admin" }).error);
  assert.ok(validateIdea({ ...payload, title: "hi" }).error);
  assert.ok(validateIdea({ ...payload, description: "too short" }).error);
  assert.ok(validateIdea({ ...payload, name: "<script>" }).error);
  assert.ok(validateIdea({ ...payload, website: "spam.example" }).error);
  assert.ok(validateIdea({ ...payload, description: "a".repeat(30) + " http://a http://b http://c" }).error);
  assert.ok(validateIdea([]).error);
});

test("reports not accepting until configured", async () => {
  assert.equal((await ideasStatus({}).json()).accepting, false);
  assert.equal((await ideasStatus(env()).json()).accepting, true);
  const res = await handleIdeaPost(request(), {}, "1.1.1.1", github());
  assert.equal(res.status, 503);
});

test("creates a labelled issue with escaped text and defused mentions", async () => {
  const calls = [];
  const res = await handleIdeaPost(
    request({ ...payload, description: "Ping @someone <b>bold</b> and **stars** please" }),
    env(), "1.1.1.1", github(201, calls));
  assert.equal(res.status, 201);
  assert.deepEqual(await res.json(), { accepted: true, issue_number: 7 });
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /repos\/Zephino\/Games\/issues$/);
  const issue = calls[0].body;
  assert.equal(issue.title, "[Game idea] Space station builder");
  assert.deepEqual(issue.labels, ["game-idea"]);
  assert.ok(!issue.body.includes("@someone"));
  assert.ok(!issue.body.includes("<b>"));
  assert.ok(issue.body.includes("\\*\\*stars\\*\\*"));
  assert.ok(issue.body.includes("**Genre:** Simulation"));
});

test("retries without labels when GitHub refuses them", async () => {
  const calls = [];
  let n = 0;
  const fetcher = async (url, init) => {
    calls.push(JSON.parse(init.body));
    return new Response("{}", { status: n++ === 0 ? 422 : 201 });
  };
  const res = await handleIdeaPost(request(), env(), "1.1.1.1", fetcher);
  assert.equal(res.status, 201);
  assert.equal(calls.length, 2);
  assert.equal(calls[1].labels, undefined);
});

test("never claims success when GitHub fails", async () => {
  const res = await handleIdeaPost(request(), env(), "1.1.1.1", github(401));
  assert.equal(res.status, 502);
});

test("enforces the per-visitor daily limit", async () => {
  const e = env();
  for (let i = 0; i < 3; i++) {
    assert.equal((await handleIdeaPost(request(), e, "2.2.2.2", github())).status, 201);
  }
  assert.equal((await handleIdeaPost(request(), e, "2.2.2.2", github())).status, 429);
  assert.equal((await handleIdeaPost(request(), e, "3.3.3.3", github())).status, 201);
  assert.ok([...e._data.keys()].every((k) => !k.includes("2.2.2.2")));
});

test("rejects oversized bodies and unknown routes", async () => {
  const big = await handleIdeaPost(request({ ...payload, description: "x".repeat(7000) }), env(), "1.1.1.1", github());
  assert.equal(big.status, 413);
  const res = await worker.fetch(new Request("https://example.workers.dev/other"), env());
  assert.equal(res.status, 404);
  const pre = await worker.fetch(new Request("https://example.workers.dev/ideas", { method: "OPTIONS" }), env());
  assert.equal(pre.headers.get("Access-Control-Allow-Origin"), "*");
});

test("strips invisible and direction-spoofing characters", () => {
  const sneaky = { ...payload, title: "Space​ sta‮tion﻿", description: "Keep⁠ the crew‍ alive on a tiny station." };
  const checked = validateIdea(sneaky);
  assert.equal(checked.title, "Space station");
  assert.ok(!/[​-‏‪-‮⁠-⁩﻿]/.test(checked.description));
});

test("drops backticks from titles so they can't render as code", async () => {
  const calls = [];
  await handleIdeaPost(request({ ...payload, title: "`rm -rf` simulator" }), env(), "1.1.1.1", github(201, calls));
  assert.equal(calls[0].body.title, "[Game idea] 'rm -rf' simulator");
});

test("treats SQL-injection text as plain text (there is no database)", async () => {
  const attack = "Robert'); DROP TABLE ideas;-- and 1=1 OR '1'='1' UNION SELECT * FROM users";
  const checked = validateIdea({ ...payload, title: "x'; DROP TABLE ideas;--", description: attack });
  assert.equal(checked.error, undefined);
  const calls = [];
  const res = await handleIdeaPost(request({ ...payload, description: attack }), env(), "1.1.1.1", github(201, calls));
  assert.equal(res.status, 201);
  // It reaches GitHub only as escaped, quoted Markdown text.
  const body = calls[0].body.body;
  assert.ok(body.includes("> Robert'\\); DROP TABLE ideas;\\-\\- and 1=1 OR '1'='1' UNION SELECT \\* FROM users"));
});

test("rejects non-string and wrongly shaped fields", () => {
  assert.ok(validateIdea({ ...payload, title: { $ne: "" } }).error);
  assert.ok(validateIdea({ ...payload, description: ["a".repeat(30)] }).error);
  assert.ok(validateIdea({ ...payload, genre: 1 }).error);
  assert.ok(validateIdea(null).error);
  assert.ok(validateIdea("text").error);
});
