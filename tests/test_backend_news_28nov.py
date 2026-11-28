"""owner 28 Nov: ADD NEWS from the News360 Backend - a news typed there (content, extra details, follow-up of an earlier post, link,
picture, note with extra instructions, format reel / post / carousel) is taken by the page's own job, written by the usual writer
and posted through every usual check. The same test file is in all 7 page repositories."""
import base64
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))
sys.path.insert(0, str(ROOT / "research_free"))
import backend_news as bn      # noqa: E402
import factgate      # noqa: E402
import freshness      # noqa: E402
import post      # noqa: E402

PAGE = bn.pages()[0]
REQ = {"id": "BN-261128-221500-123", "by": "siva", "page": PAGE, "kind": "new", "format": "reel",
       "text": "பெருந்துறையில் நாளை காலை 9 மணி முதல் மதியம் 2 மணி வரை மின்தடை என மின்வாரியம் அறிவித்துள்ளது.\nபராமரிப்புப் பணி காரணமாக இந்த மின்தடை.",
       "details": "", "link": "", "old": "", "note": "", "image": None}


class FakeCollect:
    """the parts of research_free/collect.py the backend news uses"""
    def __init__(self):
        self.sent, self.posting, self.uploaded, self.dup_recent = [], 0, [], None

    def open_article(self, n):
        if "broken" in n["url"]:
            raise RuntimeError("404")
        return {"url": n["url"], "title": "இணைப்பின் தலைப்பு", "text": "இணைப்பில் உள்ள கட்டுரையின் முழு உரை இங்கே உள்ளது.", "published": "2026-11-28"}

    def tamil_source(self, art):
        return len(re.findall(r"[஀-௿]", art["text"])) >= 40

    def file_story(self, art, res, log, recent, scenes=None):
        d, model, errors, att = res
        self.dup_recent = recent
        return {"tamil_headline": d["tamil_headline"], "post_to": d["post_to"], "source": art["url"], "published": art["published"],
                "prompts": "scene one\n---\nscene two", "verification": "DRAFT - fact-check: no problems found" if not errors else "DRAFT - NOT CLEAN, held from posting - problems: " + "; ".join(errors)}, ""

    def _upload_image(self, data):
        self.uploaded.append(data)
        return "https://media.example/owner.jpg"

    def send_batch(self, group, log=None, images=True):
        self.sent.append((group, images))
        return True

    def bridge(self, action, **kw):
        return {"ok": True, "rows": [{"story_id": "RN-900", "headline_ta": "தலைப்பு"}]}

    def trigger_posting(self, log=None):
        self.posting += 1


class FakeWriter:
    def __init__(self, errors=()):
        self.EXTRA, self.seen, self.errors = [""], [], list(errors)

    def write(self, art, today):
        self.seen.append((art, self.EXTRA[0]))
        return {"tamil_headline": "தலைப்பு"}, "gemini", list(self.errors), 1


def jpeg(w, h):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), (10, 120, 200)).save(b, "JPEG")
    return b.getvalue()


class TheArticleTheWriterGets(unittest.TestCase):
    def test_owner_words_first_then_details_then_the_linked_article(self):
        art = bn.article(dict(REQ, details="கூடுதல் தகவல்", link="https://news.example/a"), FakeCollect())
        self.assertTrue(art["text"].startswith("பெருந்துறையில் நாளை"))
        self.assertLess(art["text"].index("கூடுதல் விவரங்கள்:"), art["text"].index("செய்தி இணைப்பில் உள்ள கட்டுரை:"))
        self.assertEqual(art["title"], "பெருந்துறையில் நாளை காலை 9 மணி முதல் மதியம் 2 மணி வரை மின்தடை என மின்வாரியம் அறிவித்துள்ளது.")
        self.assertEqual(art["url"], "https://news.example/a")
        self.assertTrue(art["manual"])      # typed by the owner: never refused for its age
        self.assertTrue(art["published"].startswith("20"))

    def test_only_a_link(self):
        art = bn.article(dict(REQ, text="", link="https://news.example/a"), FakeCollect())
        self.assertEqual(art["text"], "இணைப்பில் உள்ள கட்டுரையின் முழு உரை இங்கே உள்ளது.")
        self.assertEqual(art["title"], "இணைப்பின் தலைப்பு")

    def test_a_link_that_does_not_open(self):
        with self.assertRaises(RuntimeError):      # nothing to write from: the owner is told
            bn.article(dict(REQ, text="", link="https://news.example/broken"), FakeCollect())
        art = bn.article(dict(REQ, link="https://news.example/broken"), FakeCollect())      # with typed content the news is still written
        self.assertIn("பெருந்துறையில்", art["text"])

    def test_follow_up_puts_the_earlier_post_among_the_facts(self):
        art = bn.article(dict(REQ, kind="followup", old="RN-661"), FakeCollect())
        self.assertTrue(art["text"].endswith(bn.FOLLOW_FACT))      # so the writer's own fact check accepts the mention


