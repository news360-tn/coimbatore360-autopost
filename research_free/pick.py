"""Coimbatore 360 - owner's pick flow (owner 1 Nov).

Twice a day (6:00 AM and 4:00 PM IST) the news of Dinamalar and Dinamani's Coimbatore pages ONLY is collected - by the article's own
published time, in back-to-back windows (yesterday 4 PM -> 6 AM, then 6 AM -> 4 PM; a late or failed round continues from the last end).
The list goes to the owner by e-mail with a check-box page (Apps Script bridge). The owner ticks news and presses Submit:
EVERY ticked news is written and posted (no other check). No submit within 1 hour: the top 12 by importance are written and posted.
A submit after the automatic pick ADDS the extra ticked news. Already posted news is never listed again; news listed but not posted
comes back in the next round's list while it is less than 24 hours old.

  python research_free/pick.py collect   -> collect, save the round, send the list (prints the round id)
  python research_free/pick.py decide    -> wait for the submit (max WAIT_MIN) or pick the top 12; writes the links to pick_urls.txt
  python research_free/pick.py late      -> links ticked after the decision and not written yet -> pick_urls.txt ('' when none)
State: research_free/archive/pick_state.json (committed by the workflow)."""
import datetime, difflib, hashlib, json, os, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import allnews      # noqa: E402

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
STATE = HERE / "archive" / "pick_state.json"
URLS = HERE / "results" / "pick_urls.txt"
AUTO_TOP = int(os.environ.get("PICK_AUTO_TOP", "12"))
WAIT_MIN = int(os.environ.get("PICK_WAIT_MIN", "60"))
LEFT_HOURS = 24
FIRST_WINDOW_H = 14
AD = re.compile(r"தள்ளுபடி|ஆஃபர்|ஆபர்|அள்ளுங்க|அள்ளுவோம்|விற்பனை தொடக்கம்|ஷோரூம்|புதிய கிளை திறப்பு|சிறப்பு விற்பனை")      # advertorials, not news
DRY = os.environ.get("PICK_DRY", "") in ("1", "true", "yes")


def log(*a):
    print(datetime.datetime.now(IST).strftime("%H:%M:%S"), *a, flush=True)


def now():
    return datetime.datetime.now(IST)


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_end": "", "pool": {}, "rounds": {}}


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    rounds = dict(sorted(st.get("rounds", {}).items())[-20:])      # keep the last 10 days of rounds
    st["rounds"] = rounds
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def pid(url):
    return "C" + hashlib.sha1(url.encode()).hexdigest()[:7]


def when(s):
    try:
        t = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=IST)
    except Exception:
        return None


def summary(text, title):
    """the first one or two sentences of the article that add to the headline (max ~220 characters)"""
    t = re.sub(r"\s+", " ", text or "").strip()
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", t):
        if len(s) < 25 or difflib.SequenceMatcher(None, s, title or "").ratio() > 0.8:
            continue
        out = (out + " " + s).strip()
        if len(out) > 140:
            break
    return (out[:217] + "...") if len(out) > 220 else out


def category(title):
    import collect
    k = collect.top_kind(title) or ""
    names = {"power_cut": "மின்தடை", "rain": "மழை / வானிலை", "crime": "குற்றம்", "accident": "விபத்து"}
    if k in names:
        return names[k]
    for w, c in (("குடிநீர்", "குடிநீர்"), ("மாநகராட்சி", "மாநகராட்சி"), ("சாலை", "சாலை"), ("ரயில்", "ரயில்"), ("பேருந்து", "போக்குவரத்து"),
                 ("நீதிமன்ற", "நீதிமன்றம்"), ("கல்லூரி", "கல்வி"), ("பள்ளி", "கல்வி"), ("வேலைவாய்ப்பு", "வேலைவாய்ப்பு"), ("விலை", "விலை"),
                 ("கோயில்", "ஆன்மிகம்"), ("கோவில்", "ஆன்மிகம்")):
        if w in title:
            return c
    return "பொது"


