import { filterResources, summarize, parseTags, STATUS_LABELS, KIND_LABELS } from "./library.js";

const $ = selector => document.querySelector(selector);
const state = { resources: [], query: "", view: "all", kind: "", status: "", tag: "", sort: "newest", loaded: false };
let editingId = null;
let deletingId = null;
let toastTimer;
const icons = { article: "≡", video: "▷", course: "◈", tool: "⌘", book: "▤" };

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(path, { method, headers: { "Content-Type": "application/json", "X-Trailmark-Request": "1" },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  } catch {
    throw new Error("Cannot reach Trailmark. Check that the Python server is running, then try again.");
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}). Please try again.`);
  return data;
}

function notify(message) {
  clearTimeout(toastTimer);
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  toastTimer = setTimeout(() => { $("#toast").hidden = true; }, 5500);
}

async function load() {
  $("#retry").disabled = true;
  try {
    const data = await api("/api/resources");
    state.resources = data.resources;
    state.loaded = true;
    $("#load-error").hidden = true;
    render();
    return true;
  } catch (error) {
    $("#load-error span").textContent = error.message;
    $("#load-error").hidden = false;
    if (!state.loaded) $("#cards").replaceChildren();
    return false;
  } finally { $("#retry").disabled = false; }
}

async function patchResource(id, patch, control) {
  control.disabled = true;
  try {
    const updated = await api(`/api/resources/${id}`, { method: "PATCH", body: patch });
    state.resources = state.resources.map(item => item.id === id ? updated : item);
    render();
    notify("Resource updated.");
  } catch (error) { notify(error.message); render(); }
}

function createCard(item) {
  const card = element("article", "resource-card");
  const top = element("div", "card-top");
  const type = element("span", `type-label ${item.kind}`);
  type.append(element("span", "type-icon", icons[item.kind]), document.createTextNode(KIND_LABELS[item.kind]));
  const favorite = element("button", `favorite-button${item.favorite ? " selected" : ""}`, item.favorite ? "★" : "☆");
  favorite.type = "button";
  favorite.setAttribute("aria-label", `${item.favorite ? "Unfavorite" : "Favorite"} ${item.title}`);
  favorite.setAttribute("aria-pressed", String(item.favorite));
  favorite.addEventListener("click", () => patchResource(item.id, { favorite: !item.favorite }, favorite));
  top.append(type, favorite);
  const title = element("h3");
  const link = element("a", "resource-link", item.title);
  link.href = item.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  title.append(link);
  const domain = element("a", "domain", `${new URL(item.url).hostname.replace(/^www\./, "")} ↗`);
  domain.href = item.url; domain.target = "_blank"; domain.rel = "noopener noreferrer";
  const notes = element("p", "card-notes", item.notes || "A new idea waiting to be explored.");
  const tags = element("div", "card-tags");
  for (const tag of item.tags) {
    const button = element("button", "tag", tag);
    button.setAttribute("aria-label", `Filter by tag ${tag}`);
    button.addEventListener("click", () => { state.tag = tag; render(); });
    tags.append(button);
  }
  const bottom = element("div", "card-bottom");
  const status = element("select", `card-status ${item.status}`);
  status.setAttribute("aria-label", `Learning status for ${item.title}`);
  for (const [value, label] of Object.entries(STATUS_LABELS)) {
    const option = element("option", "", label);
    option.value = value; option.selected = value === item.status;
    status.append(option);
  }
  status.addEventListener("change", () => patchResource(item.id, { status: status.value }, status));
  const actions = element("div", "card-actions");
  const edit = element("button", "text-button", "Edit");
  edit.setAttribute("aria-label", `Edit ${item.title}`);
  edit.addEventListener("click", () => openEditor(item));
  const remove = element("button", "remove-button", "×");
  remove.setAttribute("aria-label", `Remove ${item.title}`);
  remove.addEventListener("click", () => {
    deletingId = item.id;
    $("#delete-description").textContent = item.title;
    $("#delete-dialog").showModal();
    $("#cancel-delete").focus();
  });
  actions.append(edit, remove);
  bottom.append(status, actions);
  card.append(top, title, domain, notes, tags, bottom);
  return card;
}

function render() {
  const summary = summarize(state.resources);
  for (const key of ["total", "learning", "completed"]) $(`#stat-${key}`).textContent = summary[key];
  $("#stat-rate").replaceChildren(document.createTextNode(summary.rate), element("small", "", "%"));
  $("#completion-progress").value = summary.rate;
  for (const [name, key] of [["all", "total"], ["learning", "learning"], ["completed", "completed"], ["favorites", "favorites"]]) $(`#nav-${name}`).textContent = summary[key];
  document.querySelectorAll("[data-view]").forEach(button => {
    const active = button.dataset.view === state.view;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  const names = { all: "All resources", learning: "In progress", completed: "Completed", favorites: "Favorites" };
  const visible = filterResources(state.resources, state);
  $("#library-title").replaceChildren(document.createTextNode(`${names[state.view]} `), element("span", "", visible.length));
  $("#collection-note").textContent = `${visible.length} of ${state.resources.length} resources`;
  $("#cards").replaceChildren(...visible.map(createCard));
  $("#empty-state").hidden = state.resources.length !== 0;
  $("#no-results").hidden = state.resources.length === 0 || visible.length !== 0;
  const tags = [...new Set(state.resources.flatMap(item => item.tags))].sort();
  if (state.tag && !tags.includes(state.tag)) tags.push(state.tag);
  const tagButtons = ["", ...tags].map(tag => {
    const button = element("button", `filter-tag${state.tag === tag ? " active" : ""}`, tag || "Everything");
    button.setAttribute("aria-pressed", String(state.tag === tag));
    button.addEventListener("click", () => { state.tag = tag; render(); });
    return button;
  });
  $("#tag-filters").replaceChildren(...tagButtons);
  $("#clear-filters").hidden = !(state.query || state.tag || state.kind || state.status || state.view !== "all" || state.sort !== "newest");
}

function resetFilters() {
  Object.assign(state, { query: "", kind: "", status: "", tag: "", view: "all", sort: "newest" });
  $("#search").value = ""; $("#kind-filter").value = ""; $("#status-filter").value = ""; $("#sort").value = "newest";
  render();
}

function openEditor(item = null) {
  const form = $("#resource-form");
  form.reset();
  editingId = item?.id ?? null;
  $("#dialog-title").textContent = item ? "A little more context." : "Save something good.";
  $("#form-error").hidden = true;
  if (item) {
    for (const field of ["title", "url", "kind", "status", "notes"]) form.elements[field].value = item[field];
    form.elements.tags.value = item.tags.join(", ");
    form.elements.favorite.checked = item.favorite;
  }
  $("#resource-dialog").showModal();
  form.elements.title.focus();
}

$("#resource-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const fields = form.elements;
  const payload = Object.fromEntries(["title", "url", "kind", "status", "notes"].map(key => [key, fields[key].value]));
  payload.tags = parseTags(fields.tags.value);
  payload.favorite = fields.favorite.checked;
  const resourceId = editingId;
  $("#save-resource").disabled = true;
  $("#save-resource").textContent = "Saving…";
  $("#form-error").hidden = true;
  try {
    const saved = await api(resourceId ? `/api/resources/${resourceId}` : "/api/resources", { method: resourceId ? "PATCH" : "POST", body: payload });
    if (resourceId) state.resources = state.resources.map(item => item.id === resourceId ? saved : item);
    else state.resources.unshift(saved);
    $("#resource-dialog").close();
    render();
    notify(resourceId ? "Changes saved." : "Resource saved. A new trail to follow.");
  } catch (error) { $("#form-error").textContent = error.message; $("#form-error").hidden = false; }
  finally { $("#save-resource").disabled = false; $("#save-resource").textContent = "Save resource"; }
});

