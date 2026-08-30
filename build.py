#!/usr/bin/env python3
"""Static site generator for aditya-taparia.github.io.

Reads data/site.json, data/publications.json, data/news.json and
pages/intro.html, and writes fully static HTML: no client-side fetching, so
search engines and LLM crawlers (which do not run JavaScript) see everything.

Standard library only, deliberately: the GitHub Action needs no pip install
and cannot break on a dependency update.

Usage:  python3 build.py
"""

import html
import json
import os
import re
import shutil
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
PAGES = os.path.join(ROOT, "pages")

BUILD_DATE = date.today().isoformat()

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet">\n'
    '<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">'
)


# Real brand marks for the platforms that have one. Material Icons only
# offers stand-ins here -- a generic office block for LinkedIn, angle
# brackets for GitHub -- which read as "some company" and "some code"
# rather than as the sites they link to. Paths are the official marks
# (Simple Icons, 24x24, CC0); `fill: currentColor` in the stylesheet keeps
# them in step with the button's hover inversion.
BRAND_ICON_PATHS = {
    "linkedin": (
        "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 "
        "0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 "
        "1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 "
        "7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 "
        "2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 "
        "2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 "
        ".774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 "
        "23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
    ),
    "github": (
        "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 "
        "11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-"
        "4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 "
        "17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 "
        "1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-"
        "1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 "
        "1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 "
        "1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 "
        "2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765"
        ".84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 "
        "1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20"
        ".565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
    ),
}


def icon_markup(name):
    """A brand mark where one exists, otherwise the Material Icons ligature."""
    path = BRAND_ICON_PATHS.get(name)
    if path:
        return ('<svg class="btn-icon" viewBox="0 0 24 24" aria-hidden="true" '
                'focusable="false"><path d="%s"/></svg>' % path)
    return '<span class="material-icons">%s</span>' % esc(name)


# --------------------------------------------------------------- helpers ---

def esc(text):
    """Escape for HTML text and attribute contexts."""
    return html.escape(str(text if text is not None else ""), quote=True)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(relpath, content):
    dest = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("  wrote %s (%d bytes)" % (relpath, len(content.encode("utf-8"))))


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text or "")


def authors_html(authors, highlight="Aditya Taparia"):
    parts = []
    for name in authors:
        if name == highlight:
            parts.append("<strong>%s</strong>" % esc(name))
        else:
            parts.append(esc(name))
    return ", ".join(parts)


def authors_plain(authors):
    return ", ".join(authors)


# ----------------------------------------------------------------- head ---