class TheWritersInstructions(unittest.TestCase):
    def test_note_and_follow_up(self):
        t = bn.instructions(dict(REQ, kind="followup", old="RN-661", note="do not name the worker"))
        self.assertIn("FOLLOW-UP", t)
        self.assertIn("RN-661", t)
        self.assertIn("📌 முந்தைய செய்தியின் தொடர்ச்சி:", t)
        self.assertIn("do not name the worker", t)
        self.assertIn("never allow a fact that is not in the text", t)
        plain = bn.instructions(REQ)
        self.assertNotIn("FOLLOW-UP", plain)
        self.assertNotIn("EXTRA INSTRUCTIONS", plain)

    def test_the_instructions_are_for_this_one_story_only(self):
        c, w = FakeCollect(), FakeWriter()
        bn.build(dict(REQ, note="short and clear"), c, w, [])
        self.assertIn("short and clear", w.seen[0][1])
        self.assertEqual(w.EXTRA[0], "")      # the next news of the run is written without them


class TheStoryForTheSheet(unittest.TestCase):
    def build(self, **kw):
        c, w = FakeCollect(), FakeWriter(kw.pop("errors", ()))
        story, why = bn.build(dict(REQ, **kw), c, w, [{"story_id": "RN-1"}])
        return story, why, c

    def test_notes_tell_the_posting_job_what_it_is(self):
        story, _, c = self.build()
        self.assertIn("manual", story["note"])      # poster/post.py: a manual story is never 'stale'
        self.assertIn("BN-261128-221500-123", story["note"])
        self.assertIn(bn.OWNER_TEXT_NOTE, story["note"])
        self.assertNotIn(bn.FOLLOW_NOTE, story["note"])
        self.assertNotIn(bn.FORMAT_NOTE, story["note"])      # a reel is the normal format
        self.assertEqual(c.dup_recent, [{"story_id": "RN-1"}])      # a NEW news is still checked against what was filed

    def test_follow_up_and_format(self):
        story, _, c = self.build(kind="followup", old="RN-661", format="carousel")
        self.assertIn(bn.FOLLOW_NOTE + " of RN-661", story["note"])
        self.assertIn(bn.FORMAT_NOTE + " carousel", story["note"])
        self.assertEqual(c.dup_recent, [])      # a follow-up is not a duplicate of the news it continues
        self.assertEqual(post.backend_format({"notes": "28 Nov 22:15 " + story["note"]}), "carousel")
        self.assertTrue(freshness.owner_follow_up({"notes": "28 Nov 22:15 " + story["note"]}))

    def test_a_link_only_news_is_still_fact_checked_against_its_article(self):
        story, _, _ = self.build(text="", link="https://news.example/a")
        self.assertNotIn(bn.OWNER_TEXT_NOTE, story["note"])
        self.assertEqual(story["source"], "https://news.example/a")

    def test_owner_picture_is_used_and_no_ai_picture_is_made(self):
        story, _, c = self.build(image={"type": "image/jpeg", "data": base64.b64encode(jpeg(1600, 1200)).decode()})
        self.assertEqual(story["images"], ["https://media.example/owner.jpg"])
        self.assertEqual(story["prompts"], bn.OWNER_PICTURE)      # one prompt, one picture: the Sheet queues it at once
        from PIL import Image
        self.assertEqual(Image.open(io.BytesIO(c.uploaded[0])).size, (1152, 2048))

    def test_without_a_picture_the_usual_ai_picture_is_made(self):
        story, _, _ = self.build()
        self.assertNotIn("images", story)
        self.assertIn("scene one", story["prompts"])

    def test_english_content_is_not_held_for_its_language(self):
        story, _, _ = self.build(text="Power cut in Perundurai tomorrow from 9 am to 2 pm, the electricity board said. " * 2, errors=["not grounded: only 12% of the words"])
        self.assertIn("no problems found", story["verification"])
        story, _, _ = self.build(errors=["not grounded: only 12% of the words"])      # Tamil content keeps the check
        self.assertIn("NOT CLEAN", story["verification"])

    def test_picture_is_cut_to_9_16_never_stretched(self):
        from PIL import Image
        for w, h in ((1600, 1200), (900, 2400), (1080, 1920)):
            self.assertEqual(Image.open(io.BytesIO(bn.to_reel_size(jpeg(w, h)))).size, (1152, 2048))