for (const selector of ["#add-resource", "#empty-add"]) $(selector).addEventListener("click", () => openEditor());
for (const selector of ["#close-dialog", "#cancel-dialog"]) $(selector).addEventListener("click", () => { if (!$("#save-resource").disabled) $("#resource-dialog").close(); });
$("#resource-dialog").addEventListener("cancel", event => { if ($("#save-resource").disabled) event.preventDefault(); });
$("#cancel-delete").addEventListener("click", () => { if (!$("#confirm-delete").disabled) $("#delete-dialog").close(); });
$("#delete-dialog").addEventListener("cancel", event => { if ($("#confirm-delete").disabled) event.preventDefault(); });
$("#confirm-delete").addEventListener("click", async () => {
  $("#confirm-delete").disabled = true;
  try {
    await api(`/api/resources/${deletingId}`, { method: "DELETE" });
    state.resources = state.resources.filter(item => item.id !== deletingId);
    $("#delete-dialog").close(); render(); notify("Resource removed.");
  } catch (error) { notify(error.message); }
  finally { $("#confirm-delete").disabled = false; }
});

document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
  state.view = button.dataset.view;
  state.status = ""; $("#status-filter").value = "";
  render();
}));
for (const [selector, key, event] of [["#search", "query", "input"], ["#kind-filter", "kind", "change"], ["#status-filter", "status", "change"], ["#sort", "sort", "change"]]) {
  $(selector).addEventListener(event, e => { state[key] = e.target.value; render(); });
}
for (const selector of ["#clear-filters", "#empty-reset"]) $(selector).addEventListener("click", resetFilters);
$("#retry").addEventListener("click", load);
$("#import-button").addEventListener("click", () => $("#import-file").click());
$("#import-file").addEventListener("change", async event => {
  const file = event.target.files[0];
  if (!file) return;
  $("#import-button").disabled = true;
  try {
    if (file.size > 1024 * 1024) throw new Error("Choose a backup smaller than 1 MiB.");
    let data;
    try { data = JSON.parse(await file.text()); } catch { throw new Error("That file is not valid JSON. Choose a Trailmark backup."); }
    const result = await api("/api/import", { method: "POST", body: data });
    await load();
    notify(`Imported ${result.imported} resources. Skipped ${result.skipped} duplicate links.`);
  } catch (error) { notify(error.message); }
  finally { event.target.value = ""; $("#import-button").disabled = false; }
});

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("#theme-toggle").setAttribute("aria-pressed", String(theme === "dark"));
  $("#theme-toggle span").textContent = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  try { localStorage.setItem("trailmark-theme", theme); } catch { /* The app also works with storage disabled. */ }
}
let theme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
try { theme = localStorage.getItem("trailmark-theme") || theme; } catch { /* Use the system preference. */ }
setTheme(theme === "dark" ? "dark" : "light");
$("#theme-toggle").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
load();