def head(site, *, title, description, url_path, prefix, og_image=None,
         og_type="website", extra=""):
    """Shared <head>. `prefix` is the relative path back to the site root."""
    base = site["url"].rstrip("/")
    canonical = base + "/" + url_path.lstrip("/") if url_path else base + "/"
    image = og_image or site["profile_image"]
    image_abs = image if image.startswith("http") else base + "/" + image.lstrip("/")

    verification = ""
    if site.get("google_site_verification"):
        verification = '\n<meta name="google-site-verification" content="%s">' % esc(
            site["google_site_verification"])

    analytics = ""
    if site.get("goatcounter_code"):
        analytics = (
            '\n<!-- GoatCounter: cookieless, no personal data, private dashboard -->\n'
            '<script data-goatcounter="https://%s.goatcounter.com/count"\n'
            '        async src="https://gc.zgo.at/count.js"></script>'
            % esc(site["goatcounter_code"])
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{esc(site['name'])}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="{esc(og_type)}">
<meta property="og:site_name" content="{esc(site['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(image_abs)}">
<meta property="og:image:alt" content="{esc(site['profile_image_alt'])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(image_abs)}">
<meta name="twitter:image:alt" content="{esc(site['profile_image_alt'])}">
<meta name="theme-color" content="{esc(site['theme_color'])}">
{FONT_LINKS}
<link rel="stylesheet" href="{prefix}styles.css">
<link rel="icon" type="image/png" href="{prefix}{esc(site['favicon'])}">
<link rel="apple-touch-icon" href="{prefix}{esc(site['favicon'])}">{verification}{analytics}{extra}
</head>
"""


def footer(site, prefix, extra_links=""):
    year = BUILD_DATE[:4]
    return f"""<footer class="site-footer page">
{extra_links}<p>&copy; {year} {esc(site['name'])} &middot; <a href="mailto:{esc(site['email'])}">{esc(site['email'])}</a></p>
</footer>
<script src="{prefix}main.js" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------- JSON-LD ---

def person_ld(site, pubs):
    base = site["url"].rstrip("/")
    return {
        "@type": "Person",
        "@id": base + "/#person",
        "name": site["name"],
        "url": base + "/",
        "email": "mailto:" + site["email"],
        "image": base + "/" + site["profile_image"],
        "jobTitle": "PhD Student in Computer Science",
        "description": site["description"],
        "knowsAbout": site["research_focus"],
        "affiliation": {
            "@type": "CollegeOrUniversity",
            "name": site["affiliation"]["name"],
            "url": site["affiliation"]["url"],
            "department": {
                "@type": "Organization",
                "name": site["affiliation"]["department"],
            },
        },
        "alumniOf": {
            "@type": "CollegeOrUniversity",
            "name": site["alumni_of"]["name"],
            "url": site["alumni_of"]["url"],
        },
        "sameAs": site["same_as"],
    }


def article_ld(site, pub):
    base = site["url"].rstrip("/")
    url = "%s/papers/%s/" % (base, pub["slug"])
    node = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "@id": url + "#article",
        "name": pub["title"],
        "headline": pub["title"],
        "url": url,
        "mainEntityOfPage": url,
        "datePublished": pub["year"],
        "inLanguage": "en",
        "abstract": pub["description"],
        "author": [{"@type": "Person", "name": a} for a in pub["authors"]],
        "publisher": {"@type": "Organization", "name": pub["venue"]},
        "isPartOf": {"@type": "Periodical", "name": pub["venue"]},
        "author_note": None,
    }
    node.pop("author_note")
    if pub.get("image"):
        node["image"] = base + "/" + pub["image"]
    if pub.get("arxiv_id"):
        node["identifier"] = "arXiv:" + pub["arxiv_id"]
    if pub.get("doi"):
        node["sameAs"] = "https://doi.org/" + pub["doi"]
    if pub.get("award"):
        node["award"] = pub["award"]
    return node


def ld_script(payload):
    return ('<script type="application/ld+json">\n%s\n</script>'
            % json.dumps(payload, indent=2, ensure_ascii=False))


# ------------------------------------------------------ publication card ---

def pub_card(site, pub, prefix="", index=0):
    """One entry in the publication list on the homepage / papers index."""
    slug = pub["slug"]
    paper_url = "%spapers/%s/" % (prefix, slug)
    bib_id = "bib-%s" % slug
    has_thumb = bool(pub.get("image"))

    thumb = ""
    if has_thumb:
        thumb = (
            '<div class="pub-thumb">'
            '<a href="%s"><img src="%s%s" alt="%s" width="178" height="148" '
            'loading="lazy" decoding="async"></a>'
            '</div>'
        ) % (esc(paper_url), prefix, esc(pub["image"]),
             esc(pub.get("image_alt") or pub["title"]))

    venue_line = "%s, %s" % (esc(pub["venue"]), esc(pub["year"]))
    if pub.get("award"):
        venue_line += ' &middot; <span class="pub-award">%s 🎗</span>' % esc(pub["award"])

    buttons = []
    links = pub.get("links") or {}
    if links.get("pdf"):
        buttons.append(
            '<a href="%s" class="btn btn-publication" target="_blank" rel="noopener">'
            '<span class="material-icons">picture_as_pdf</span> PDF</a>' % esc(links["pdf"]))
    if links.get("video"):
        buttons.append(
            '<a href="#" class="btn btn-publication" data-video="%s%s">'
            '<span class="material-icons">play_circle</span> Video</a>'
            % (prefix, esc(links["video"])))
    if links.get("code"):
        buttons.append(
            '<a href="%s" class="btn btn-publication" target="_blank" rel="noopener">'
            '<span class="material-icons">code</span> Code</a>' % esc(links["code"]))
    buttons.append(
        '<a href="%s" class="btn btn-publication">'
        '<span class="material-icons">article</span> Details</a>' % esc(paper_url))
    buttons.append(
        '<button type="button" class="btn btn-publication" data-bibtex-toggle="%s" '
        'aria-expanded="false" aria-controls="%s">'
        '<span class="material-icons">format_quote</span> BibTeX</button>'
        % (bib_id, bib_id))

    return f"""<li class="pub-item" data-category="{esc(pub['category'])}">
{thumb}<div class="pub-body">
<h3 class="pub-title"><a href="{esc(paper_url)}">{esc(pub['title'])}</a></h3>
<div class="pub-authors">{authors_html(pub['authors'])}</div>
<div class="pub-venue">{venue_line}</div>
<div class="description">{esc(pub['tldr'])}</div>
<div class="pub-links">{''.join(buttons)}</div>
<div id="{bib_id}" class="bibtex"><pre>{esc(pub['bibtex'])}</pre></div>
</div>
</li>"""


