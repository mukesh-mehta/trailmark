import test from "node:test";
import assert from "node:assert/strict";
import { filterResources, summarize, parseTags } from "../trailmark/static/library.js";

const resources = [
  { id: 1, title: "Python basics", url: "https://example.com/python", notes: "Practice generators", tags: ["python", "backend"], status: "learning", kind: "course", favorite: true, created_at: "2026-01-01" },
  { id: 2, title: "Accessible interfaces", url: "https://example.com/a11y", notes: "Keyboard focus", tags: ["design"], status: "completed", kind: "article", favorite: false, created_at: "2026-01-02" },
  { id: 3, title: "JavaScript guide", url: "https://example.com/js", notes: "Web fundamentals", tags: ["web"], status: "queued", kind: "book", favorite: true, created_at: "2026-01-02" },
];

test("search matches words across titles, notes, URLs, and tags, ignoring case", () => {
  assert.deepEqual(filterResources(resources, { query: " PYTHON generators " }).map(x => x.id), [1]);
  assert.deepEqual(filterResources(resources, { query: "example.com/a11y" }).map(x => x.id), [2]);
  assert.equal(filterResources(resources, { query: "not-present" }).length, 0);
});

test("filters intersect rather than replacing one another", () => {
  assert.deepEqual(filterResources(resources, { view: "favorites", kind: "course", tag: "backend", status: "learning" }).map(x => x.id), [1]);
  assert.equal(filterResources(resources, { view: "learning", status: "completed" }).length, 0);
  assert.deepEqual(filterResources(resources, { view: "completed" }).map(x => x.id), [2]);
});

test("sorting is stable and does not mutate the original library", () => {
  assert.deepEqual(filterResources(resources).map(x => x.id), [3, 2, 1]);
  assert.deepEqual(filterResources(resources, { sort: "oldest" }).map(x => x.id), [1, 2, 3]);
  assert.deepEqual(filterResources(resources, { sort: "title" }).map(x => x.id), [2, 3, 1]);
  assert.deepEqual(resources.map(x => x.id), [1, 2, 3]);
});

test("dashboard totals handle empty and mixed libraries", () => {
  assert.deepEqual(summarize([]), { total: 0, learning: 0, completed: 0, favorites: 0, rate: 0 });
  assert.deepEqual(summarize(resources), { total: 3, learning: 1, completed: 1, favorites: 2, rate: 33 });
});

test("tag parsing trims, normalizes, and deduplicates", () => {
  assert.deepEqual(parseTags(" Python,web, python, , WEB "), ["python", "web"]);
  assert.deepEqual(parseTags(" , "), []);
});
