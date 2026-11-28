"""owner 28 Nov: ADD NEWS from the News360 Backend (news360-backend.pages.dev, screen "Add news").
The owner types a news there - content, extra details, a follow-up of an earlier post, a news link, a picture, a note with extra
instructions. The request waits in the backend's private store; this file is the page's side of it:

  python research_free/backend_news.py peek   every posting run (cheap, standard library only): is a request waiting for this page?
                                              then backend_news.yml is started. It also tells the backend what became of the earlier
                                              requests (posted with the links / held by a check with the reason), read from this
                                              repository's own records.
  python research_free/backend_news.py run    (backend_news.yml) each waiting request is written by the same free writer chain as every
                                              other news, with the owner's instructions; the picture is the owner's, or an AI picture
                                              made the usual way; the story is saved in the page's Sheet and the posting job posts it
                                              on Instagram, then Facebook and YouTube - through every usual check.

Nothing is posted from here. Without the secrets DASH_URL / DASH_WRITE_KEY both commands do nothing and never fail a run.
The same file is in all 7 page repositories."""
import base64
import datetime
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
STORE = os.environ.get("DASH_URL", "").strip()
KEY = os.environ.get("DASH_WRITE_KEY", "").strip()
WORKFLOW = "backend_news.yml"
FOLLOW_NOTE = "backend follow-up"      # in the Sheet row's notes: poster/freshness.py owner_follow_up() - never held as a duplicate
OWNER_TEXT_NOTE = "backend owner text"      # in the notes: poster/factgate.py - the owner's own words are not checked against a link
FORMAT_NOTE = "backend format"      # in the notes, followed by "post" or "carousel": poster/post.py backend_format() - a picture post, no reel
FOLLOW_FACT = "முந்தைய செய்தியின் தொடர்ச்சி: இந்த விவகாரம் குறித்து இந்தப் பக்கத்தில் முன்பு செய்தி வெளியானது."
OWNER_PICTURE = "(picture given by the owner in the backend)"


def log(*a):
    print("backend news:", *a, flush=True)


def pages():
    """the pages this repository posts for (Rasipuram 360 never posts on its own - owner 23 Nov)"""
    name = (os.environ.get("GITHUB_REPOSITORY") or ROOT.name).split("/")[-1].lower()
    return ["namakkal"] if name.startswith("news360") else [name.split("360")[0]]


def store(action, **kw):
    """one question to the backend's store (the key goes in the body, never in the link)"""
    body = json.dumps(dict(kw, action=action, key=KEY)).encode("utf-8")
    req = urllib.request.Request(STORE, data=body, headers={"Content-Type": "text/plain;charset=utf-8"})
    with urllib.request.urlopen(req, timeout=120) as r:      # the store answers through one redirect, which is followed
        return json.loads(r.read().decode("utf-8"))


def done(req, status, story="", msg="", links=None):
    try:
        store("manual_done", id=req["id"], status=status, story=story, msg=str(msg or "")[:480], links=links or {})
    except Exception as e:
        log(f"{req.get('id')}: the backend was not told ({status}):", str(e)[:120])


# ---------------------------------------------------------------------------------------------------- peek (every posting run)
def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def story_state(page, story, root=None):
    """what this repository's own records say about a story: ('posted', links, '') | ('held', {}, why) | ('', {}, '')"""
    root = Path(root or ROOT)
    links, media = {}, ""
    rec = sorted((root / "poster" / "posted").glob(f"*-{page}-{story}.json"))
    if rec:
        d = _load(rec[-1])
        if str(d.get("link") or "").startswith("https://"):
            links["instagram"] = d["link"]
        media = str(d.get("media_id") or "")
    for kind in ("reel", "photos"):      # a reel, or the pictures of a poster / carousel
        fb = _load(root / "poster" / "fb_posted" / f"{page}-{story}-{kind}.json")
        if fb.get("status") == "posted" and str(fb.get("link") or "").startswith("https://"):
            links["facebook"] = fb["link"]
    for u in (_load(root / "poster" / "yt_uploaded" / f"{page}.json").get("uploads") or []):
        if media and str(u.get("ig")) == media and u.get("youtube"):
            links["youtube"] = "https://youtube.com/shorts/" + str(u["youtube"])
    if links.get("instagram"):
        return "posted", links, ""
    try:
        for line in (root / ".last_check").read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"[\d:]+ SKIP (RN-\d+) (.+)", line)
            if m and m.group(1) == story:
                return "held", {}, m.group(2).strip()[:300]
    except Exception:
        pass
    return "", {}, ""