# ------------------------------------------------------------- homepage ---

def build_index(site, pubs, news, intro):
    base = site["url"].rstrip("/")
    n_conf = sum(1 for p in pubs if p["category"] == "conference")
    n_pre = sum(1 for p in pubs if p["category"] == "preprint")

    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": base + "/#website",
                "url": base + "/",
                "name": site["name"],
                "description": site["description"],
                "inLanguage": "en",
                "publisher": {"@id": base + "/#person"},
            },
            person_ld(site, pubs),
            {
                "@type": "ItemList",
                "@id": base + "/#publications",
                "name": "Publications by " + site["name"],
                "numberOfItems": len(pubs),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "url": "%s/papers/%s/" % (base, p["slug"]),
                        "name": p["title"],
                    }
                    for i, p in enumerate(pubs)
                ],
            },
        ],
    }

    # The rail's links break into two centred rows, the fuller one on top.
    # An explicit break element beats letting flex-wrap choose, which would
    # reshuffle the moment a label or the webfont changed width.
    break_after = (len(site["links"]) + 1) // 2
    links = []
    for i, link in enumerate(site["links"]):
        target = ' target="_blank" rel="noopener"' if link["external"] else ""
        links.append(
            '<a href="%s" class="btn"%s>%s %s</a>'
            % (esc(link["href"]), target, icon_markup(link["icon"]), esc(link["label"])))
        if i + 1 == break_after:
            links.append('<span class="link-break" aria-hidden="true"></span>')

    news_rows = []
    for item in news:
        news_rows.append(
            '<tr><td class="news-date-cell"><span class="news-date">%s</span></td>'
            '<td>%s</td></tr>' % (esc(item["date"]), item["html"]))

    cards = "\n".join(pub_card(site, p, prefix="", index=i) for i, p in enumerate(pubs))

    tabs = [
        ("all", "All", len(pubs)),
        ("conferences", "Conferences &amp; Journals", n_conf),
        ("preprints", "Preprints &amp; Workshops", n_pre),
    ]
    tab_html = "\n".join(
        '<a class="tab-button%s" role="tab" id="tab-%s" href="#%s" data-tab="%s" '
        'aria-selected="%s" tabindex="%s">%s <span class="pub-tab-count">(%d)</span></a>'
        % (" active" if key == "all" else "", key, key, key,
           "true" if key == "all" else "false", "0" if key == "all" else "-1",
           label, count)
        for key, label, count in tabs)

    body = f"""<body>
<a class="skip-link" href="#main">Skip to content</a>

<div id="videoModal" class="modal" role="dialog" aria-modal="true" aria-label="Video player">
  <div class="modal-content">
    <button type="button" class="close-btn" aria-label="Close video">&times;</button>
    <video id="modalVideo" controls preload="none">
      <source src="" type="video/mp4">
      Your browser does not support the video tag.
    </video>
  </div>
</div>

<main id="main" class="page">

  <section class="intro-grid">
    <div class="intro-text">
      <div class="name-block"><h1 class="h-name">{esc(site['name'])}</h1></div>
      <p class="h-tagline">{esc(site['tagline'])}</p>
{intro}
    </div>
    <div class="intro-photo">
      <img src="{esc(site['profile_image'])}" alt="{esc(site['profile_image_alt'])}"
           width="768" height="1020" decoding="async">
    </div>
    <div class="link-row">
{chr(10).join('      ' + l for l in links)}
    </div>
  </section>

  <section class="home-section" aria-labelledby="news-heading">
    <h2 class="h-section" id="news-heading">News</h2>
    <div class="news-box">
      <table class="news-table">
        <tbody>
{chr(10).join('          ' + r for r in news_rows)}
        </tbody>
      </table>
    </div>
  </section>

  <section class="home-section" aria-labelledby="research-heading">
    <h2 class="h-section" id="research-heading">Research</h2>
    <p>All {len(pubs)} publications are listed below. See also my
       <a href="data/CV.pdf">CV</a> and
       <a href="https://scholar.google.com/citations?user=hfU1wQwAAAAJ&amp;hl=en" target="_blank" rel="noopener">Google Scholar</a>.</p>

    <div class="tab-navigation" role="tablist" aria-label="Filter publications">
{chr(10).join('      ' + t for t in tab_html.split(chr(10)))}
    </div>

    <ol class="pub-list" id="pub-list" data-filter="all">
{cards}
    </ol>
  </section>

</main>
"""

    return (head(site,
                 title=site["title"],
                 description=site["description"],
                 url_path="",
                 prefix="",
                 og_type="profile",
                 extra="\n" + ld_script(graph))
            + body
            + footer(site, ""))


