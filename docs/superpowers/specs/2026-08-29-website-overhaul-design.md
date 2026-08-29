# Website Overhaul — Design Spec

**Date:** 2026-08-29
**Repo:** `aditya-taparia.github.io`
**Author:** Aditya Taparia

## Problem

The site has not been updated since October 2025. Four distinct problems:

1. **Stale content.** Three papers are missing entirely, two have outdated venues,
   two journal papers have never appeared, and the bio still says "first-year".
2. **Invisible to crawlers.** All content arrives via `fetch()` after page load.
   LLM crawlers (GPTBot, ClaudeBot, PerplexityBot, CCBot) do not execute
   JavaScript, so they see an empty document. There is no `sitemap.xml`,
   `robots.txt`, structured data, or per-paper URL.
3. **No analytics.** No way to know who visits or how they arrive.
4. **Markup bugs.** Malformed BibTeX, `charset=us-ascii` on UTF-8 content, a fixed
   900px layout that breaks on mobile, reliance on the legacy global `event`.

## Goals

- Every paper listed, correct, and individually indexable.
- Content visible to search engines and LLM crawlers without JavaScript.
- Analytics that respects visitors and needs no cookie banner.
- Keep the existing visual identity (Jon Barron-inspired) and the videos.

## Non-goals

- No visual redesign. Layout, colours, and typography stay as they are apart
  from responsive fixes.
- No CV rewrite. `data/CV.pdf` is stale but regenerating it is out of scope;
  flag it to the user instead.
- No JS framework, no npm, no `node_modules`.

---

## 1. Build pipeline

`build.py`, Python **standard library only**. No `pip install` in CI, so the
Action cannot break on a dependency update. Templates are module-level
functions returning f-strings; at 12 papers a template engine is not warranted.

```
SOURCES (hand-edited)          BUILD          OUTPUT (generated, committed)
data/publications.json  ─┐                   ├─ index.html
data/news.json          ─┼─> build.py ─────> ├─ papers/index.html
data/site.json          ─┤                   ├─ papers/<slug>/index.html × 12
pages/intro.html        ─┘                   ├─ llms.txt
                                             └─ sitemap.xml
```

**Generated files are committed.** GitHub Pages serves them directly; no Jekyll,
no build on their side. Add `.nojekyll`.

### Source files

| File | Role |
|---|---|
| `data/publications.json` | All 12 papers. Single source of truth. |
| `data/news.json` | News items: `date`, `sort_key`, `html`, optional `logo`. |
| `data/site.json` | Site metadata: URL, title, description, social links, GoatCounter code. |
| `pages/intro.html` | Bio prose. Stays HTML — it is prose with inline links. |

`pages/news.html` and `pages/publication.html` are deleted; their content is
generated.

### Publication schema

Existing fields kept. Added:

| Field | Purpose |
|---|---|
| `slug` | URL segment for `/papers/<slug>/` |
| `category` | `"conference"` (Conferences & Journals) or `"preprint"` (Preprints & Workshops) |
| `abstract` | Full abstract for the paper landing page |
| `tldr` | One sentence for `llms.txt` |
| `sort_key` | `YYYY-MM` for deterministic ordering |
| `arxiv_id` | Emitted as `citation_arxiv_id` |
| `venue_short` | e.g. `AAAI 2026`, for compact listings |
| `award` | Optional, e.g. Best Student Paper shortlist |
| `image_alt` | Describes what the figure shows |

`image` becomes optional. When absent, the card renders with text at full width.

### CI

`.github/workflows/build.yml` — on push to `main` touching sources, runs
`python3 build.py` and commits changed output with `[skip ci]`.

Guards: skip if the commit is from the bot (loop prevention); fail the build on
schema errors rather than emitting broken HTML.

---

## 2. Research section

Renamed **"Research"** (from "Selected Research"). All 12 papers. Three tabs:

| Tab | N | Contents |
|---|---|---|
| All | 12 | Everything, newest first by `sort_key` |
| Conferences & Journals | 9 | AAAI'26, EACL'26, ECML PKDD'26, IROS'25, ICML'25, ICML'24, AAAI Symp'25, Alexandria Eng. J., JCCE |
| Preprints & Workshops | 3 | ICLR-W'26, NeurIPS-W'24, arXiv (ARC) |

Tabs are real links (`#all`, `#conferences`, `#preprints`) so each is
addressable. JS also listens for `hashchange`, so a pasted `#conferences`
link switches tabs on an already-open page, not only on a cold load.

**Changed during implementation.** The original plan rendered three tab
panels, which meant emitting all 12 papers into "All" and then again into
their category panel. That is duplicate content inside one document, and the
copies in the inactive panels sit under `display:none`, which search engines
discount. Instead each paper is emitted **exactly once** with a
`data-category` attribute, and the tabs set `data-filter` on the list so CSS
hides non-matching items. Same behaviour, no duplication, smaller HTML.