def candidates(log_lines, since=None):
    """Dinamalar Coimbatore district list + Dinamani Coimbatore edition: article links"""
    items = []
    try:
        items += allnews.from_dinamalar_list()
    except Exception as e:
        log_lines.append(f"Dinamalar list failed: {str(e)[:120]}")
    try:
        cfgs = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
        for cfg in cfgs:
            if "dinamani.com" in cfg["url"]:
                items += allnews.from_listing(dict(cfg, limit=80))
    except Exception as e:
        log_lines.append(f"Dinamani list failed: {str(e)[:120]}")
    # the district list pages show only the latest ~20-40 news: Google / Bing news searches limited to the two papers fill the rest of the window
    for q in ("கோவை", "கோயம்புத்தூர்", "பொள்ளாச்சி", "மேட்டுப்பாளையம்"):
        for dom in ("dinamalar.com", "dinamani.com"):
            for fn in (allnews.from_google, allnews.from_bing):
                try:
                    got = [x for x in fn(f"{q} site:{dom}") if dom in (x.get("site", "") + x.get("url", ""))
                           and not (since and when(x.get("published")) and when(x.get("published")) < since)]      # older than the window: not opened
                    items += got
                except Exception as e:
                    log_lines.append(f"{fn.__name__} {dom} '{q}' failed: {str(e)[:80]}")
    seen, out = set(), []
    for it in items:
        u = it["url"]
        if "news.google.com" in u:
            try:
                u = allnews.resolve(u)
            except Exception:
                continue
        u = u.split("?")[0].rstrip("/").replace("dinamani.com/amp/story/", "dinamani.com/")
        if u not in seen and ("dinamalar.com/news" in u or "dinamani.com/" in u):
            seen.add(u)
            out.append(dict(it, url=u))
    return out


def is_posted(url, title, recent):
    import collect
    for r in recent:
        if r.get("source") and r["source"].split("?")[0].rstrip("/") == url:
            return True
        if title and collect._fr().similar(r.get("headline_ta", ""), title, 0.6, r.get("researched")):
            return True
    return False


def check_article(it, recent):
    """-> (item dict, '') when it is real Coimbatore district news, else (None, reason)"""
    import collect
    try:
        art = allnews.article_any(it["url"])
    except Exception as e:
        return None, f"could not open ({str(e)[:50]})"
    art["url"] = it["url"]
    title = re.sub(r"\s+", " ", (art.get("title") or "").replace("ுா", "ூ")).strip()
    if not title:
        return None, "no title"
    if len(collect.body_words(art)) < collect.HEADLINE_ONLY_MIN:
        return None, "only a headline"
    if not collect.tamil_source(art):
        return None, "not Tamil"
    if not (allnews.has_place(title) or allnews.has_place(art["text"][:400]) or allnews.url_district(it["url"]) in allnews.DISTRICT_SLUGS
            or it.get("via") == "dinamalar-list") or not allnews.local_ok(it["url"], title):
        return None, "not Coimbatore district"
    if allnews.other_district(title):
        return None, "other district"
    if AD.search(title):
        return None, "shop offer / advertisement"
    low = collect.low_interest(title, it["url"])
    if low and ("feature" in low or "editorial" in low):
        return None, low      # recipes, tips, opinion: not news (ceremonies / awards stay - the owner decides)
    if is_posted(it["url"], title, recent):
        return None, "already posted"
    if collect.same_event_filed(dict(art, title=title), recent, days=2):
        return None, "same event already posted"
    pub = art.get("published") or ""
    n = {"title": title, "snippet": art["text"][:400], "published": pub, "mentions": 1}
    return {"id": pid(it["url"]), "url": it["url"], "title": title, "summary": summary(art["text"], title),
            "source": "தினமலர்" if "dinamalar.com" in it["url"] else "தினமணி", "published": pub, "category": category(title),
            "score": collect.score(n), "power_cut": bool(collect._fr().is_power_cut(title))}, ""


def merge_same(items):
    """the same news from both papers is listed once (both sources noted)"""
    out = []
    for it in items:
        hit = next((o for o in out if difflib.SequenceMatcher(None, o["title"], it["title"]).ratio() > 0.62), None)
        if hit:
            if it["source"] not in hit["source"]:
                hit["source"] += " + " + it["source"]
            hit.setdefault("alts", []).append(it["url"])
            hit["score"] = max(hit["score"], it["score"]) + 1
        else:
            out.append(it)
    return out