# ---------------------------------------------------------- paper pages ---

def citation_meta(pub):
    tags = ['<meta name="citation_title" content="%s">' % esc(pub["title"])]
    for author in pub["authors"]:
        tags.append('<meta name="citation_author" content="%s">' % esc(author))
    tags.append('<meta name="citation_publication_date" content="%s">' % esc(pub["year"]))

    vt = pub.get("venue_type")
    if vt == "journal":
        tags.append('<meta name="citation_journal_title" content="%s">' % esc(pub["venue"]))
    elif vt in ("conference", "workshop"):
        tags.append('<meta name="citation_conference_title" content="%s">' % esc(pub["venue"]))

    if pub.get("doi"):
        tags.append('<meta name="citation_doi" content="%s">' % esc(pub["doi"]))
    if pub.get("arxiv_id"):
        tags.append('<meta name="citation_arxiv_id" content="%s">' % esc(pub["arxiv_id"]))
    pdf = (pub.get("links") or {}).get("pdf_direct")
    if pdf:
        tags.append('<meta name="citation_pdf_url" content="%s">' % esc(pdf))
    tags.append('<meta name="citation_language" content="en">')
    return "\n".join(tags)


def build_paper(site, pub, prev_pub, next_pub):
    base = site["url"].rstrip("/")
    url = "%s/papers/%s/" % (base, pub["slug"])
    prefix = "../../"

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": site["name"], "item": base + "/"},
            {"@type": "ListItem", "position": 2, "name": "Publications", "item": base + "/papers/"},
            {"@type": "ListItem", "position": 3, "name": pub["title"], "item": url},
        ],
    }

    extra = "\n" + citation_meta(pub) + "\n" + ld_script(article_ld(site, pub)) \
            + "\n" + ld_script(breadcrumb_ld)

    # Prefer a full-resolution figure on the landing page; the list thumbnail
    # is usually a crop.
    figure_src = pub.get("figure") or pub.get("image")
    figure = ""
    if figure_src:
        figure = (
            '<figure class="paper-figure">'
            '<img src="%s%s" alt="%s" loading="lazy" decoding="async">'
            '</figure>'
        ) % (prefix, esc(figure_src), esc(pub.get("image_alt") or pub["title"]))

    venue_line = "%s, %s" % (esc(pub["venue"]), esc(pub["year"]))
    if pub.get("award"):
        venue_line += ' &middot; <span class="pub-award">%s 🎗</span>' % esc(pub["award"])

    links = pub.get("links") or {}
    buttons = []
    if links.get("pdf"):
        buttons.append('<a href="%s" class="btn btn-publication" target="_blank" rel="noopener">'
                       '<span class="material-icons">picture_as_pdf</span> PDF</a>' % esc(links["pdf"]))
    if links.get("arxiv"):
        buttons.append('<a href="%s" class="btn btn-publication" target="_blank" rel="noopener">'
                       '<span class="material-icons">description</span> arXiv</a>' % esc(links["arxiv"]))
    if links.get("video"):
        buttons.append('<a href="#" class="btn btn-publication" data-video="%s%s">'
                       '<span class="material-icons">play_circle</span> Video</a>'
                       % (prefix, esc(links["video"])))
    if links.get("code"):
        buttons.append('<a href="%s" class="btn btn-publication" target="_blank" rel="noopener">'
                       '<span class="material-icons">code</span> Code</a>' % esc(links["code"]))

    equal = ""
    if pub.get("equal_contribution"):
        equal = '<p class="paper-meta">* Equal contribution by %s.</p>' % esc(
            " and ".join(pub["equal_contribution"]))

    video_modal = ""
    if links.get("video"):
        video_modal = """
<div id="videoModal" class="modal" role="dialog" aria-modal="true" aria-label="Video player">
  <div class="modal-content">
    <button type="button" class="close-btn" aria-label="Close video">&times;</button>
    <video id="modalVideo" controls preload="none">
      <source src="" type="video/mp4">
      Your browser does not support the video tag.
    </video>
  </div>
</div>
"""

    nav = []
    if prev_pub:
        nav.append('<a href="../%s/">&larr; %s</a>' % (esc(prev_pub["slug"]), esc(prev_pub["venue_short"])))
    nav.append('<a href="../">All publications</a>')
    if next_pub:
        nav.append('<a href="../%s/">%s &rarr;</a>' % (esc(next_pub["slug"]), esc(next_pub["venue_short"])))

    body = f"""<body>
<a class="skip-link" href="#main">Skip to content</a>
{video_modal}
<main id="main" class="page">

  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="{prefix}">{esc(site['name'])}</a> &rsaquo;
    <a href="../">Publications</a> &rsaquo;
    <span>{esc(pub['venue_short'])}</span>
  </nav>

  <article>
    <header class="paper-header">
      <h1 class="paper-title">{esc(pub['title'])}</h1>
      <p class="paper-authors">{authors_html(pub['authors'])}</p>
      <p class="paper-meta">{venue_line}</p>
      {equal}
      <div class="pub-links">{''.join(buttons)}</div>
    </header>

    {figure}

    <section class="paper-section">
      <h2>Summary</h2>
      <p>{esc(pub['description'])}</p>
    </section>

    <section class="paper-section">
      <h2>BibTeX</h2>
      <pre class="paper-bibtex" id="bibtex-{esc(pub['slug'])}">{esc(pub['bibtex'])}</pre>
      <button type="button" class="btn btn-publication" data-copy-target="bibtex-{esc(pub['slug'])}" data-label="Copy BibTeX">
        <span class="material-icons">content_copy</span> Copy BibTeX
      </button>
    </section>
  </article>

  <nav class="footer-nav" aria-label="Publication navigation">
    {' &middot; '.join(nav)}
  </nav>

</main>
"""

    return (head(site,
                 title="%s — %s" % (pub["title"], site["name"]),
                 description=pub["tldr"],
                 url_path="papers/%s/" % pub["slug"],
                 prefix=prefix,
                 og_image=pub.get("image") or site["profile_image"],
                 og_type="article",
                 extra=extra)
            + body
            + footer(site, prefix))