class TheRun(unittest.TestCase):
    def run_with(self, items, collect=None, writer=None):
        c, w, told = collect or FakeCollect(), writer or FakeWriter(), []

        def store(action, **kw):
            if action == "manual_take":
                return {"ok": True, "items": items}
            told.append((action, kw))
            return {"ok": True}
        with mock.patch.object(bn, "STORE", "https://store"), mock.patch.object(bn, "KEY", "k"), mock.patch.object(bn, "store", store), \
                mock.patch.dict(sys.modules, {"collect": c, "run": w}):
            n = bn.run()
        return n, c, told

    def test_written_saved_and_reported(self):
        n, c, told = self.run_with([dict(REQ)])
        self.assertEqual(n, 1)
        self.assertEqual(len(c.sent), 1)
        self.assertTrue(c.sent[0][1])      # no owner picture: the pictures are made the usual way
        self.assertEqual(c.posting, 1)      # the posting job is started at once
        self.assertEqual(told[0][0], "manual_done")
        self.assertEqual((told[0][1]["status"], told[0][1]["story"]), ("filed", "RN-900"))

    def test_a_held_story_says_so(self):
        _, _, told = self.run_with([dict(REQ)], writer=FakeWriter(["numbers not found in the article: 7"]))
        self.assertEqual(told[0][1]["status"], "held")
        self.assertIn("numbers not found", told[0][1]["msg"])

    def test_a_failure_is_reported_and_the_next_news_still_goes(self):
        n, c, told = self.run_with([dict(REQ, id="BN-1", text="", link="https://news.example/broken"), dict(REQ, id="BN-2")])
        self.assertEqual(n, 1)
        self.assertEqual([(t[1]["id"], t[1]["status"]) for t in told], [("BN-1", "problem"), ("BN-2", "filed")])
        self.assertIn("could not be opened", told[0][1]["msg"])

    def test_sheet_not_reachable_is_tried_again(self):
        c = FakeCollect()
        c.send_batch = lambda group, log=None, images=True: False
        n, _, told = self.run_with([dict(REQ)], collect=c)
        self.assertEqual(n, 0)
        self.assertEqual(told[0][1]["status"], "waiting")

    def test_without_the_secrets_nothing_happens(self):
        with mock.patch.object(bn, "STORE", ""), mock.patch.object(bn, "KEY", ""), mock.patch.object(bn, "store", side_effect=AssertionError("never called")):
            self.assertEqual(bn.run(), 0)
            self.assertEqual(bn.peek(), 0)
            self.assertEqual(bn.waiting(), 0)