def rank(items):
    return sorted(items, key=lambda x: (not x.get("power_cut"), -x.get("score", 0), str(x.get("published", ""))), reverse=False)


def bridge_get(action, **kw):
    import collect
    return collect.bridge(action, **kw)


def bridge_post(action, payload):
    import requests
    r = requests.post(os.environ["BRIDGE_URL"], params={"key": os.environ["BRIDGE_KEY"]},
                      data=json.dumps({"action": action, **payload}, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, timeout=120)
    r.raise_for_status()
    d = r.json()
    if not d.get("ok"):
        raise RuntimeError(f"bridge {action}: {d.get('error')}")
    return d


def recent_rows():
    rr = bridge_get("recent")
    if not rr.get("ok"):
        raise RuntimeError(f"bridge recent: {rr}")
    return rr["rows"]


def cmd_collect():
    st = load_state()
    t_end = now()
    t_start = when(st.get("last_end")) or (t_end - datetime.timedelta(hours=FIRST_WINDOW_H))
    rid = t_end.strftime("%Y-%m-%d_") + ("morning" if t_end.hour < 12 else "evening")
    log(f"round {rid}: news published {t_start:%d %b %H:%M} -> {t_end:%d %b %H:%M} (Dinamalar + Dinamani Coimbatore)")
    recent = recent_rows()
    lines = []
    cands = candidates(lines, t_start)
    for l in lines:
        log(l)
    log(f"{len(cands)} links on the two papers' Coimbatore pages")
    pool = st.setdefault("pool", {})
    new, reasons = [], {}
    for it in cands:
        if pid(it["url"]) in pool:      # listed in an earlier round: it comes back only as a leftover (below)
            continue
        item, why = check_article(it, recent)
        if not item:
            reasons[why] = reasons.get(why, 0) + 1
            continue
        pt = when(item["published"])
        if pt and pt < t_start:
            reasons["published before this window"] = reasons.get("published before this window", 0) + 1
            continue
        if pt and pt > t_end + datetime.timedelta(minutes=5):
            continue
        new.append(item)
    log("skipped: " + ", ".join(f"{k}={v}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])))
    new = merge_same(new)
    # leftovers: listed before, never posted, less than 24 hours old
    left = []
    for k, it in list(pool.items()):
        pt = when(it.get("published")) or when(it.get("listed_at"))
        if it.get("posted") or it.get("written") or (pt and (t_end - pt).total_seconds() > LEFT_HOURS * 3600):
            pool.pop(k)
            continue
        if is_posted(it["url"], it["title"], recent):
            pool.pop(k)
            continue
        left.append(dict(it, leftover=True))
    new = rank(new)
    left = rank(left)
    for it in new:
        pool[it["id"]] = dict(it, listed_at=t_end.isoformat())
    items = new + left
    log(f"list: {len(new)} new + {len(left)} earlier news not posted yet")
    for i, it in enumerate(items, 1):
        log(f"  {i:2}. [{it['category']}] {it['title'][:70]} ({it['source']}){' (earlier)' if it.get('leftover') else ''}")
    deadline = t_end + datetime.timedelta(minutes=WAIT_MIN)
    st["rounds"][rid] = {"window": [t_start.isoformat(), t_end.isoformat()], "ids": [x["id"] for x in items], "sent": False,
                         "deadline": deadline.isoformat(), "decided": None, "written": []}
    if not DRY and items:
        try:
            bridge_post("pickList", {"round": rid, "deadline": deadline.strftime("%I:%M %p").lstrip("0"), "auto_top": AUTO_TOP,
                                     "window": f"{t_start:%d %b %I:%M %p} – {t_end:%d %b %I:%M %p}",
                                     "items": [{k: x.get(k, "") for k in ("id", "title", "summary", "source", "published", "category", "url")}
                                               | {"leftover": bool(x.get("leftover"))} for x in items]})
            st["rounds"][rid]["sent"] = True
            log("list e-mailed with the check-box page")
        except Exception as e:      # the Apps Script was not updated yet / did not answer: the top 12 are posted without waiting
            log("COULD NOT E-MAIL THE LIST (update + redeploy apps_script/Code.gs):", str(e)[:200])
    elif not items:
        log("no news in this window - no e-mail")
    st["last_end"] = t_end.isoformat()      # the next round starts here (also when this round found nothing)
    if DRY:
        log("DRY RUN: list shown only - no e-mail, the round is not saved")
    else:
        save_state(st)
    print(f"ROUND={rid}")
    return rid


def current_round(st):
    rs = sorted(st.get("rounds", {}).items())
    return rs[-1] if rs else (None, None)


def write_urls(urls):
    URLS.parent.mkdir(parents=True, exist_ok=True)
    URLS.write_text("\n".join(urls), encoding="utf-8")
    print("PICK_URLS=" + " ".join(urls))


def cmd_decide():
    st = load_state()
    rid, rnd = current_round(st)
    if not rid or not rnd.get("ids"):
        log("no list this round - nothing to post")
        return write_urls([])
    pool = st.get("pool", {})
    deadline = when(rnd["deadline"])
    chosen, how = None, ""
    while rnd.get("sent"):      # no e-mail went out: no one can tick - the top 12 at once
        try:
            s = bridge_get("pickStatus", round=rid)
            if s.get("ok") and s.get("submitted"):
                chosen, how = [i for i in s.get("ids", []) if i in pool], f"owner ticked {len(s.get('ids', []))} at {s.get('at')}"
                break
        except Exception as e:
            log("status check failed (tried again):", str(e)[:120])
        if DRY or now() >= deadline:
            break
        time.sleep(60)
    if chosen is None:
        items = rank([pool[i] for i in rnd["ids"] if i in pool])
        chosen, how = [x["id"] for x in items[:AUTO_TOP]], f"no submit by {deadline:%I:%M %p} - automatic top {AUTO_TOP}"
        if not DRY:
            try:
                bridge_post("pickAuto", {"round": rid, "ids": chosen})
            except Exception as e:
                log("could not mark the automatic pick on the page:", str(e)[:120])
    log(f"decided: {how} -> {len(chosen)} news to write and post")
    rnd["decided"] = {"how": how, "ids": chosen, "at": now().isoformat()}
    rnd["written"] = sorted(set(rnd.get("written", [])) | set(chosen))
    for i in chosen:
        if i in pool:
            pool[i]["written"] = True      # never offered again as an earlier (left-over) news
    save_state(st)
    return write_urls([pool[i]["url"] for i in chosen if i in pool])


def cmd_late():
    """news the owner ticked after the decision (late submit or a second submit) and not written yet"""
    st = load_state()
    rid, rnd = current_round(st)
    if not rid:
        return write_urls([])
    pool = st.get("pool", {})
    try:
        s = bridge_get("pickStatus", round=rid)
    except Exception as e:
        log("status check failed:", str(e)[:120])
        return write_urls([])
    extra = [i for i in (s.get("ids") or []) if i in pool and i not in rnd.get("written", [])] if s.get("submitted") else []
    if extra:
        log(f"owner ticked {len(extra)} more news after the decision - written now")
        rnd["written"] = sorted(set(rnd.get("written", [])) | set(extra))
        for i in extra:
            pool[i]["written"] = True
        save_state(st)
    return write_urls([pool[i]["url"] for i in extra])


def mark_posted(rows):
    """pool items whose link is now in the Sheet are 'posted' (never listed again)"""
    st = load_state()
    srcs = {str(r.get("source") or "").split("?")[0].rstrip("/") for r in rows}
    n = 0
    for it in st.get("pool", {}).values():
        if it["url"] in srcs and not it.get("posted"):
            it["posted"] = True
            n += 1
    save_state(st)
    return n


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "collect":
        cmd_collect()
    elif cmd == "decide":
        cmd_decide()
    elif cmd == "late":
        cmd_late()
    elif cmd == "mark":
        log(f"{mark_posted(recent_rows())} listed news now posted")
    else:
        sys.exit(__doc__)