**Images:** all get `loading="lazy"`, `decoding="async"`, explicit
`width`/`height` (avoids layout shift), and descriptive `alt`. Five papers have
no image and render text at full width. No thumbnail generation — no Pillow
dependency; existing images total 1.6 MB.

---

## 3. Per-paper landing pages

`/papers/<slug>/index.html` for each of the 12. Each carries:

- `<h1>` with the paper title
- Full author list, venue, year, award
- Abstract, BibTeX (with a copy button), links to PDF/code/video
- **Google Scholar tags:** `citation_title`, `citation_author` (one per author,
  in order), `citation_publication_date`, `citation_conference_title` or
  `citation_journal_title`, `citation_arxiv_id`, `citation_pdf_url`,
  `citation_abstract_html_url`, `citation_language`
- `ScholarlyArticle` JSON-LD
- `<link rel="canonical">`, OG + Twitter card, breadcrumb nav

`/papers/` — index of all 12 in compact form.

### Slugs

| Slug | Paper |
|---|---|
| `vlc-fusion` | VLC Fusion (ECML PKDD 2026) |
| `abductive-reasoning` | Consistency-based Abductive Reasoning (AAAI 2026) |
| `expressivity-bench` | ExpressivityBench (Findings of EACL 2026) |
| `anatomy-of-uncertainty` | The Anatomy of Uncertainty in LLMs (ICBINB @ ICLR 2026) |
| `learning-to-configure` | Learning to Configure Agentic AI Systems (ARC) |
| `rlpo` | Explainable Concept Generation (ICML 2025) |
| `batcave` | BaTCAVe (IROS 2025) |
| `mds-a` | MDS-A (AAAI Spring Symposium 2025) |
| `failures-are-fated` | Failures Are Fated (ICML 2024) |
| `red-teaming-diffusion` | LLM-Assisted Red Teaming (NeurIPS-W 2024) |
| `hpix` | Transforming satellite imagery into vector maps (Alexandria Eng. J. 2024) |
| `stock-forecasting` | Multi-sequential NN Models for Stock Price Forecasting (JCCE 2025) |

---

## 4. SEO / GEO layer

**Per page:** unique `<title>` and `<meta name="description">`, canonical URL,
OG + Twitter card, `theme-color`, semantic `<h1>`/`<h2>`/`<h3>`.

**Homepage JSON-LD `@graph`:** `WebSite` + `Person` (affiliation ASU, advisor
Ransalu Senanayake, `sameAs` → Scholar, GitHub, LinkedIn, arXiv) + `ItemList`
of publications.

**`robots.txt`** — explicitly allow LLM crawlers, since GEO is a stated goal:

```
User-agent: *
Allow: /

User-agent: GPTBot
Allow: /
# same for ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended,
# CCBot, Applebot-Extended, Bingbot, cohere-ai

Sitemap: https://aditya-taparia.github.io/sitemap.xml
```

**`llms.txt`** — generated: bio, research focus, page index, one-line summary per
paper with its landing-page URL, profile links.

**`sitemap.xml`** — homepage, `/papers/`, 12 paper pages, CV PDF. `lastmod` from
build date.

**`404.html`** — styled, links home.

---

## 5. Analytics

GoatCounter on every generated page:

```html
<script data-goatcounter="https://<code>.goatcounter.com/count"
        async src="https://gc.zgo.at/count.js"></script>
```

Cookieless, ~3 KB, private dashboard by default, no consent banner. Site code
comes from `data/site.json`; if unset, the tag is omitted rather than emitting a
broken URL.

Google Search Console verification via a meta tag in `data/site.json`.

**Rejected:** GA4 (needs a cookie consent banner; ~50 KB; heavily ad-blocked by
an ML audience, so it would undercount) and a local aggregator script (nothing to
aggregate with one source).

---

## 6. Bug fixes

| # | Fix |
|---|---|
| 1 | BibTeX `@article{taparia2025vlc},` → `{taparia2025vlc,`; same for `ngu2025multiple` |
| 2 | `<!DOCTYPE html>`; `<meta charset="utf-8">` as first element in `<head>` |
| 3 | Fixed `width="900"` → `max-width:900px; width:100%`; intro table stacks under 700px |
| 4 | `switchTab(name, this)` — no reliance on global `event` |
| 5 | Favicon `type="image/png"` |
| 6 | Remove unused jQuery (~90 KB), `images/VLC Fusion.jpg`, `images/background.png` |
| 7 | Videos stay. Add `preload="none"` so they load only on click; modal sized responsively (currently `50vw/50vh`, unusable on mobile) |
| 8 | `.bibtex.show` gets `overflow-y:auto` — currently clips long entries |
| 9 | LLNL logo downloaded locally; Bosch logo added. Stop hotlinking `media.licdn.com` |
| 10 | `rel="noopener"` on all `target="_blank"` |
| 11 | Modal closes on Escape; tabs get `role="tab"`/`aria-selected` |
| 12 | `.nojekyll` added |