class ThePeek(unittest.TestCase):
    def records(self, d):
        (d / "poster" / "posted").mkdir(parents=True)
        (d / "poster" / "fb_posted").mkdir(parents=True)
        (d / "poster" / "yt_uploaded").mkdir(parents=True)
        (d / "poster" / "posted" / f"20261128-170000-{PAGE}-RN-900.json").write_text(json.dumps({"link": "https://www.instagram.com/reel/abc/", "media_id": "111"}), encoding="utf-8")
        (d / "poster" / "fb_posted" / f"{PAGE}-RN-900-reel.json").write_text(json.dumps({"status": "posted", "link": "https://www.facebook.com/reel/1/"}), encoding="utf-8")
        (d / "poster" / "fb_posted" / f"{PAGE}-RN-902-photos.json").write_text(json.dumps({"status": "posted", "link": "https://www.facebook.com/2"}), encoding="utf-8")
        (d / "poster" / "posted" / f"20261128-171000-{PAGE}-RN-902.json").write_text(json.dumps({"link": "https://www.instagram.com/p/car/", "media_id": "333"}), encoding="utf-8")
        (d / "poster" / "yt_uploaded" / f"{PAGE}.json").write_text(json.dumps({"uploads": [{"ig": "111", "youtube": "YT1"}]}), encoding="utf-8")
        (d / ".last_check").write_text("22:41:44 SKIP RN-901 held: location unknown\n22:41:44 SKIP RN-7 stale: published 29 Oct\n", encoding="utf-8")

    def test_story_state_from_the_repository_records(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            self.records(d)
            self.assertEqual(bn.story_state(PAGE, "RN-900", d), ("posted", {"instagram": "https://www.instagram.com/reel/abc/", "facebook": "https://www.facebook.com/reel/1/",
                                                                              "youtube": "https://youtube.com/shorts/YT1"}, ""))
            self.assertEqual(bn.story_state(PAGE, "RN-902", d)[1], {"instagram": "https://www.instagram.com/p/car/", "facebook": "https://www.facebook.com/2"})      # a carousel: no YouTube
            self.assertEqual(bn.story_state(PAGE, "RN-901", d), ("held", {}, "held: location unknown"))
            self.assertEqual(bn.story_state(PAGE, "RN-999", d), ("", {}, ""))

    def test_peek_reports_changes_once_and_starts_the_writer(self):
        told, started = [], []
        open_ = [{"id": "BN-1", "page": PAGE, "story": "RN-900", "status": "filed", "links": {}},
                 {"id": "BN-2", "page": PAGE, "story": "RN-901", "status": "filed", "links": {}},
                 {"id": "BN-3", "page": PAGE, "story": "RN-901", "status": "held", "links": {}},      # already told: not told again
                 {"id": "BN-4", "page": PAGE, "story": "RN-999", "status": "filed", "links": {}}]

        def store(action, **kw):
            if action == "manual_take":
                self.assertTrue(kw.get("peek"))
                return {"ok": True, "waiting": 2, "open": open_}
            told.append((kw["id"], kw["status"], kw.get("links"), kw.get("msg")))
            return {"ok": True}
        with tempfile.TemporaryDirectory() as t:
            self.records(Path(t))
            with mock.patch.object(bn, "STORE", "https://store"), mock.patch.object(bn, "KEY", "k"), mock.patch.object(bn, "store", store), \
                    mock.patch.object(bn, "ROOT", Path(t)), mock.patch.object(bn, "start_workflow", lambda: started.append(1) or True):
                self.assertEqual(bn.peek(), 2)
        self.assertEqual([x[:2] for x in told], [("BN-1", "posted"), ("BN-2", "held")])
        self.assertEqual(told[0][2]["youtube"], "https://youtube.com/shorts/YT1")
        self.assertEqual(told[1][3], "held: location unknown")
        self.assertEqual(started, [1])

    def test_the_key_goes_in_the_body_never_in_the_link(self):
        seen = {}

        class R:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{"ok": true, "waiting": 0, "open": []}'

        def urlopen(req, timeout=0):
            seen["url"], seen["body"] = req.full_url, json.loads(req.data.decode("utf-8"))
            return R()
        with mock.patch.object(bn, "STORE", "https://script.example/exec"), mock.patch.object(bn, "KEY", "secret-key"), mock.patch.object(bn.urllib.request, "urlopen", urlopen):
            bn.peek()
        self.assertEqual(seen["url"], "https://script.example/exec")
        self.assertEqual(seen["body"]["key"], "secret-key")
        self.assertEqual(seen["body"]["pages"], [PAGE])


class ThePostingJobHooks(unittest.TestCase):
    def test_follow_up_is_never_a_duplicate_of_the_news_it_continues(self):
        old = {"headline_ta": "பேரூர் கோயில் உண்டியல் தங்கம் திருட்டு புகார்", "researched": "2026-11-28 10:00"}
        new = {"headline_ta": "பேரூர் கோயில் உண்டியல் தங்கம் புகார்: விசாரணை முடிவு", "researched": "2026-11-28 20:00"}
        self.assertFalse(freshness.follow_up(old, new))
        self.assertTrue(freshness.follow_up(old, dict(new, notes="28 Nov manual BACKEND news BN-1 by siva; backend follow-up of RN-661")))
        self.assertFalse(freshness.owner_follow_up({"notes": "free-model draft"}))
        with mock.patch.object(post, "ig_recent", side_effect=AssertionError("the Instagram feed is not even read")):
            self.assertEqual(post.ig_duplicate(dict(new, notes="backend follow-up of RN-661"), PAGE), "")

    def test_owner_text_is_not_checked_against_a_link(self):
        row = {"source": "https://news.example/a", "notes": "manual BACKEND news BN-1 by siva; backend owner text", "headline_ta": "x"}
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "x"}), mock.patch.dict(sys.modules, {"allnews": mock.Mock(article_any=mock.Mock(side_effect=AssertionError("not read")))}):
            self.assertEqual(factgate.check(row), [])

    def test_format_decides_what_is_made(self):
        reel, poster, car = {"notes": "manual BACKEND news"}, {"notes": "x; backend format post"}, {"notes": "x; Backend Format Carousel | gemini"}
        self.assertEqual([post.backend_format(r) for r in (reel, poster, car, {}, None)], ["", "post", "carousel", "", ""])
        self.assertTrue(post.spec_has_carousel(poster))
        self.assertTrue(post.spec_has_carousel(car))
        label = post.LABEL[PAGE]
        self.assertFalse(post.page_done(dict(car), PAGE))      # nothing posted yet
        self.assertTrue(post.page_done(dict(car, **{PAGE + "_link": "https://www.instagram.com/p/x/"}), PAGE))      # the picture post is out: done, no reel is waited for
        self.assertFalse(post.page_done({"notes": "", "slides_spec": '{"carousel": false}', "reel_link": "", PAGE + "_link": ""}, PAGE))      # a normal story still waits for its reel
        self.assertTrue(post.page_done({"notes": "", "slides_spec": '{"carousel": false}', "reel_link": label + ": https://x", PAGE + "_link": ""}, PAGE))

    def test_one_picture_is_a_normal_post_not_a_carousel(self):
        calls = []

        def ig(method, path, token, **kw):
            calls.append((method, path, kw))
            return {"id": "M1", "permalink": "https://www.instagram.com/p/one/"}
        with mock.patch.object(post, "ig", ig), mock.patch.object(post, "ig_account", lambda t: ("UID", "name")), mock.patch.object(post, "wait_ready", lambda *a, **k: None), \
                mock.patch.object(post, "create_with_collab", lambda uid, token, params, collab: (calls.append(("create", params)) or "C1", False, "")):
            mid, link, _, _ = post.publish_carousel("tok", ["https://media.example/slide1.jpg"], "caption", "")
        self.assertEqual((mid, link), ("M1", "https://www.instagram.com/p/one/"))
        create = next(c for c in calls if c[0] == "create")[1]
        self.assertEqual(create, {"image_url": "https://media.example/slide1.jpg", "caption": "caption"})      # no CAROUSEL, no is_carousel_item
        self.assertFalse([c for c in calls if c[0] == "POST" and c[2].get("is_carousel_item")])


