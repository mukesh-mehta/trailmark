// Pure helpers shared by the interface and Node's built-in test runner.
export const STATUS_LABELS = { queued: "To learn", learning: "In progress", completed: "Completed" };
export const KIND_LABELS = { article: "Article", video: "Video", course: "Course", tool: "Tool", book: "Book" };

export function filterResources(resources, { query = "", view = "all", kind = "", status = "", tag = "", sort = "newest" } = {}) {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const result = resources.filter(item => {
    const haystack = [item.title, item.url, item.notes, ...item.tags].join(" ").toLocaleLowerCase();
    return terms.every(term => haystack.includes(term))
      && (view === "all" || (view === "favorites" ? item.favorite : item.status === view))
      && (!kind || item.kind === kind) && (!status || item.status === status)
      && (!tag || item.tags.includes(tag));
  });
  return result.sort((a, b) => sort === "title" ? a.title.localeCompare(b.title)
    : (sort === "oldest" ? 1 : -1) * (a.created_at.localeCompare(b.created_at) || a.id - b.id));
}

export function summarize(resources) {
  const completed = resources.filter(item => item.status === "completed").length;
  return { total: resources.length, learning: resources.filter(item => item.status === "learning").length,
    completed, favorites: resources.filter(item => item.favorite).length,
    rate: resources.length ? Math.round(completed / resources.length * 100) : 0 };
}

export function parseTags(value) {
  return [...new Set(value.split(",").map(tag => tag.trim().toLowerCase()).filter(Boolean))];
}