def build_papers_index(site, pubs):
    rows = []
    for pub in pubs:
        award = ""
        if pub.get("award"):
            award = ' &middot; <span class="pub-award">%s 🎗</span>' % esc(pub["award"])
        rows.append(
            '<li class="pub-item" data-category="%s"><div class="pub-body">'
            '<h3 class="pub-title"><a href="%s/">%s</a></h3>'
            '<div class="pub-authors">%s</div>'
            '<div class="pub-venue">%s, %s%s</div>'
            '</div></li>'
            % (esc(pub["category"]), esc(pub["slug"]), esc(pub["title"]),
               authors_html(pub["authors"]), esc(pub["venue"]), esc(pub["year"]), award))

    body = f"""<body>
<a class="skip-link" href="#main">Skip to content</a>
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="../">{esc(site['name'])}</a> &rsaquo; <span>Publications</span>
  </nav>
  <h1 class="h-name">Publications</h1>
  <p>All {len(pubs)} publications by {esc(site['name'])}, newest first.
     Each links to a page with the abstract and citation.</p>
  <ol class="pub-list pub-list-compact" data-filter="all">
{chr(10).join('    ' + r for r in rows)}
  </ol>
</main>
"""

    return (head(site,
                 title="Publications — %s" % site["name"],
                 description="Complete list of %d publications by %s, spanning ICML, AAAI, IROS, EACL and ECML PKDD."
                             % (len(pubs), site["name"]),
                 url_path="papers/",
                 prefix="../")
            + body
            + footer(site, "../"))