---

## 7. Content corrections

### Publications

**Added (3):**
- Consistency-based Abductive Reasoning — AAAI 2026, pp. 19216–19223, arXiv 2505.19361
- The Anatomy of Uncertainty in LLMs — ICBINB Workshop @ ICLR 2026, arXiv 2603.24967
- Learning to Configure Agentic AI Systems (ARC) — arXiv 2602.11574

**Added (2, never on site):**
- Transforming satellite imagery into vector maps using modified GANs (HPix) —
  Alexandria Engineering Journal 109:792–806, 2024, DOI 10.1016/j.aej.2024.09.074
- Multi-sequential Neural Network Models for Stock Price Forecasting — JCCE, 2025

**Corrected (2):**
- VLC Fusion: `arXiv preprint` → **ECML PKDD 2026**, Best Research Track Student
  Paper shortlist. Category `preprint` → `conference`.
- ExpressivityArena → retitled **ExpressivityBench: Can LLMs Communicate
  Implicitly?**, **Findings of EACL 2026**, pp. 4500–4515. Author order corrected
  to Tint, Sagar, Taparia, Raines, Pathiraja, Liu, Senanayake.

### News

Newest first, verified notification dates:

| Date | Item |
|---|---|
| May '26 | 🎗 VLC Fusion → ECML PKDD'26, Best Student Paper shortlist (notified May 27, 2026) |
| May '26 | [Bosch] Joined Bosch as a Research Intern |
| Jan '26 | ExpressivityBench → Findings of EACL'26 (notified Jan 3, 2026) |
| Nov '25 | Abductive Reasoning → AAAI'26 (notified Nov 8, 2025) |
| Jun '25 | BaTCAVe → IROS'25 |
| May '25 | [LLNL] Joined LLNL, Student Research Intern, MIG group |
| May '25 | Explainable Concept Generation → ICML'25 |
| Jan '25 | Joined ASU as a PhD student |
| Dec '24 | Presented four workshop papers at NeurIPS'24 |
| May '24 | 🎗 Failures Are Fated → ICML'24, spotlight (top 3.5%) |
| Aug '23 | Joined ASU as a Masters student |

Changes from the current page: LLNL corrected Aug '25 → **May '25** (user
confirmed); ICBINB/ICLR'26 item **removed** (user request); news box keeps its
current height with `overflow-y:auto`.

### Intro

- "first-year" → **"second-year"** PhD student
- Mention past internships: LLNL (May–Aug 2025), Bosch (May–Aug 2026, completed)

### Explicitly excluded — unverified

- **Qualcomm San Diego Summer 2026.** Search snippet only; user did not confirm.
- **CS MS Thesis Outstanding Student Award (SCAI).** Search snippet only; user
  did not confirm.

Neither appears anywhere in the output.

---

## 8. Post-deploy checklist (user actions)

Cannot be automated:

1. Register a GoatCounter site; put the code in `data/site.json`.
2. Verify the site in **Google Search Console**; submit `sitemap.xml`.
3. Verify in **Bing Webmaster Tools**; submit the sitemap.
4. Add the homepage URL to the **Google Scholar profile**.
5. Optionally supply images for the 5 papers that lack them.
6. `data/CV.pdf` is from Oct 2025 and is now stale — regenerate.

**Expectation:** indexing takes days to weeks; Google Scholar's crawler is slow
and selective. This work removes the technical barriers to indexing; it does not
guarantee ranking.

---

## Testing

No test framework exists in this repo, and one is not warranted for a static
site. Verification is instead:

1. `python3 build.py` exits 0 and is **idempotent** — running twice produces no
   diff.
2. Every generated HTML file parses (`html.parser`, no unclosed tags).
3. Every internal link and image path resolves to a file on disk.
4. Every BibTeX entry parses — balanced braces, `@type{key,` well-formed.
   This is the regression test for the bug that started this.
5. `sitemap.xml` is well-formed XML; every `<loc>` exists on disk.
6. JSON-LD blocks parse as JSON.
7. All 12 papers appear in All; counts per tab are 12 / 9 / 3.
8. Neither "Qualcomm" nor "Outstanding Student Award" appears in any output.
9. No generated page contains a fixed pixel width attribute; every page has a
   viewport meta and `<meta charset="utf-8">` as the first element in `<head>`.
10. Rendered check at 375px and 1440px width — no horizontal scroll.

`verify.py` implements 1–9 and runs in CI after the build. As built it is
**89 checks**.

Item 10 was verified manually in Chrome by constraining the document to 375px
and 768px and measuring `document.body.scrollWidth` against the document
width, plus every element's right edge. Result: no overflow, zero offending
elements. The old `<table width="900">` would have reported 900px against a
375px document, so this is a meaningful regression check; check 9 is its
static equivalent and does run in CI.