def start_workflow():
    """start backend_news.yml now; False when there is no token (its own 15-minute schedule then takes the request)"""
    tok, repo = os.environ.get("GH_TOKEN"), os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if not tok or not repo:
        return False
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/dispatches",
                                     data=json.dumps({"ref": "main"}).encode("utf-8"), method="POST",
                                     headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                                              "Content-Type": "application/json", "User-Agent": "news360-backend-news"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 204
    except Exception as e:
        log("the writer job was not started (its schedule takes it):", str(e)[:120])
        return False


def peek():
    if not STORE or not KEY:
        return 0      # not set up for this repository: silent, the posting run goes on
    got = store("manual_take", pages=pages(), peek=True)
    for it in got.get("open") or []:      # tell the backend what became of the news added earlier
        status, links, why = story_state(it.get("page"), it.get("story"))
        new_links = {k: v for k, v in links.items() if not (it.get("links") or {}).get(k)}
        if status == "posted" and (it.get("status") != "posted" or new_links):
            done(it, "posted", story=it.get("story"), msg="", links=links)
            log(f"{it['id']} {it.get('story')}: posted", sorted(links))
        elif status == "held" and it.get("status") == "filed":
            done(it, "held", story=it.get("story"), msg=why)
            log(f"{it['id']} {it.get('story')}: held -", why[:100])
    n = int(got.get("waiting") or 0)
    if n:
        log(f"{n} news waiting in the backend -", "the writer job is started" if start_workflow() else "the writer job's schedule takes it")
    return n


# ---------------------------------------------------------------------------------------------------- run (backend_news.yml)
def to_reel_size(data):
    """the owner's picture as a 9:16 JPEG (centre crop, never stretched), 1152 x 2048 like the pipeline's own pictures"""
    from io import BytesIO
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(BytesIO(data))).convert("RGB")      # a phone photo keeps its upright position
    w, h = im.size
    if w * 16 > h * 9:
        nw = round(h * 9 / 16)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    elif w * 16 < h * 9:
        nh = round(w * 16 / 9)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im = im.resize((1152, 2048), Image.LANCZOS)
    out = BytesIO()
    im.save(out, "JPEG", quality=93, subsampling=0)
    return out.getvalue()


def article(req, collect):
    """the 'article' the writer works from: the owner's own words first, then the extra details, then the linked article's text"""
    text, details, link = (str(req.get(k) or "").strip() for k in ("text", "details", "link"))
    linked = None
    if link:
        try:
            linked = collect.open_article({"url": link, "alts": [], "title": "", "published": ""})
        except Exception as e:
            if not text:
                raise RuntimeError(f"the news link could not be opened ({str(e)[:100]}) - add the news again with its content typed in")
            log(f"{req['id']}: the link could not be opened, written from the typed content only:", str(e)[:100])
    parts = [p for p in (text, ("கூடுதல் விவரங்கள்:\n" + details) if details else "") if p]
    if linked and (linked.get("text") or "").strip():
        parts.append(("செய்தி இணைப்பில் உள்ள கட்டுரை:\n" if parts else "") + linked["text"].strip())
    if not parts:
        raise RuntimeError("the news link has no readable article text - add the news again with its content typed in")
    if req.get("kind") == "followup":
        parts.append(FOLLOW_FACT)      # a fact of the 'article', so the mention passes the writer's own fact check
    first = next((ln.strip() for ln in text.split("\n") if ln.strip()), "")
    title = (first[:140] if first else "") or (linked or {}).get("title") or ""
    return {"url": (linked or {}).get("url") or link, "title": title, "text": "\n\n".join(parts),
            "published": datetime.datetime.now(IST).isoformat(timespec="seconds"), "manual": True}


def instructions(req):
    """the extra lines the writer gets for this one story (research_free/run.py EXTRA)"""
    out = ["THIS NEWS WAS GIVEN BY THE PAGE OWNER BY HAND. Write the post only from the text above. If the text is in English, write the post in Tamil as always."]
    if req.get("kind") == "followup":
        out.append("FOLLOW-UP: this continues a news this page posted earlier" + (f" ({str(req.get('old'))[:200]})" if req.get("old") else "") +
                   ". Report the NEW development as the news. In the caption, after the news, add one short paragraph that begins with "
                   "'📌 முந்தைய செய்தியின் தொடர்ச்சி:' and says this page reported the matter earlier and what has changed now. "
                   "Say the same in one sentence of the reel_script, just before the fixed closing sentence.")
    note = str(req.get("note") or "").strip()
    if note:
        out.append("THE OWNER'S EXTRA INSTRUCTIONS FOR THIS STORY (follow them; they never allow a fact that is not in the text):\n" + note[:1500])
    return "\n".join(out)


