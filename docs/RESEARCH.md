# Project idea research

Researched on **16 November 2026** using public project repositories and official documentation. These sources are examples of established use cases, not claims that Trailmark implements their full feature sets.

| Idea | Example source | Why it is useful | Fit for this project |
|---|---|---|---|
| Personal learning/bookmark library | [linkding](https://github.com/sissbruecker/linkding) | A searchable, organized home for saved links. | Strong: a complete local workflow can be built with Python, SQLite, and a JavaScript interface. |
| Website-change monitor | [changedetection.io](https://github.com/dgtlmoon/changedetection.io) | Detect changes to pages and alert users. | Interesting, but a useful baseline needs fetching, scheduling, diffs, and network safeguards. |
| Job-application tracker | [Job Tracker](https://github.com/mquadros/job-tracker) | Keep applications, pipeline stages, and notes together. | Feasible, but learning resources provide a broader demo without requiring personal job-search data. |

## Decision

Build **Trailmark**, a learning-oriented resource library. The choice is a design judgment based on the requested stack and partial-feature scope, not a popularity ranking.

Its distinguishing focus is the learning loop: save a resource, record intent, start it, write takeaways, and mark it complete. Tags, favorites, and progress counts make that loop usable even before metadata extraction, an extension, or synchronization exists.

## Implementation references

- [Flask Quickstart](https://flask.palletsprojects.com/en/stable/quickstart/) — routing, serving assets, and local development.
- [Testing Flask Applications](https://flask.palletsprojects.com/en/stable/testing/) — test clients and application-factory fixtures.

No source code was copied from the inspiration projects. Trailmark uses its own UI, data model, and endpoints.
