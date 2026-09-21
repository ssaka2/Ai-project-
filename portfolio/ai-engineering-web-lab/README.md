# AI Engineering Web Lab

Interactive browser-based evaluation of recorded AI responses, plus links to the twelve other projects. Rules cover required/forbidden text, word count, and optional JSON syntax. Downloadable reports contain rule outcomes. No AI model is called, and inputs are neither transmitted by application code nor saved.

## Run

Requires Node.js 24 for tests and Python 3 for the optional static server.

```sh
cd portfolio/ai-engineering-web-lab
node --test test-evaluate.mjs
python -m http.server 8000 --directory dist
```

Open http://localhost:8000. Six tests cover success, failure, limits, JSON parsing, invalid inputs, and duplicate terms. Source assets and JavaScript syntax were validated. Managed static hosting offers no compatible browser preview here, so visual browser QA and WebMCP registration validation remain unverified. WebMCP is feature-detected; the ordinary UI works without it.

[Deployed Site](https://sandeep-ai-engineering-lab.ssaka2.chatgpt.site) — owner-only access at publication. This does not deploy the linked backend services. Public access has not been enabled.

Text rules use substring matching and whitespace-separated word counts, not semantic evaluation. JSON mode checks syntax only, not schemas, duplicate keys, or numeric precision. Do not use rule pass counts as evidence of factual accuracy or safety.