def build(req, collect, writer, recent):
    """(story for the Sheet, '') or (None, why it could not be made)"""
    art = article(req, collect)
    today = datetime.datetime.now(IST).strftime("%A %d %B %Y")
    writer.EXTRA[0] = instructions(req)
    try:
        d, model, errors, att = writer.write(art, today)
    finally:
        writer.EXTRA[0] = ""
    if not collect.tamil_source(art):      # content typed in English: its words cannot be 'found' in the Tamil draft
        errors = [e for e in errors if "not grounded" not in e]
    if isinstance(d, dict):
        d.setdefault("post_to", "Namakkal 360")
    follow = req.get("kind") == "followup"
    story, why = collect.file_story(art, (d, model, errors, att), [], [] if follow else recent)
    if not story:
        return None, why
    if pages() == ["namakkal"] and hasattr(collect, "district_wide"):      # the Namakkal repository's own rule (collect.py main)
        story["post_to"] = "Namakkal 360 (collab: Rasipuram 360)" if collect.district_wide(story) else "Namakkal 360"
    own = bool(str(req.get("text") or "").strip() or str(req.get("details") or "").strip())
    fmt = str(req.get("format") or "reel").lower()      # reel (normal) | post (one poster) | carousel (2 or more slides)
    story["note"] = (f"manual BACKEND news {req['id']} by {str(req.get('by') or '')[:40]}" +
                     (f"; {FOLLOW_NOTE} of {str(req.get('old') or '')[:120]}" if follow else "") + (f"; {OWNER_TEXT_NOTE}" if own else "") +
                     (f"; {FORMAT_NOTE} {fmt}" if fmt in ("post", "carousel") else "") +
                     f" | {model}, {att} attempt(s), {len(errors)} validator problem(s)")
    img = req.get("image") or {}
    if img.get("data"):
        try:
            story["images"] = [collect._upload_image(to_reel_size(base64.b64decode(img["data"])))]
            story["prompts"] = OWNER_PICTURE      # one picture given = no picture to make
        except Exception as e:
            log(f"{req['id']}: the owner's picture could not be used, an AI picture is made:", str(e)[:120])
    return story, ""


def story_id(collect, story):
    """the RN number the Sheet gave the story just saved ('' when it cannot be read - the status then stays 'filed' without a number)"""
    try:
        rows = (collect.bridge("recent") or {}).get("rows") or []
        mine = [r for r in rows if str(r.get("headline_ta") or "").strip() == str(story.get("tamil_headline") or "").strip()]
        return str(mine[-1].get("story_id") or "") if mine else ""
    except Exception as e:
        log("the story number could not be read:", str(e)[:100])
        return ""


def run():
    if not STORE or not KEY:
        log("DASH_URL / DASH_WRITE_KEY are not set in this repository - nothing to do")
        return 0
    items = (store("manual_take", pages=pages(), max=2).get("items")) or []
    if not items:
        log("nothing waiting")
        return 0
    sys.path.insert(0, str(HERE))
    import collect
    import run as writer
    recent = []
    try:
        rr = collect.bridge("recent")
        recent = rr.get("rows") or [] if rr.get("ok") else []
    except Exception as e:
        log("the Sheet's recent stories could not be read (the duplicate check at posting still runs):", str(e)[:100])
    filed = 0
    for req in items:
        log(f"{req['id']} ({req.get('page')}, {req.get('kind')}, by {req.get('by')}): writing")
        try:
            story, why = build(req, collect, writer, recent)
            if not story:
                done(req, "problem", msg="not written: " + str(why))
                log(f"{req['id']}: not written -", why)
                continue
            if not collect.send_batch([story], [], images=not story.get("images")):
                done(req, "waiting", msg="the page's Sheet did not answer - tried again in the next run")
                log(f"{req['id']}: the Sheet did not take it - tried again later")
                continue
            sid = story_id(collect, story)
            held = "NOT CLEAN" in str(story.get("verification") or "")
            done(req, "held" if held else "filed", story=sid,
                 msg=("written, but held by the fact check - the automatic fix job corrects it: " + str(story.get("verification"))[-250:]) if held else "written - the posting job posts it")
            filed += 1
            log(f"{req['id']}: saved as {sid or 'a new story'} - {story.get('tamil_headline')}")
        except Exception as e:
            done(req, "problem", msg=f"could not be written ({type(e).__name__}: {str(e)[:300]}) - add it again")
            log(f"{req['id']}: failed -", type(e).__name__, str(e)[:300])
    if filed:
        try:
            collect.trigger_posting([])
        except Exception as e:
            log("the posting job was not started (its schedule posts it):", str(e)[:100])
    return filed


def waiting():
    """how many requests wait for this page (backend_news.yml asks before it installs anything)"""
    if not STORE or not KEY:
        return 0
    return int(store("manual_take", pages=pages(), peek=True).get("waiting") or 0)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "peek"
    try:
        if mode == "waiting":
            print(waiting())
        elif mode == "run":
            run()
        else:
            peek()
    except Exception as e:      # this never fails a posting run
        log(f"{mode} skipped:", type(e).__name__, str(e)[:200])
        if mode == "waiting":
            print(0)