# ------------------------------------------------------------- 404 page ---

def build_404(site):
    body = f"""<body>
<main id="main" class="page">
  <h1 class="h-name">Page not found</h1>
  <p>That page doesn't exist. Try the <a href="/">homepage</a> or the
     <a href="/papers/">list of publications</a>.</p>
</main>
"""
    return (head(site, title="Page not found — %s" % site["name"],
                 description="Page not found.", url_path="404.html", prefix="/")
            + body + footer(site, "/"))


# ------------------------------------------------------- text artefacts ---

def build_llms_txt(site, pubs, news):
    base = site["url"].rstrip("/")
    lines = ["# %s" % site["name"], ""]
    lines.append("> %s" % site["description"])
    lines.append("> Contact: %s" % site["email"])
    lines.append("")

    lines.append("## Research focus")
    lines.append("")
    for item in site["research_focus"]:
        lines.append("- %s" % item)
    lines.append("")

    lines.append("## Pages")
    lines.append("")
    lines.append("- [Homepage](%s/): biography, news, and all publications" % base)
    lines.append("- [Publications](%s/papers/): complete list of %d publications" % (base, len(pubs)))
    lines.append("- [CV](%s/data/CV.pdf): curriculum vitae (PDF)" % base)
    lines.append("")

    lines.append("## Publications")
    lines.append("")
    for pub in pubs:
        award = " %s." % pub["award"] if pub.get("award") else ""
        lines.append("- [%s](%s/papers/%s/) — %s. %s.%s Authors: %s."
                     % (pub["title"], base, pub["slug"], pub["venue_short"],
                        pub["tldr"].rstrip("."), award, authors_plain(pub["authors"])))
    lines.append("")

    lines.append("## Recent news")
    lines.append("")
    for item in news[:6]:
        lines.append("- %s: %s" % (item["date"], strip_tags(item["html"]).strip()))
    lines.append("")

    lines.append("## Profiles")
    lines.append("")
    for link in site["same_as"]:
        lines.append("- %s" % link)
    lines.append("")

    return "\n".join(lines)