class TheWorkflows(unittest.TestCase):
    def test_backend_news_workflow(self):
        y = (ROOT / ".github" / "workflows" / "backend_news.yml").read_text(encoding="utf-8")
        for k in ("DASH_URL: ${{ secrets.DASH_URL }}", "DASH_WRITE_KEY: ${{ secrets.DASH_WRITE_KEY }}", "BRIDGE_URL: ${{ secrets.BRIDGE_URL }}", "GEMINI_API_KEY:",
                  "workflow_dispatch:", "python3 research_free/backend_news.py waiting", "python -u research_free/backend_news.py run", 'AUTO_IMAGES: "1"'):
            self.assertIn(k, y)
        self.assertNotIn("PICK_", y)
        self.assertEqual(y.count("if: steps.q.outputs.n != '0'"), 3)      # nothing is installed when nothing waits

    def test_posting_job_only_peeks_and_can_never_be_stopped_by_it(self):
        y = (ROOT / ".github" / "workflows" / "post.yml").read_text(encoding="utf-8").replace("\r\n", "\n")
        i = y.index("backend_news.py peek")
        step = y[y.rindex("      - name:", 0, i):i + 60]
        self.assertIn("continue-on-error: true", step)
        self.assertIn("timeout-minutes: 2", step)
        self.assertIn("|| true", step)
        self.assertLess(y.index("  check:"), i)
        self.assertEqual(y.count("backend_news.py"), 1)      # the writing itself is never done inside the posting job

    def test_peek_needs_only_the_standard_library(self):
        src = (ROOT / "research_free" / "backend_news.py").read_text(encoding="utf-8")
        top = src[:src.index("def log(")]
        self.assertNotIn("import requests", top)
        self.assertNotIn("import collect", top)
        self.assertNotIn("PIL", top)


if __name__ == "__main__":
    unittest.main()
