# aditya-taparia.github.io

Personal academic website. Static HTML generated from JSON by `build.py`
(Python standard library only — no npm, no dependencies).

**UI inspired by:** [jonbarron.github.io](https://github.com/jonbarron/jonbarron.github.io)

## Editing

Edit the sources, never the generated HTML:

| File | Contents |
|------|----------|
| `data/publications.json` | All publications. Single source of truth. |
| `data/news.json` | News items. |
| `data/site.json` | Bio metadata, links, analytics codes. |
| `pages/intro.html` | Biography prose. |
| `styles.css`, `main.js` | Styling and behaviour. |

Then:

```sh
python3 build.py     # regenerate the site
python3 verify.py    # 89 checks: links, BibTeX, structured data, idempotency
```

Pushing to `main` runs both in GitHub Actions and commits the output, so
running them locally is optional — but it is the fastest way to see mistakes.

### Generated — do not edit by hand

`index.html` · `papers/**` · `404.html` · `llms.txt` · `sitemap.xml` ·
`robots.txt`

## Adding a publication

Append an object to `data/publications.json`:

```jsonc
{
  "id": "short_id",
  "slug": "url-slug",              // becomes /papers/url-slug/
  "title": "...",
  "authors": ["Aditya Taparia", "..."],   // exact order; your name is bolded
  "venue": "Full venue name",
  "venue_short": "ICML 2027",
  "venue_type": "conference",      // conference | workshop | journal | preprint
  "year": "2027",
  "sort_key": "2027-07",           // YYYY-MM, controls ordering (newest first)
  "category": "conference",        // conference = "Conferences & Journals" tab
                                   // preprint   = "Preprints & Workshops" tab
  "image": "images/foo.png",       // optional; omit and text spans full width
  "figure": "images/foo_full.jpg", // optional; full-res version for the paper page
  "image_alt": "What the figure shows.",
  "description": "Paragraph for the listing and the paper page.",
  "tldr": "One sentence for llms.txt and the meta description.",
  "arxiv_id": "2501.00000",        // optional
  "doi": "10.xxxx/yyyy",           // optional
  "award": "Spotlight",            // optional; rendered in red with a ribbon
  "links": { "pdf": "...", "pdf_direct": "...", "code": "...", "video": "..." },
  "bibtex": "@inproceedings{key,\n    title={...},\n ...\n}"
}
```

`build.py` fails loudly on a missing required field, a duplicate slug, a
missing image, or a hotlinked news image. `verify.py` additionally checks that
every BibTeX entry parses.

## Analytics

Set in `data/site.json`:

- `goatcounter_code` — your GoatCounter subdomain. Empty means the tag is
  omitted entirely.
- `google_site_verification` — the Search Console verification token.

GoatCounter is cookieless, so no consent banner is required.

## SEO / GEO

Each paper gets its own page at `/papers/<slug>/` carrying `citation_*` meta
tags (what Google Scholar reads), `ScholarlyArticle` JSON-LD, a canonical URL
and an OG card. `robots.txt` explicitly allows LLM crawlers, and `llms.txt`
gives them a plain-text summary of the profile and every paper.

---

Built by Aditya Taparia • [ataparia@asu.edu](mailto:ataparia@asu.edu)
