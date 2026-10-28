"""Fetch Coimbatore district news candidates. Free sources only; polite 1.5 s gaps. Used inside GitHub Actions."""
import re, time, html
import requests
UA = {"User-Agent": "Mozilla/5.0 (compatible; Coimbatore360-research/1.0)"}
DISTRICT = "tamil-nadu-district-news-coimbatore"      # Dinamalar's Coimbatore district page
LIST_URL = "https://www.dinamalar.com/news/" + DISTRICT


def _get(u):
    time.sleep(1.5)
    r = requests.get(u, headers=UA, timeout=40)
    r.raise_for_status()
    return r.text


def candidate_links(limit=15):
    h = _get(LIST_URL)
    links = []
    for m in re.finditer(r'href="(/news/[^"#?]+?/\d{6,})"', h):
        u = "https://www.dinamalar.com" + m.group(1)
        if u not in links:
            links.append(u)
    # 27 Oct: only the first 8 stories are <a href> links; the rest of the district list sits in the page data as
    # '/news/tamil-nadu-district-news-coimbatore/<id>/<slug>'
    for m in re.finditer(r'/news/(' + DISTRICT + r')/(?:(\d{6,})/([a-z0-9-]+)|([a-z0-9-]+)/(\d{6,}))', h):
        slug, nid = (m.group(3), m.group(2)) if m.group(2) else (m.group(4), m.group(5))
        u = f"https://www.dinamalar.com/news/{m.group(1)}/{slug}/{nid}"
        if u not in links:
            links.append(u)
    return links[:limit]


def article(url):
    """returns dict(title, published, text) parsed from the page"""
    h = _get(url)
    def g(pat):
        m = re.search(pat, h)
        return html.unescape(m.group(1)).strip() if m else ""
    title = g(r'"newstitle"\s*:\s*"([^"]+)"') or g(r"<title>([^<]+)</title>")
    pub = g(r'"publisheddate"\s*:\s*"([^"]+)"')
    body = g(r'"articleBody"\s*:\s*"([^"]{80,})"').replace("\\n", "\n")
    h2 = re.sub(r"<(style|script|noscript|svg)[^>]*>.*?</\1>", " ", h, flags=re.S)
    paras = [html.unescape(x).strip() for x in re.sub(r"<[^>]+>", "\n", h2).split("\n")]
    paras = [re.sub(r"\s+", " ", x) for x in paras if len(x) > 60 and re.search(r"[\u0B80-\u0BFF]", x) and "{" not in x and "css-" not in x]
    seen, out = set(), []
    for x in paras:
        if x not in seen:
            seen.add(x); out.append(x)
    text = body if len(body) > 200 else "\n".join(out)
    return {"url": url, "title": title, "published": pub, "text": text.strip()}
