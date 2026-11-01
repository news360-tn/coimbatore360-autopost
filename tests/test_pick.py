"""owner 1 Nov (Coimbatore): collection only at 6 AM / 4 PM from Dinamalar + Dinamani, by published-time windows; the owner ticks the
news in an e-mail page, else the top 12; posted news never listed again; listed-not-posted news returns while < 24 h old."""
import datetime, json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_free"))
import pick      # noqa: E402

IST = pick.IST


def art(url, title, pub, score=5, pc=False):
    return {"id": pick.pid(url), "url": url, "title": title, "summary": "s", "source": "தினமலர்", "published": pub.isoformat(),
            "category": "பொது", "score": score, "power_cut": pc}


class PickFlow(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.old = (pick.STATE, pick.URLS, pick.DRY)
        pick.STATE = Path(self.d.name) / "pick_state.json"
        pick.URLS = Path(self.d.name) / "urls.txt"
        pick.DRY = False
        self.sent = []

    def tearDown(self):
        pick.STATE, pick.URLS, pick.DRY = self.old
        self.d.cleanup()

    def run_collect(self, now, found, recent=()):
        cands = [{"url": a["url"], "via": "listing"} for a in found]
        by = {a["url"]: a for a in found}
        with mock.patch.object(pick, "now", return_value=now), \
                mock.patch.object(pick, "candidates", side_effect=lambda l, since=None: cands), \
                mock.patch.object(pick, "check_article", side_effect=lambda it, r: (dict(by[it["url"]]), "")), \
                mock.patch.object(pick, "recent_rows", return_value=list(recent)), \
                mock.patch.object(pick, "is_posted", side_effect=lambda u, t, r: any(x.get("source") == u for x in r)), \
                mock.patch.object(pick, "bridge_post", side_effect=lambda a, p: self.sent.append((a, p)) or {"ok": True}):
            return pick.cmd_collect()

    def test_windows_by_published_time_and_no_repeats(self):
        d = datetime.date(2026, 11, 1)
        m6 = datetime.datetime.combine(d, datetime.time(6, 0), IST)
        st = {"last_end": (m6 - datetime.timedelta(hours=14)).isoformat(), "pool": {}, "rounds": {}}
        pick.STATE.write_text(json.dumps(st))
        a_old = art("https://www.dinamalar.com/a", "பழைய செய்தி", m6 - datetime.timedelta(hours=20))
        a_in = art("https://www.dinamani.com/b", "இரவு செய்தி", m6 - datetime.timedelta(hours=3))
        self.run_collect(m6, [a_old, a_in])
        items = self.sent[-1][1]["items"]
        self.assertEqual([x["title"] for x in items], ["இரவு செய்தி"])      # published before the window: not listed
        # evening: the morning item (not posted) comes back as an earlier news; a new 6 AM-4 PM item is listed as new
        e4 = datetime.datetime.combine(d, datetime.time(16, 0), IST)
        a_new = art("https://www.dinamalar.com/c", "மதியச் செய்தி", e4 - datetime.timedelta(hours=2))
        self.run_collect(e4, [a_in, a_new])
        items = self.sent[-1][1]["items"]
        self.assertEqual([(x["title"], x["leftover"]) for x in items], [("மதியச் செய்தி", False), ("இரவு செய்தி", True)])
        self.assertEqual(json.loads(pick.STATE.read_text())["last_end"], e4.isoformat())
        # next morning: the item was posted meanwhile -> never listed again
        n6 = m6 + datetime.timedelta(days=1)
        self.run_collect(n6, [], recent=[{"source": a_in["url"]}, {"source": a_new["url"]}])
        self.assertEqual(len(self.sent), 2, "nothing left to list: no e-mail")

    def test_leftovers_older_than_a_day_are_dropped(self):
        t = datetime.datetime(2026, 11, 2, 16, 0, tzinfo=IST)
        old = art("https://www.dinamalar.com/x", "நேற்றைய செய்தி", t - datetime.timedelta(hours=30))
        pick.STATE.write_text(json.dumps({"last_end": (t - datetime.timedelta(hours=10)).isoformat(), "rounds": {},
                                          "pool": {old["id"]: dict(old, listed_at=(t - datetime.timedelta(hours=28)).isoformat())}}))
        self.run_collect(t, [])
        self.assertEqual(self.sent, [])
        self.assertEqual(json.loads(pick.STATE.read_text())["pool"], {})

    def test_power_cut_first_then_score(self):
        t = datetime.datetime(2026, 11, 1, 6, 0, tzinfo=IST)
        xs = [art("https://www.dinamani.com/1", "a", t, 5), art("https://www.dinamani.com/2", "b", t, 9), art("https://www.dinamani.com/3", "c", t, 3, pc=True)]
        self.assertEqual([x["title"] for x in pick.rank(xs)], ["c", "b", "a"])

    def decide(self, status, items=15):
        t = datetime.datetime(2026, 11, 1, 6, 0, tzinfo=IST)
        pool = {}
        for i in range(items):
            a = art(f"https://www.dinamani.com/{i}", f"n{i}", t, score=i)
            pool[a["id"]] = a
        rid = "2026-11-01_morning"
        pick.STATE.write_text(json.dumps({"last_end": t.isoformat(), "pool": pool, "rounds": {rid: {
            "ids": list(pool), "deadline": t.isoformat(), "written": [], "decided": None, "sent": True}}}))
        with mock.patch.object(pick, "bridge_get", return_value=status), \
                mock.patch.object(pick, "bridge_post", side_effect=lambda a, p: self.sent.append((a, p)) or {"ok": True}):
            pick.cmd_decide()
        return [l for l in pick.URLS.read_text().split("\n") if l], pool

    def test_owner_pick_is_posted_exactly(self):
        urls, pool = self.decide({"ok": True, "submitted": True, "ids": [pick.pid("https://www.dinamani.com/2"), pick.pid("https://www.dinamani.com/0")]})
        self.assertEqual(urls, ["https://www.dinamani.com/2", "https://www.dinamani.com/0"])      # low score too: the owner decides

    def test_no_reply_top_12(self):
        urls, _ = self.decide({"ok": True, "submitted": False})
        self.assertEqual(len(urls), 12)
        self.assertEqual(urls[0], "https://www.dinamani.com/14")
        self.assertEqual(self.sent[-1][0], "pickAuto")

    def test_list_not_emailed_means_top_12_at_once(self):
        t = datetime.datetime(2026, 11, 1, 6, 0, tzinfo=IST)
        a = art("https://www.dinamani.com/z", "z", t)
        far = (datetime.datetime.now(IST) + datetime.timedelta(hours=1)).isoformat()
        pick.STATE.write_text(json.dumps({"last_end": t.isoformat(), "pool": {a["id"]: a}, "rounds": {"r": {
            "ids": [a["id"]], "deadline": far, "written": [], "decided": None, "sent": False}}}))
        with mock.patch.object(pick, "bridge_get", side_effect=AssertionError("must not wait")), \
                mock.patch.object(pick, "bridge_post", return_value={"ok": True}):
            pick.cmd_decide()
        self.assertEqual(pick.URLS.read_text(), a["url"])

    def test_fewer_than_12_all_posted(self):
        urls, _ = self.decide({"ok": True, "submitted": False}, items=5)
        self.assertEqual(len(urls), 5)

    def test_late_ticks_are_added_once(self):
        self.decide({"ok": True, "submitted": False})
        st = json.loads(pick.STATE.read_text())
        rid = next(iter(st["rounds"]))
        not_written = [i for i in st["rounds"][rid]["ids"] if i not in st["rounds"][rid]["written"]]
        with mock.patch.object(pick, "bridge_get", return_value={"ok": True, "submitted": True, "ids": not_written[:2] + st["rounds"][rid]["written"][:1]}):
            pick.cmd_late()
            self.assertEqual(len([l for l in pick.URLS.read_text().split("\n") if l]), 2)
            pick.cmd_late()
            self.assertEqual(pick.URLS.read_text(), "")      # never written twice


class Wiring(unittest.TestCase):
    def test_writer_writes_only_the_picked_links(self):
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        self.assertIn("if PICK_ONLY:", src)
        wf = (ROOT / ".github" / "workflows" / "pick.yml").read_text(encoding="utf-8")
        for s in ('PICK_ONLY: "1"', 'PICK_AUTO_TOP: "12"', 'PICK_WAIT_MIN: "60"', 'MANUAL_URL="$urls"'):
            self.assertIn(s, wf)

    def test_bridge_has_the_check_box_page(self):
        gs = (ROOT / "apps_script" / "Code.gs").read_text(encoding="utf-8")
        for s in ("function pickList_", "function makePickForm_", "FormApp.openById", "pickStatus_", "function authorizeForms"):
            self.assertIn(s, gs)

class OwnerPickIsPosted(unittest.TestCase):
    """1 Nov: 7 news the owner ticked at 9 AM (published 31 Oct evening) were held by the poster as 'stale: not today'"""
    def test_picked_story_has_no_skip(self):
        sys.path.insert(0, str(ROOT / "poster"))
        import post
        url = "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/x/1"
        post._PICKED = {pick.pid(url)}
        try:
            row = {"story_id": "RN-1", "source": url, "published": "2020-01-01T10:00:00+05:30", "headline_ta": "செய்தி", "reel_script": "",
                   "caption": ""}
            self.assertTrue(post.owner_picked(row))
            self.assertTrue(post.owner_picked(dict(row, source=url.replace("www.", "l-www."))))
            self.assertFalse(post.owner_picked(dict(row, source="https://www.dinamani.com/other")))
        finally:
            post._PICKED = None


if __name__ == "__main__":
    unittest.main()