def build_sitemap(site, pubs):
    base = site["url"].rstrip("/")
    entries = [(base + "/", "1.0", "monthly"),
               (base + "/papers/", "0.9", "monthly"),
               (base + "/data/CV.pdf", "0.6", "monthly")]
    for pub in pubs:
        entries.append(("%s/papers/%s/" % (base, pub["slug"]), "0.8", "yearly"))

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, priority, freq in entries:
        out.append("  <url>")
        out.append("    <loc>%s</loc>" % esc(loc))
        out.append("    <lastmod>%s</lastmod>" % BUILD_DATE)
        out.append("    <changefreq>%s</changefreq>" % freq)
        out.append("    <priority>%s</priority>" % priority)
        out.append("  </url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def build_robots(site):
    base = site["url"].rstrip("/")
    lines = ["# Everyone may index this site.",
             "User-agent: *",
             "Allow: /",
             ""]
    lines.append("# Explicitly welcome AI/LLM crawlers so this work is discoverable")
    lines.append("# through assistants and generative search as well as classic search.")
    for agent in site["llm_user_agents"]:
        lines.append("User-agent: %s" % agent)
        lines.append("Allow: /")
        lines.append("")
    lines.append("Sitemap: %s/sitemap.xml" % base)
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------ validation ---

def validate(site, pubs, news):
    errors = []
    slugs = set()
    for pub in pubs:
        for field in ("id", "slug", "title", "authors", "venue", "venue_short",
                      "year", "sort_key", "category", "description", "tldr", "bibtex"):
            if not pub.get(field):
                errors.append("%s: missing required field %r" % (pub.get("id", "?"), field))
        if pub.get("category") not in ("conference", "preprint"):
            errors.append("%s: category must be 'conference' or 'preprint'" % pub.get("id"))
        if pub.get("slug") in slugs:
            errors.append("duplicate slug %r" % pub.get("slug"))
        slugs.add(pub.get("slug"))
        for key in ("image", "figure"):
            if pub.get(key) and not os.path.exists(os.path.join(ROOT, pub[key])):
                errors.append("%s: %s not found: %s" % (pub["id"], key, pub[key]))
        video = (pub.get("links") or {}).get("video")
        if video and not os.path.exists(os.path.join(ROOT, video)):
            errors.append("%s: video not found: %s" % (pub["id"], video))

    for item in news:
        for src in re.findall(r'<img[^>]+src="([^"]+)"', item.get("html", "")):
            if src.startswith("http"):
                errors.append("news %s: hotlinked image, host a local copy: %s"
                              % (item["date"], src))
            elif not os.path.exists(os.path.join(ROOT, src)):
                errors.append("news %s: image not found: %s" % (item["date"], src))

    return errors


# ------------------------------------------------------------------ main ---

def main():
    site = load(os.path.join(DATA, "site.json"))
    pubs = load(os.path.join(DATA, "publications.json"))
    news = load(os.path.join(DATA, "news.json"))
    intro = read(os.path.join(PAGES, "intro.html"))

    pubs.sort(key=lambda p: p["sort_key"], reverse=True)
    news.sort(key=lambda n: n["sort_key"], reverse=True)

    errors = validate(site, pubs, news)
    if errors:
        print("Build failed:", file=sys.stderr)
        for err in errors:
            print("  - %s" % err, file=sys.stderr)
        return 1

    print("Building %s (%d publications, %d news items)"
          % (site["url"], len(pubs), len(news)))

    write("index.html", build_index(site, pubs, news, intro))
    write("papers/index.html", build_papers_index(site, pubs))

    for i, pub in enumerate(pubs):
        prev_pub = pubs[i - 1] if i > 0 else None
        next_pub = pubs[i + 1] if i + 1 < len(pubs) else None
        write("papers/%s/index.html" % pub["slug"], build_paper(site, pub, prev_pub, next_pub))

    # Drop landing pages for papers no longer in publications.json, so a
    # removed paper cannot linger as a live URL that is absent from the sitemap.
    papers_dir = os.path.join(ROOT, "papers")
    slugs = {p["slug"] for p in pubs}
    for entry in sorted(os.listdir(papers_dir)):
        path = os.path.join(papers_dir, entry)
        if os.path.isdir(path) and entry not in slugs:
            shutil.rmtree(path)
            print("  removed stale papers/%s/" % entry)

    write("404.html", build_404(site))
    write("llms.txt", build_llms_txt(site, pubs, news))
    write("sitemap.xml", build_sitemap(site, pubs))
    write("robots.txt", build_robots(site))

    # GitHub Pages: serve files verbatim, no Jekyll processing.
    open(os.path.join(ROOT, ".nojekyll"), "w").close()

    if not site.get("goatcounter_code"):
        print("\n  note: data/site.json has no goatcounter_code — "
              "analytics tag omitted from output.")
    if not site.get("google_site_verification"):
        print("  note: data/site.json has no google_site_verification — "
              "Search Console tag omitted.")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
