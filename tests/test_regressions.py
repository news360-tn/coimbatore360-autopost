"""Regression tests built from real cases the pipeline got wrong (26-27 Oct 2026). Run before every push:

    python3 -m unittest discover -s tests -v

Each test names the real story that broke, so a failure says which old problem has come back."""
import ast, datetime, json, os, re, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for d in ("poster", "research_free", "reel"):
    sys.path.insert(0, str(ROOT / d))

import freshness as fr          # noqa: E402
import allnews                  # noqa: E402
import collect                  # noqa: E402
import post                     # noqa: E402

IST = fr.IST
TODAY = datetime.datetime.now(IST).date()


def from_file(path, names, extra=None):
    """load only some top-level functions/assignments of a file (reel4.py needs a browser library to import as a whole)"""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in names)]
    ns = {"os": os, "sys": sys, "json": json, "re": re, "Path": Path, "__file__": str(path), "html": __import__("html")}
    ns.update(extra or {})
    exec(compile(ast.Module(body, []), str(path), "exec"), ns)
    return ns


class DuplicateCheck(unittest.TestCase):
    def test_prisoner_is_not_the_rss_march(self):      # 27 Oct: the escaped-prisoner news was skipped as a 'duplicate'
        self.assertFalse(fr.similar("கோவையில் நீதிமன்ற உத்தரவுப்படி ஆர்எஸ்எஸ் அணிவகுப்பு ஊர்வலம்",
                                    "கோவை நீதிமன்றத்திலிருந்து  தப்பியோடிய கைதி பிடிப்பு", 0.55))

    def test_bus_death_is_not_roof_fall(self):
        self.assertFalse(fr.similar("வேலகவுண்டம்பட்டி அருகே தனியார் பேருந்து மோதி தொழிலாளி உயிரிழப்பு",
                                    "வீட்டின் கூரை மேலிருந்து விழுந்த தொழிலாளி உயிரிழப்பு", 0.55))

    def test_same_news_other_words_still_duplicate(self):
        self.assertTrue(fr.similar("100 ஆண்டுகளான புளியமரம் சாலையின் குறுக்கே சாய்ந்தது",
                                   "சூலூர் அருகே 100 ஆண்டு புளியமரம் சாலையில் சாய்ந்தது", 0.55))
        self.assertTrue(fr.similar("கோவையில் நீதிமன்ற உத்தரவுப்படி ஆர்எஸ்எஸ் அணிவகுப்பு ஊர்வலம்",
                                   "கோவையில் ஆா்எஸ்எஸ் அணிவகுப்பு ஊா்வலம்", 0.55))      # old print form ா் = ர்

    def test_different_numbers_are_different_events(self):      # 26 Oct: RN-111 vs RN-62
        self.assertTrue(fr.different_numbers("சூதாடிய 8 பேர் கைது", "சூதாடிய 6 பேர் கைது"))

    def test_power_cut_other_place_not_duplicate(self):      # 27 Oct: RN-131 skipped as a 'duplicate' of an older power cut
        a = "காளப்பநாயக்கன்பட்டி துணை மின் நிலையப் பராமரிப்பு: நாளை காலை 9 முதல் மதியம் 2 வரை மின் தடை"
        b = "பூளவாடி துணை மின் நிலையப் பராமரிப்பு: நாளை காலை 9 முதல் மதியம் 2 வரை மின் தடை"
        self.assertFalse(fr.similar(b, a, 0.62, f"{TODAY:%d %b %Y}, 02:00"))
        self.assertTrue(fr.similar(a, a, 0.62, f"{TODAY:%d %b %Y}, 02:00"))
        old = TODAY - datetime.timedelta(days=15)
        self.assertFalse(fr.similar(a, a, 0.62, f"{old:%d %b %Y}, 10:00"))      # same substation, an older notice

    def test_writer_same_news(self):
        self.assertTrue(collect.same_news("மழையால் கோவை கலெக்டர் குடியிருப்பின் சுற்றுச்சுவர் இடிந்தது",
                                          "கனமழை: கோவை ஆட்சியர் பங்களா சுவர் இடிந்து விழுந்தது"))

    def test_writer_other_news_not_duplicate(self):      # 28 Oct: three new stories were skipped as 'similar to a filed story'
        now = f"{TODAY:%d %b %Y}, 06:00"
        old = f"{TODAY - datetime.timedelta(days=6):%d %b %Y}, 06:00"
        self.assertFalse(collect.same_news("கோவையில் தென்னை விவசாயிகள் பிரச்னை: அக். 30-ல் முத்தரப்புக் கூட்டம்",
                                           "30ல் விவசாயிகள் குறைதீர் கூட்டம்", now))      # RN-140: two shared words only
        self.assertFalse(collect.same_news("🗑️ குப்பையுடன் தேங்கிய மழைநீர் – சுகாதார சீர்கேடு",
                                           "சர்வீஸ் சாலையில் குவிக்கும் குப்பையால் சுகாதார சீர்கேடு", old))      # RN-69: days older
        self.assertTrue(collect.same_news("கலெக்டர் அலுவலகத்தில் முதியவர் தீக்குளிக்க முயற்சி: நிலத் தகராறு",
                                          "முதியவர் தீக்குளிக்க முயற்சி கலெக்டர் ஆபீசில் பரபரப்பு", now))      # RN-146: real repeat


class LearnedPriority(unittest.TestCase):
    """28 Oct: power cuts and jobs (our most watched news) were scored -0.5 as 'civic' / 'education_jobs'"""

    def test_power_cut_and_jobs_have_own_topic(self):
        import learned
        self.assertEqual("power_cut", learned.topic("நாளை காளப்பநாயக்கன்பட்டி உள்ளிட்ட 9 பகுதிகளில் மின் தடை: சாலை பணி"))
        self.assertEqual("jobs", learned.topic("கோவையில் 23ஆம் தேதி தனியார் வேலைவாய்ப்பு முகாம்"))
        self.assertEqual("education", learned.topic("TNPSC குரூப் 4 தேர்வுக்கு இலவசப் பயிற்சி"))      # 'தேர்' (chariot) is not temple
        real = learned.load
        learned.load = lambda: {"topic_weight": {"civic": -0.5, "education": -0.5}}      # not measured yet: the starting weight is used
        try:
            self.assertGreater(learned.boost("நாளை 9 பகுதிகளில் மின் தடை"), 0)
        finally:
            learned.load = real


class CoimbatorePriority(unittest.TestCase):
    """owner 29 Oct (Coimbatore): power cut > crime > accident > civic > the rest; news published TODAY only"""

    def test_order(self):
        score = lambda t: collect.interest({"title": t, "text": ""})
        cut, crime, acc, civic = (score("சிங்காநல்லூரில் நாளை மின் தடை"), score("காந்திபுரத்தில் நகை திருடியவர் கைது"),
                                  score("உக்கடத்தில் பஸ் மோதி விபத்து"), score("வடவள்ளியில் குடிநீர் தட்டுப்பாடு"))
        rest = (score("கோவையில் தனியார் வேலைவாய்ப்பு முகாம்"), score("கோவையில் கனமழை"), score("கோவை கோயில் திருவிழா"))
        self.assertTrue(cut > crime > acc > civic > max(rest), (cut, crime, acc, civic, rest))

    def test_today_only(self):
        self.assertEqual(1, collect.FRESH_DAYS)
        self.assertTrue(collect.fresh(datetime.datetime.now(IST).isoformat()))
        self.assertFalse(collect.fresh((datetime.datetime.now(IST) - datetime.timedelta(days=1)).isoformat()))
        self.assertTrue(collect.fresh((datetime.datetime.now(IST) - datetime.timedelta(hours=2)).isoformat()))      # 11:30 pm news at the 1 am round

    def test_every_two_hours_cap_50(self):      # owner 29 Oct: collect every 2 h, post at once, do not miss city news
        wf = ROOT / ".github" / "workflows"
        self.assertIn('cron: "7 */2 * * *"', (wf / "research_free.yml").read_text())
        self.assertIn('age("collect") > 135', (wf / "post.yml").read_text())
        for f in ("post.yml", "research_free.yml", "write_stories.yml"):
            self.assertIn('DAILY_CAP: "50"', (wf / f).read_text(), f)
        for wf in ("research_free.yml", "write_stories.yml"):
            self.assertIn('FRESH_DAYS: "1"', (ROOT / ".github" / "workflows" / wf).read_text())


class PowerCutTiming(unittest.TestCase):
    A = "காளப்பநாயக்கன்பட்டி துணை மின் நிலையப் பராமரிப்பு: நாளை காலை 9 முதல் மதியம் 2 வரை மின் தடை"

    def at(self, h, m=0):
        return datetime.datetime.combine(TODAY, datetime.time(h, m), IST)

    def test_late_notice_not_posted(self):      # 27 Oct: RN-131 (cut until 2 pm) went out at 13:42
        y = TODAY - datetime.timedelta(days=1)
        self.assertIn("too late", fr.power_cut_over(self.A, "", f"{y} 18:33", self.at(13, 35)))
        self.assertEqual("", fr.power_cut_over(self.A, "", f"{y} 18:33", self.at(10, 0)))

    def test_tomorrow_cut_posted_today(self):
        self.assertEqual("", fr.power_cut_over(self.A, "", f"{TODAY} 18:33", self.at(21, 0)))

    def test_english_and_evening_end(self):
        y = TODAY - datetime.timedelta(days=1)
        self.assertIn("14:00", fr.power_cut_over("Power cut in Pollachi tomorrow", "Power cut from 9 am to 2 pm", f"{y}", self.at(13, 45)))
        self.assertIn("17:00", fr.power_cut_over("கோவையில் இன்று காலை 9 முதல் மாலை 5 வரை மின்தடை", "", f"{TODAY}", self.at(16, 45)))


class NewsDate(unittest.TestCase):
    def test_date_from_link(self):      # 27 Oct: the Sheet had no publish date for RN-131
        self.assertEqual(datetime.date(2026, 10, 26), fr.news_date("", "https://www.dinamani.com/all-editions/edition-coimbatore/coimbatore/2026/Oct/26/x"))
        self.assertEqual(datetime.date(2026, 10, 23), fr.news_date("", "https://www.dinakaran.com/district/kovai-231026-3/"))
        self.assertEqual(datetime.date(2026, 10, 25), fr.news_date("2026-10-25T09:00:00Z", ""))


class PostingGate(unittest.TestCase):
    def setUp(self):
        post.ALL_ROWS = []

    def row(self, **k):
        r = {"story_id": "RN-T1", "headline_ta": "சிங்காநல்லூரில் தடை செய்யப்பட்ட புகையிலை விற்ற 2 பேர் கைது", "headline_en": "Two held for selling banned tobacco in Singanallur",
             "category": "குற்றம்", "location": "சிங்காநல்லூர், கோவை", "caption": "சிங்காநல்லூரில் புகையிலை விற்ற இருவர் கைது",
             "published": f"{TODAY}", "source": "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/x/1",
             "researched": f"{TODAY:%d %b %Y}, 06:25", "post_status": "", "notes": "", "batch": "", "review": "Auto"}
        r.update(k)
        return r

    def test_today_news_posts(self):
        self.assertEqual("", post.skip_reason(self.row()))

    def test_two_day_old_news_not_posted(self):      # 27 Oct: RN-103 (25 Oct RSS march) went out two days late
        old = TODAY - datetime.timedelta(days=2)
        self.assertIn("older than yesterday", post.skip_reason(self.row(published=f"{old}", researched=f"{old:%d %b %Y}, 01:50")))

    def test_old_news_by_link_date(self):
        old = TODAY - datetime.timedelta(days=3)
        self.assertIn("older than yesterday", post.skip_reason(self.row(
            published="", source=f"https://www.dinamani.com/all-editions/edition-coimbatore/coimbatore/{old:%Y/%b/%d}/x")))

    def test_other_district_not_posted(self):      # Tiruppur is next door but not ours
        self.assertTrue(post.skip_reason(self.row(headline_ta="பல்லடத்தில் பேருந்து விபத்து: 5 பேர் காயம்", location="பல்லடம், திருப்பூர்",
                                                  caption="பல்லடம் அருகே விபத்து")))


class DistrictFilter(unittest.TestCase):
    def test_link_district(self):
        self.assertEqual("coimbatore", allnews.url_district("https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/central-media-crowds/4360211"))
        self.assertEqual("coimbatore", allnews.url_district("https://www.dinamani.com/all-editions/edition-coimbatore/coimbatore/2026/Oct/26/x"))
        self.assertEqual("virudhunagar", allnews.url_district("https://www.dinamani.com/all-editions/edition-madurai/virudhunagar/2026/Oct/26/x"))

    def test_places(self):
        for t in ("பொள்ளாச்சியில்", "சூலூரில் தீ", "Valparai rain", "மேட்டுப்பாளையத்தில்", "ஆர்.எஸ்.புரத்தில்"):
            self.assertTrue(allnews.has_place(t), t)
        for t in ("திருப்பூரில் கனமழை", "ஊட்டியில் மண் சரிவு", "அவிநாசியில் விபத்து", "நாமக்கல்லில் கனமழை", "Erode rain"):
            self.assertTrue(allnews.other_district(t), t)
        self.assertFalse(allnews.other_district("கோவை அவிநாசி சாலையில் விபத்து"))      # a road inside Coimbatore city


class Recheck(unittest.TestCase):
    URL = "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/central-media-crowds/4360211"

    def test_rejected_district_page_story_checked_again_once(self):      # 27 Oct: centre-median / Star 3.0 stayed 'checked earlier'
        st = {"s": "notdistrict", "n": 0}
        self.assertTrue(collect.recheck_once(st, self.URL))
        self.assertNotIn("s", st)      # the writer must not see the old verdict
        st["s"] = "notdistrict"
        self.assertFalse(collect.recheck_once(st, self.URL))      # only once

    def test_old_duplicate_checked_again(self):      # the escaped-prisoner news
        st = {"s": "dup", "n": 0}
        self.assertTrue(collect.recheck_once(st, "https://news.google.com/x"))

    def test_other_district_not_rechecked(self):
        self.assertFalse(collect.recheck_once({"s": "notdistrict"}, "https://www.dinamani.com/all-editions/edition-madurai/virudhunagar/2026/Oct/26/x"))


class DinamalarList(unittest.TestCase):
    def test_reads_whole_list(self):      # 27 Oct: only the first 8 stories were read; the 140 mm rain report was missed
        import sources
        page = ('<a href="/news/tamil-nadu-district-news-coimbatore/2-held-for-selling-tobacco/4360215">x</a>'
                '{"url":"/news/tamil-nadu-district-news-coimbatore/4360205/140--rain-recorded-in-district-people-rejoice"}')
        old = sources._get
        sources._get = lambda u: page
        try:
            links = sources.candidate_links(60)
        finally:
            sources._get = old
        self.assertEqual(2, len(links))
        self.assertTrue(any(l.endswith("/140--rain-recorded-in-district-people-rejoice/4360205") for l in links))


class Reel(unittest.TestCase):
    def test_no_b_tags_on_screen(self):      # 27 Oct: '<b>90,703</b>' showed in a reel
        E = from_file(ROOT / "reel" / "reel4.py", {"E"})["E"]
        self.assertEqual("90,703", E("<b>90,703</b>"))
        self.assertEqual("5 &lt; 7", E("5 < 7"))

    def test_valluvar_only(self):      # owner 28 Oct: Coimbatore uses only the free Valluvar voice, never Google Charon
        ns = from_file(ROOT / "reel" / "reel4.py", {"voice_setting", "pick_voice"})
        os.environ["GOOGLE_TTS_API_KEY"] = "test"
        try:
            vs, alt = ns["pick_voice"]({"story": "RN-1", "sentences": [{"say": "அ" * 1300}]})
        finally:
            os.environ.pop("GOOGLE_TTS_API_KEY", None)
        self.assertEqual("edge", vs.get("engine"))
        self.assertEqual("ta-IN-ValluvarNeural", vs.get("voice"))
        code = (ROOT / "reel" / "reel4.py").read_text(encoding="utf-8")
        self.assertNotIn("texttospeech.googleapis", code)
        self.assertNotIn("Chirp3-HD", code)
        cfg = json.loads((ROOT / "poster" / "config.json").read_text())
        self.assertNotIn("reel_voice_alt", cfg)
        for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
            self.assertNotIn("GOOGLE_TTS_API_KEY", wf.read_text(), wf.name)


class Images(unittest.TestCase):
    def order(self, fail):
        """which sources generate() tries, when the sources in `fail` do not answer"""
        import imagegen
        calls = []
        def src(name):
            def f(*a, **k):
                calls.append(name)
                if name in fail:
                    raise RuntimeError(name + " 429: down")
                return b"img"
            return f
        saved = {k: getattr(imagegen, k) for k in ("_cf", "_gemini_image", "generate_nvidia", "_fal", "to_story_size")}
        env = {k: os.environ.get(k) for k in ("FAL_KEY", "NVIDIA_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "GEMINI_API_KEY")}
        imagegen._cf, imagegen._gemini_image, imagegen.generate_nvidia, imagegen.to_story_size = src("cloudflare"), src("gemini"), src("nvidia"), (lambda b: b)
        imagegen._fal = lambda p, s, k, model=None: src(model)()
        os.environ.update({k: "test" for k in env})
        imagegen.DEAD.clear()
        try:
            imagegen.generate("p", 1)
        except Exception:
            pass
        finally:
            for k, v in saved.items():
                setattr(imagegen, k, v)
            for k, v in env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
            imagegen.DEAD.clear()
        return calls

    def test_free_first(self):      # owner 28 Oct: free sources first, paid FAL only when they fail
        self.assertEqual(["cloudflare"], self.order(set()))
        self.assertEqual("nvidia", self.order({"cloudflare"})[-1])
        calls = self.order({"cloudflare", "nvidia"})
        self.assertEqual(["cloudflare", "nvidia"], calls[:2], "every free source first")
        self.assertEqual("fal-ai/flux/schnell", calls[2], "FAL only when no free source worked, cheapest first (owner 29 Oct)")

    def test_no_picture_means_plain_branded_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = post.plain_background(Path(tmp), 1)
            self.assertEqual(1, len(files))
            self.assertTrue(files[0].exists())
        self.assertLessEqual(float(os.environ.get("AUTO_IMG_GIVEUP_H", "0.5")), 0.5)

    def test_prompt_asks_for_no_text(self):      # 29 Oct test picture had 'POLICE' written on the jeep
        import imagegen
        seen = []
        old = (imagegen._cf, imagegen.to_story_size, os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID"))
        imagegen._cf, imagegen.to_story_size = (lambda m, body, t, a: seen.append(body["prompt"]) or b"img"), (lambda b: b)
        os.environ["CLOUDFLARE_API_TOKEN"] = os.environ["CLOUDFLARE_ACCOUNT_ID"] = "test"
        imagegen.DEAD.clear()
        try:
            imagegen.generate("A police jeep on a Coimbatore road at dawn", 1)
        finally:
            imagegen._cf, imagegen.to_story_size = old[0], old[1]
            for k, v in (("CLOUDFLARE_API_TOKEN", old[2]), ("CLOUDFLARE_ACCOUNT_ID", old[3])):
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.assertIn("No text", seen[0])

    def test_one_image_per_story(self):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        self.assertEqual(1, len(d["scenes"]))
        d["scenes"] = [d["scenes"][0]] * 3
        self.assertTrue(validate.validate(d, ""), "three image prompts must be refused")
        self.assertNotEqual("1", os.environ.get("REUSE_IMAGES"), "older pictures are never reused")


class CityOnly(unittest.TestCase):
    """owner 29 Oct: start with Coimbatore CITY only (whole district later with CITY_ONLY=0)"""

    def test_towns_outside_the_city_skipped(self):
        for t in ("பொள்ளாச்சியில் விபத்து", "மேட்டுப்பாளையத்தில் யானை", "சூலூரில் கைது", "Pollachi farmers protest"):
            self.assertTrue(allnews.outside_city(t), t)
        self.assertTrue(allnews.outside_city("நகை பறிப்பு", "பொள்ளாச்சி, கோவை"))      # the location the writer found

    def test_power_cuts_from_the_whole_district(self):      # owner 29 Oct: never miss a power cut - whole district; other news city only
        for t in ("பொள்ளாச்சியில் நாளை மின்தடை", "மேட்டுப்பாளையம் பகுதிகளில் நாளை மின் விநியோகம் நிறுத்தம்", "Pollachi power cut tomorrow"):
            self.assertEqual("", allnews.outside_city(t), t)
        row = {"source": "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/x/1",
               "headline_ta": "பொள்ளாச்சியில் நாளை மின்தடை", "caption": "", "location": "பொள்ளாச்சி"}
        self.assertNotIn("city", post.not_coimbatore(row))
        self.assertTrue(any("பொள்ளாச்சி மின்தடை" == q for q in allnews.QUERIES))
        self.assertGreater(collect.interest({"title": "பொள்ளாச்சியில் நாளை மின்தடை", "text": ""}),
                           collect.interest({"title": "காந்திபுரத்தில் நகை திருடியவர் கைது", "text": ""}))      # power cut first

    def test_city_news_kept(self):
        for t in ("கோவையில் ஆன்லைன் மோசடி", "Coimbatore power cut", "மேட்டுப்பாளையம் சாலையில் விபத்து",
                  "காந்திபுரத்தில் பஸ் விபத்து; பொள்ளாச்சி பயணிகள்", "கோவை பேரூராட்சியில் கூட்டம்"):
            self.assertEqual("", allnews.outside_city(t), t)

    def test_posting_gate_city_only(self):
        row = {"source": "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/x/1",
               "headline_ta": "பொள்ளாச்சியில் தென்னை விவசாயிகள் போராட்டம்", "caption": "", "location": "பொள்ளாச்சி"}
        self.assertIn("city", post.not_coimbatore(row))
        row.update(headline_ta="சிங்காநல்லூரில் சாலை மறியல்", location="சிங்காநல்லூர், கோவை")
        self.assertEqual("", post.not_coimbatore(row))


class ImagePrompt(unittest.TestCase):
    """owner 29 Oct: a detailed, news-related picture - the scene of THIS news first, generic scenes sent back"""
    GOOD = ("A TNEB lineman on a tall concrete pole repairs a transformer at a substation on Trichy Road in Singanallur while two other linemen in "
            "khaki shirts hold a ladder below; the shops along the road have their shutters half down and no lights, two-wheelers pass slowly, an "
            "autorickshaw waits at the corner, a few residents watch from a distance, late morning daylight with light clouds, Western Ghats faintly "
            "in the background, eye-level 35 mm wide shot showing the street and the substation fence.")

    def test_scene_first_in_prompt(self):
        p = collect.IMG_TEMPLATE.format(scene=self.GOOD)
        self.assertTrue(p.startswith("A TNEB lineman"))
        self.assertIn("No text", p)
        self.assertLess(len(p), 1800)

    def test_generic_scene_sent_back(self):
        head = "Power shutdown in Singanallur tomorrow for substation maintenance"
        self.assertTrue(collect.scene_ok(self.GOOD, head))
        self.assertFalse(collect.scene_ok("A busy city street in daylight with buildings and people. " * 3, head))
        self.assertFalse(collect.scene_ok("A TNEB lineman repairs a transformer in Singanallur.", head))      # too short


class FreeFirstThenClaude(unittest.TestCase):
    """owner 29 Oct (Coimbatore): try ALL free models first; paid Claude only when every free one failed or is out of quota"""

    def test_every_free_model_before_claude(self):
        import llm
        tried = []
        def failing(name):
            def f(model, system, user, key):
                tried.append(name)
                raise RuntimeError(f"{name} 429: daily limit reached (per day)")
            return f
        old = (llm.chain, dict(llm.DEAD), llm.FREE_FAILS[0], os.environ.get("ANTHROPIC_API_KEY"))
        llm.chain = lambda: [(p, "m", failing(p), "k") for p in ("gemini", "ghmodels", "groq", "cloudflare")]
        llm.DEAD.clear(); llm.FREE_FAILS[0] = 0
        os.environ["ANTHROPIC_API_KEY"] = "test"
        try:
            for _ in range(2):      # also on the next call of the same round
                with self.assertRaises(RuntimeError):
                    llm.ask_json("s", "u")
        finally:
            llm.chain = old[0]; llm.DEAD.clear(); llm.DEAD.update(old[1]); llm.FREE_FAILS[0] = old[2]
            os.environ.pop("ANTHROPIC_API_KEY", None) if old[3] is None else os.environ.__setitem__("ANTHROPIC_API_KEY", old[3])
        self.assertEqual(["gemini", "ghmodels", "groq", "cloudflare"], tried[:4], "all free models first")

    def test_claude_model_and_key_passed(self):
        import llm
        self.assertIn('"claude-haiku-4-5"', (ROOT / "research_free" / "llm.py").read_text())
        self.assertTrue(llm.GHM_MODELS)
        for f in ("research_free.yml", "write_stories.yml", "post.yml"):
            t = (ROOT / ".github" / "workflows" / f).read_text()
            self.assertIn("ANTHROPIC_MODEL: claude-haiku-5-5", t, f)      # owner 29 Oct: newest Haiku
            self.assertNotIn('CLAUDE_MAX_CALLS: "0"', t, f)


class NoMetaScript(unittest.TestCase):
    """29 Oct Namakkal RN-189 (deleted by the owner): 'முட்டை விலை ... இந்தக் கட்டுரையில் வெளியிடப்படவில்லை ... தெரியவந்ததும் பகிரப்படும்'"""

    def test_script_about_the_article_refused(self):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        d["reel_script"] = ("முட்டை விலை நிலவரம் குறித்த விவரம் இந்தக் கட்டுரையில் வெளியிடப்படவில்லை. "
                            "முட்டை விலை விவரம் தெரியவந்ததும் பகிரப்படும். " + validate.LAST)
        self.assertTrue([x for x in validate.validate(d, "") if "talks about the article" in x])

    def test_foreign_script_refused(self):      # RN-20 headline 'ச監獄탈옥 ... பயிற்சি'
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        d["tamil_headline"] = "ச監獄탈옥: குறைந்த பணியாளர், பயிற்சি பற்றாக்குறை"
        self.assertTrue([x for x in validate.validate(d, "") if "another script" in x])

    def test_normal_script_passes_meta_check(self):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        self.assertFalse([x for x in validate.validate(d, "") if "talks about the article" in x])


class QualityCheck29Oct(unittest.TestCase):
    """owner's quality check 29 Oct (Coimbatore reels RN-8, RN-20, RN-34)"""

    def ex(self):
        return dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])

    def test_card_never_cut_mid_phrase(self):      # RN-34 card 'குடும்பத் தொழில்முனைவு பிரிவில் உலகளவில் சிறந்த 3 இறுதிப்'
        import validate
        long = "குடும்பத் தொழில்முனைவு பிரிவில் உலகளவில் சிறந்த 3 இறுதிப் போட்டியாளர்களில் ஒன்றாக"
        self.assertFalse(validate.DANGLING.search(validate._cut(long, 60)))
        d = self.ex(); sp = d["slides_spec"]
        sp["slides"][0]["lines"][0] = "உலகளவில் சிறந்த 3 இறுதிப்"
        self.assertTrue([x for x in validate.validate(d, "") if "cut off mid-phrase" in x])

    def test_english_in_voice_text_sent_back(self):      # RN-34 'FBN Global Summit' was silently dropped by the voice
        import validate
        d = self.ex(); d["reel_script"] = "ஜெர்மனியில் FBN Global Summit மாநாடு நடந்தது. " + validate.LAST
        self.assertTrue([x for x in validate.validate(d, "") if "English words" in x])

    def test_state_wide_story_not_posted(self):      # RN-8 TNEB promotions, RN-20 prison staffing
        row = {"source": "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/x/1",
               "headline_ta": "மின்வாரியத்தில் 108 ஊழியர்களுக்கு பதவி உயர்வு - கோவை உள்ளிட்ட மண்டலங்கள்", "caption": "", "location": "தமிழ்நாடு மின்வாரியம்"}
        self.assertIn("state-wide", post.not_coimbatore(row))
        self.assertIn("state-wide", post.not_coimbatore({"source": "https://www.hindutamil.in/news/tamilnadu/x", "caption": "",
                                                          "headline_ta": "சிறைதப்பலுக்கு குறைந்த பணியாளர் காரணம்", "location": "தமிழ்நாடு"}))
        row["location"] = "கோயம்புத்தூர் மைய சிறை"
        self.assertNotIn("state-wide", post.not_coimbatore(row))


class SinglePage(unittest.TestCase):
    """Coimbatore 360 is one page: no Rasipuram page, no collaborator, own Sheet column"""

    def test_one_page_no_collab(self):
        row = {"post_to": "Namakkal 360 (collab: Rasipuram 360)", "story_id": "RN-1"}
        self.assertEqual(["coimbatore"], post.pages_of(row))
        self.assertEqual("", post.collab_page(row, "coimbatore"))
        self.assertEqual("", json.loads((ROOT / "poster" / "config.json").read_text()).get("collab_username", ""))

    def test_sheet_column_names_match_bridge(self):
        gs = (ROOT / "apps_script" / "Code.gs").read_text(encoding="utf-8")
        self.assertIn("coimbatore_link: 26", gs)
        self.assertNotIn("namakkal_link", gs)
        self.assertIn("IG_TOKEN_", gs)
        for namakkal_id in ("10lKyQo4rPkSyGP6kj3zvVBpm17r5fXzTa6vwdnu3y00", "1Nm6KqDoS_mz4T9UKxnvVN69EAibWz55p"):      # the Namakkal Sheet / Drive folder (same Gmail, owner 28 Oct)
            self.assertNotIn(namakkal_id, gs)
        self.assertIn("COIMBATORE360", gs)      # its own e-mail tag: the Namakkal bridge never reads Coimbatore mails

    def test_live_switches_are_files(self):      # owner 29 Oct: "go live" - LIVE and research_free/ENABLED switch it on (delete them to stop)
        for f in (ROOT / "LIVE", ROOT / "research_free" / "ENABLED"):
            if f.exists():
                self.assertTrue(f.read_text().strip(), f)


class PrimeTime(unittest.TestCase):
    """owner 27 Oct: non-urgent reels wait for 9-12 / 18-21:30; urgent news never waits; nothing is ever dropped"""
    def at(self, h, m=0):
        return datetime.datetime.combine(TODAY, datetime.time(h, m), IST)

    def row(self, title, filed_h_ago=1):
        t = datetime.datetime.now(IST) - datetime.timedelta(hours=filed_h_ago)
        return {"story_id": "RN-T", "headline_ta": title, "headline_en": "", "category": "", "researched": t.strftime("%d %b %Y, %H:%M")}

    def test_urgent_never_waits(self):
        for title in ("காளப்பநாயக்கன்பட்டி பகுதியில் நாளை மின் தடை", "தனியார் பேருந்து மோதி தொழிலாளி உயிரிழப்பு",
                      "நாமக்கல் மாவட்டத்தில் கனமழை எச்சரிக்கை", "ஆட்சியர் அறிவிப்பு: சிறப்பு முகாம்"):
            self.assertEqual("", post.prime_wait(self.row(title), self.at(14)), title)

    def test_coimbatore_posts_at_once(self):      # owner 29 Oct (Coimbatore): no fixed times, every reel posts the moment it is made
        self.assertFalse(json.loads((ROOT / "poster" / "config.json").read_text())["prime_time"]["enabled"])
        for h in (3, 14, 23):
            self.assertEqual("", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(h)), h)

    def test_posts_inside_prime_time(self):
        self.assertEqual("", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(10)))
        self.assertEqual("", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா"), self.at(19, 30)))

    def test_never_dropped_after_long_wait(self):      # a reel that has waited 12 hours goes out whatever the hour
        self.assertEqual("", post.prime_wait(self.row("கோவில் கும்பாபிஷேக விழா", filed_h_ago=13), self.at(3)))


class ReelOpening(unittest.TestCase):
    """owner 27 Oct (change 1): the most striking fact is spoken first"""
    def test_punch_line(self):
        ns = from_file(ROOT / "reel" / "reel4.py", {"punch_line", "punch_on"})
        self.assertEqual("90,703 குழந்தைகளுக்கு வைட்டமின் ஏ முகாம்!", ns["punch_line"]({"hook": ["குழந்தைகளுக்கு வைட்டமின் ஏ முகாம்", "<b>90,703</b>"]}))
        self.assertEqual("நாளை மின் தடை!", ns["punch_line"]({"hook": ["நாளை மின் தடை", "9 பகுதிகளில் மின் தடை - முழுப் பட்டியல் கீழே பாருங்கள்"]}))
        self.assertEqual("எழுத்தாளர் வரி", ns["punch_line"]({"punch": "<b>எழுத்தாளர்</b> வரி", "hook": ["x", "1"]}))
        # owner 28 Oct: the reel opens with the one-line story itself (first 2-3 s), not a separate punch line
        self.assertFalse(json.loads((ROOT / "poster" / "config.json").read_text()).get("reel_punch"))


class ReelWords(unittest.TestCase):
    """owner 27 Oct: no double reading, full dates, everyday Tamil Nadu words in voice, subtitles and cards"""
    ns = None

    @classmethod
    def setUpClass(cls):
        cls.ns = from_file(ROOT / "reel" / "reel4.py", {"everyday", "everyday_on", "EVERYDAY", "fix_dates", "MONTHS_TA", "repeats", "_words", "punch_line"})

    def test_everyday_words(self):
        e = self.ns["everyday"]
        self.assertEqual("தனியார் பஸ் மோதி டூவீலரில் சென்ற", e("தனியார் பேருந்து மோதி இருசக்கர வாகனத்தில் சென்ற"))
        self.assertEqual("மாவட்ட கலெக்டர் மதுபாலன், கலெக்டரிடம் மனு", e("மாவட்ட ஆட்சியர் மதுபாலன், ஆட்சியரிடம் மனு"))
        self.assertEqual("போலீசார் விசாரணை", e("காவல்துறையினர் விசாரணை"))
        self.assertEqual("திமுக ஆட்சியில்", e("திமுக ஆட்சியில்"))      # 'in rule' is not 'Collector'

    def test_full_dates(self):
        f, T = self.ns["fix_dates"], datetime.date(2026, 10, 27)
        self.assertEqual("முகாம் அக்டோபர் 30ஆம் தேதி வரை நடைபெறும்.", f("முகாம் <b>30</b> வரை நடைபெறும்.", T))
        self.assertEqual("அக்டோபர் 22ஆம் தேதி மணிகட்டிபுதூர்", f("22-ஆம் தேதி மணிகட்டிபுதூர்", T))
        for keep in ("அக்டோபர் 28 அன்று", "மாலை 4:30 வரை", "10.30 வரை", "5 வயது வரையுள்ள"):
            self.assertEqual(keep, f(keep, T))

    def test_no_double_reading(self):
        self.assertTrue(self.ns["repeats"]("தனியார் பஸ் மோதி தொழிலாளி பலி!", "வேலகவுண்டம்பட்டி அருகே தனியார் பஸ் மோதி ஒரு கூலித் தொழிலாளி உயிரிழந்தார்."))
        self.assertFalse(self.ns["repeats"]("நாளை மின் தடை!", "ராசிபுரம் துணை மின் நிலையத்தில் பராமரிப்பு பணி நடைபெறுகிறது."))
        self.assertEqual("தனியார் பேருந்து மோதி தொழிலாளி பலி!", self.ns["punch_line"]({"hook": ["தனியார் பேருந்து மோதி தொழிலாளி பலி", "22 விபத்து, ஞாயிறு"]}))


class Website(unittest.TestCase):
    """owner 27 Oct: every posted story goes to the website with all its details; a website problem never stops posting"""
    def test_payload_has_everything(self):
        import website
        row = {"story_id": "RN-140", "researched": "27 Oct 2026, 10:14", "published": "2026-10-27", "headline_ta": "மரவள்ளி கூட்டம்",
               "headline_en": "Tapioca meeting", "category": "Government & Services", "location": "கோவை", "source": "https://www.dinamalar.com/x/1",
               "caption": "📰 முழு விவரம்:\n🕘 நேரம்: மாலை 4:30", "reel_script": "கூட்டம் நடைபெறும்.",
               "images": '["https://res.cloudinary.com/a.jpg", "NOIMAGE", "http://insecure.jpg"]', "reel_link": "கோயம்புத்தூர் 360: https://www.instagram.com/reel/De_Cu6Pj3zR/"}
        p = website.payload(row, "", {"title_en": "Collector calls meeting", "story_en": "A meeting will be held."})
        self.assertEqual("2026-10-27T10:14:00+05:30", p["filed_at"])      # exact India time, not 12:00
        self.assertEqual(["https://res.cloudinary.com/a.jpg"], p["images"])
        self.assertEqual("Collector calls meeting", p["headline_en"])
        self.assertIn("instagram.com/reel/", p["reel_link"])
        for k in ("location", "category", "source", "caption", "reel_script"):
            self.assertTrue(p[k], k)

    def test_never_raises_without_key(self):
        import website
        os.environ.pop("WEBSITE_INGEST_KEY", None)
        self.assertFalse(website.send({"story_id": "RN-1", "headline_ta": "x", "_en": {"title_en": "x", "story_en": "y" * 50}}, ""))


class FullDetail(unittest.TestCase):
    """28 Oct: reels were 50-90 words while the source article had more detail; owner: full detail, at most 90 seconds"""

    def length_problems(self, words, article_words):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[1]["output"])
        d["reel_script"] = " ".join(["தகவல்"] * words) + " " + validate.LAST
        art = " ".join(f"சொல்{i}" for i in range(article_words))
        return [x for x in validate.validate(d, art) if x.startswith("reel_script has")]

    def test_short_reel_of_long_article_is_rewritten(self):
        self.assertTrue(self.length_problems(70, 300))
        self.assertFalse(self.length_problems(95, 300))      # owner 29 Oct: at most 60 s / 105 words; the caption keeps the rest

    def test_short_article_keeps_a_short_reel(self):
        self.assertFalse(self.length_problems(70, 80))

    def test_never_more_words_than_60_seconds(self):
        self.assertTrue(self.length_problems(130, 400))

    def test_examples_are_full_detail(self):
        for e in json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8")):
            self.assertGreaterEqual(len(e["output"]["reel_script"].split()), 80)

    def test_reel_max_seconds(self):
        self.assertEqual(json.loads((ROOT / "poster" / "config.json").read_text())["reel_max_seconds"], 60)      # owner 29 Oct
        self.assertIn("fit_max(work, len(texts), lead, gap)", (ROOT / "reel" / "reel4.py").read_text(encoding="utf-8"))

class Proofread(unittest.TestCase):
    """28 Oct: the last Tamil proofread damaged posted reels (RN-158 'செல்லாமல் சென்றனர் செல்லாமல்', RN-155 நம்மக்கல்,
    RN-145 'வர வேண்டிய' -> 'வரத் தேவையற்ற', RN-150 மீட்டப்பட்டனர், RN-157 follow line 'மூன்று அறுபது')"""

    def setUp(self):
        import tamilcheck
        self.T = tamilcheck

    def test_bad_fixes_are_refused(self):
        art = "மனைப்பட்டா கேட்டு மனு. சிறுவர்கள் மீட்கப்பட்டனர்."
        for w, ok in [("கோவை", "கோவைய்"), ("பொள்ளாச்சி", "பொல்லாச்சி"), ("வர வேண்டிய", "வரத் தேவையற்ற"), ("த்ரீ சிக்ஸ்டி", "மூன்று அறுபது"),
                      ("Follow", "பின்தொடருங்கள்"), ("கடுமையாக", ""), ("செல்லாமல்", "செல்லாமல் சென்றனர் செல்லாமல்"),
                      ("மீட்கப்பட்டனர்.", "மீட்டப்பட்டனர்."), ("மனைப்பட்டா,", "மனப்பெட்டா,"), ("மேட்டுப்பாளையம்", "மே.பாளையம்")]:
            self.assertTrue(self.T.unsafe(w, ok, art), f"{w} -> {ok} must be refused")

    def test_verb_not_turned_into_noun(self):      # 29 Oct Coimbatore RN-1: 'அரசு நிர்வாகிக்க' -> 'அரசு நிர்வாகம்'
        self.assertTrue(self.T.unsafe("அரசு நிர்வாகிக்க", "அரசு நிர்வாகம்", ""))
        self.assertEqual(self.T.unsafe("அரசு நிர்வாகிக்க", "அரசு நிர்வகிக்க", ""), "")      # the real spelling fix still goes in

    def test_real_spelling_fixes_still_go_in(self):
        for w, ok in [("வெளியிட்டுுள்ளார்.", "வெளியிட்டுள்ளார்."), ("இயக்குனர்", "இயக்குநர்"), ("கீழ்கண்ட", "கீழ்க்கண்ட")]:
            self.assertEqual(self.T.unsafe(w, ok, ""), "")

    def test_rn158_no_word_inside_a_word(self):
        import llm
        row = {"headline_ta": "x", "caption": "பள்ளிக்குச் செல்லாமல்", "slides_spec": "{}",
               "reel_script": "பள்ளிக்குச் செல்லாமல் பிறந்த நாள். ராஜா பள்ளிக்குச் செல்லவில்லை. " + self.T.LAST}
        before = dict(row)
        old = llm.ask_json
        llm.ask_json = lambda *a, **k: ({"fixes": [{"wrong": "செல்ல", "right": "செல்லாமல் சென்ற"}]}, "test")
        try:
            self.T.proofread(row, log=lambda *a: None, article="")
        finally:
            llm.ask_json = old
        self.assertEqual(row, before)

    def test_age_shorthand_sent_back(self):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[1]["output"])
        d["reel_script"] = "வீராச்சாமி தனது மகன் ராஜா, 12, பள்ளிக்குச் செல்லவில்லை. " + validate.LAST
        self.assertTrue([p for p in validate.validate(d, "") if "ages" in p])


class ClearReading(unittest.TestCase):
    """owner 28 Oct: one-line story in the first 2-3 seconds; every number heard with its meaning (age, count, date with month)"""

    def problems(self, script):
        import validate
        d = dict(json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))[0]["output"])
        d["reel_script"] = script + " " + validate.LAST
        return validate.validate(d, "")

    def test_long_opening_sent_back(self):
        self.assertTrue([p for p in self.problems("பள்ளிக்குச் செல்லாமல் பிறந்த நாள் கொண்டாடச் சென்ற மூன்று மாணவர்கள் குமாரபாளையம் பஸ் நிலையத்தில் போலீசாரால் மீட்கப்பட்டனர்.") if p.startswith("sentence 1")])
        self.assertFalse([p for p in self.problems("குமாரபாளையத்தில் மூன்று மாணவர்கள் மீட்பு.") if p.startswith("sentence 1")])

    def test_bare_numbers_sent_back(self):
        self.assertTrue([p for p in self.problems("மாணவர்கள் மீட்பு. கவுசிக், 14, ஸ்ரீதர், 15, காணவில்லை.") if "without their meaning" in p])
        for ok in ("மாணவர்கள் மீட்பு. 14 வயது கவுசிக் காணவில்லை.", "மாணவர்கள் மீட்பு. அக்டோபர் 28, 2026 அன்று கூட்டம்.",
                   "மாணவர்கள் மீட்பு. 30 பாட்டில்கள், ரூ.5,000 பறிமுதல்.", "மாணவர்கள் மீட்பு. விலை 5.70 ரூபாய்."):
            self.assertFalse([p for p in self.problems(ok) if "without their meaning" in p], ok)


class FollowUpAndPage(unittest.TestCase):
    """28 Oct: RN-159 (3 arrested for the laptop theft) was blocked as a duplicate of RN-42 (the theft, 6 days earlier);
    RN-161 (the district Collector's Diwali sweets notice on the paper's Namakkal page) was blocked as not Namakkal news"""

    def test_arrest_after_the_theft_is_new_news(self):
        old = {"story_id": "RN-42", "researched": "22 Oct 2026, 10:26", "headline_en": "Four laptops and a phone stolen from students' room near Thiruchengode",
               "headline_ta": "மாணவர்களின் லேப்டாப் திருட்டு: 4 லேப்டாப், செல்போன் மாயம்"}
        new = {"story_id": "RN-159", "researched": "28 Oct 2026, 06:39", "headline_en": "Three arrested for stealing laptops and mobile phones from student rooms near Tiruchengode",
               "headline_ta": "திருச்செங்கோடு அருகே மடிக்கணினி, கைப்பேசி திருட்டு: 3 பேர் கைது"}
        self.assertTrue(fr.follow_up(old, new))

    def test_same_day_report_stays_a_duplicate(self):
        a = {"researched": "27 Oct 2026, 17:10", "headline_ta": "ஓமலூரில் காணாமல் போன 4 பள்ளி சிறுவர்கள் குமாரபாளையத்தில் மீட்பு"}
        b = {"researched": "28 Oct 2026, 05:46", "headline_ta": "பள்ளி செல்லாமல் பிறந்த நாள் கொண்டாடிய 3 மாணவர்கள் குமாரபாளையத்தில் மீட்பு"}
        self.assertFalse(fr.follow_up(a, b))

    def test_paper_coimbatore_page_is_coimbatore_news(self):
        row = {"source": "https://www.dinamani.com/all-editions/edition-coimbatore/coimbatore/2026/Oct/27/தீபாவளி-இனிப்பு-காரம்-விற்பனைக்கு-உரிமம்-பெறுவது-கட்டாயம்",
               "headline_ta": "தீபாவளி இனிப்பு, காரம் விற்பனைக்கு உரிமம் கட்டாயம்", "caption": "உரிமம் கட்டாயம்", "location": "Tamil Nadu"}
        self.assertEqual(post.not_coimbatore(row), "")
        row["headline_ta"] = "திருப்பூரில் இனிப்பு விற்பனைக்கு உரிமம் கட்டாயம்"
        self.assertTrue(post.not_coimbatore(row))


class Ages(unittest.TestCase):
    """28 Oct RN-156: 'செல்வம், 47,' / 'செல்வம் (47)' was heard as a bare number - the age is said with வயது, also for stories written earlier"""

    def test_newspaper_ages(self):
        import names
        self.assertEqual(names.ages("வசிக்கும் செல்வம், 47, நிதி"), "வசிக்கும் செல்வம் (47 வயது), நிதி")
        self.assertEqual(names.ages("உரிமையாளர் செல்வம் (47), செவ்வாய்"), "உரிமையாளர் செல்வம் (47 வயது), செவ்வாய்")
        self.assertEqual(names.ages("கவுசிக், 14, ஸ்ரீதர், 15, ஆகியோரும்"), "கவுசிக் (14 வயது), ஸ்ரீதர் (15 வயது), ஆகியோரும்")
        for same in ("அக்டோபர் 13, 14, 15ஆம் தேதிகளில்", "அக்டோபர், 12, கூட்டம்", "செல்வம் (47 வயது) வந்தார்", "ரூ.5,000 அபராதம்"):
            self.assertEqual(names.ages(same), same)
        self.assertIn("(47 வயது)", names.spoken("வசிக்கும் செல்வம், 47, நிதி"))


if __name__ == "__main__":
    unittest.main()


class NotNews(unittest.TestCase):
    """owner 29 Oct (RN-189 egg price): a story that only says the article has no details is never filed or posted;
    a real story with one such sentence keeps its facts and loses only that sentence (RN-112)"""
    EMPTY = ("முட்டை விலை நிலவரம் குறித்த விவரம் இந்தக் கட்டுரையில் வெளியிடப்படவில்லை. கட்டுரையில் முட்டை விலை எவ்வளவு என்ற எண்ணோ தகவலோ இல்லை. "
             "வேறு ஒரு செய்தி உள்ளது. அந்தச் செய்தி முட்டை விலையுடன் தொடர்புடையது அல்ல. முட்டை விலை விவரம் தெரியவந்ததும் பகிரப்படும். "
             "மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.")
    REAL = ("நாமக்கல்லில் ஓய்வு பெற்றோர் நலச்சங்கக் கூட்டம் நடைபெற்றது. அகவிலைப்படியுடன் ஓய்வூதியம் வழங்க வேண்டும் என கோரிக்கை விடுக்கப்பட்டது. "
            "மாவட்டத் தலைவர் தலைமை வகித்தார். 2003க்குப் பின் பணியில் சேர்ந்தோர் இக்கோரிக்கையின் கீழ் வருகின்றனர். "
            "மொத்தப் பண பலன்கள் குறித்த முழு விவரம் இன்னும் தெரியவரவில்லை. மேலும் செய்திகளுக்கு நாமக்கல் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.")

    def setUp(self):
        import freshness
        self.f = freshness

    def test_empty_story_rejected(self):
        self.assertTrue(self.f.no_news("முட்டை விலை நிலவரம்", self.EMPTY, "").startswith("not news"))

    def test_headline_saying_no_detail_rejected(self):
        self.assertTrue(self.f.no_news("முட்டை விலை - விவரம் இன்னும் தெரியவில்லை", "", ""))

    def test_real_story_kept_and_cleaned(self):
        self.assertEqual(self.f.no_news("ஓய்வு பெற்றோர் நலச்சங்கக் கூட்டம்", self.REAL, ""), "")
        out = self.f.strip_no_news(self.REAL)
        self.assertNotIn("தெரியவரவில்லை", out)
        self.assertIn("அகவிலைப்படியுடன்", out)
        self.assertTrue(out.endswith("பின்தொடருங்கள்."))

    def test_posting_gate_blocks_it(self):
        row = {"story_id": "RN-189", "headline_ta": "முட்டை விலை நிலவரம்", "headline_en": "Egg price update", "category": "Business & Prices",
               "published": post.datetime.now(post.IST).isoformat(), "researched": post.datetime.now(post.IST).strftime("%d %b %Y, %H:%M"),
               "reel_script": self.EMPTY, "caption": "", "slides_spec": "{}"}
        self.assertTrue(post.skip_reason(row).startswith(("not news", "known issue meta_article")))      # blocked either way


class HeadlineOnlyAndMadeUp(unittest.TestCase):
    """owner 29 Oct (RN-12 Coimbatore, K.N. Nehru raid): a page that is only a headline is not written (the writer invented
    the rest), and a draft whose words mostly do not come from a Tamil article is not filed. Short real briefs still pass."""
    def test_headline_only_page_has_no_body(self):
        a = {"title": "KN Nehru Raid| எதிர்பாரா ட்விஸ்ட்டாக கோவையிலும்.. அதிரும் சிங்காநல்லூர்",
             "text": "KN Nehru Raid| எதிர்பாரா ட்விஸ்ட்டாக கோவையிலும்.. அதிரும் சிங்காநல்லூர் எதிர்பாரா ட்விஸ்ட்டாக கோவையிலும்"}
        self.assertLess(len(collect.body_words(a)), collect.HEADLINE_ONLY_MIN)

    def test_short_real_brief_passes(self):
        a = {"title": "சூதாட்டம் ஆடிய 6 பேருக்கு காப்பு",
             "text": "சூதாட்டம் ஆடிய 6 பேருக்கு காப்பு. பரமத்தி வேலூர் போலீசார் ரோந்து சென்றபோது பணம் வைத்து சூதாடிய ஆறு பேரை கைது செய்து ரூ.11,600 பறிமுதல் செய்தனர். அனைவரும் ஜாமீனில் விடுவிக்கப்பட்டனர்."}
        self.assertGreaterEqual(len(collect.body_words(a)), collect.HEADLINE_ONLY_MIN)

    def test_made_up_draft_rejected(self):
        art = {"url": "https://example.com/a", "title": "t", "published": collect.datetime.datetime.now(collect.IST).isoformat(),
               "text": " ".join(["நாமக்கல்லில்", "போலீசார்", "விசாரணை", "நடத்தினர்", "பொதுமக்கள்", "கோரிக்கை"] * 15)}
        d = {"tamil_headline": "நாமக்கல் செய்தி", "english_headline": "x", "category": "c", "location": "l", "scenes": ["s"],
             "reel_script": "", "caption": "", "slides_spec": {}}
        story, why = collect.file_story(art, (d, "test", ["not grounded: only 37% of the words come from the article"], 1), [], [])
        self.assertIsNone(story)
        self.assertIn("likely made up", why)


class OtherScriptLetters(unittest.TestCase):
    """owner 29 Oct (Coimbatore RN-5, 7, 17, 20, 22): letters of another script inside Tamil words are repaired, so the voice
    reads the word and the card shows Tamil letters; Chinese/Korean letters are removed"""
    def test_indic_letters_become_tamil(self):
        import verify
        self.assertEqual(verify.fix_scripts("ஒண்டிப்புதூர் மின்பிரிவில்".replace("ர்", "র்", 1)), "ஒண்டிப்புதூர் மின்பிரிவில்")
        self.assertEqual(verify.clean_text("நির்देசம்"), "நிர்தேசம்")
        self.assertEqual(verify.clean_text("போலீस் நிலையம்"), "போலீஸ் நிலையம்")

    def test_cjk_removed_and_tamil_untouched(self):
        import verify
        self.assertNotRegex(verify.clean_text("தேனி சிறை탈출்க்குப் பின்னர்"), "[가-힯]")
        s = "சாதாரண தமிழ் வாக்கியம்: ரூ.1,109 கட்டணம், 26ஆம் தேதி."
        self.assertEqual(verify.clean_text(s), s)


class TamilSourcesOnly(unittest.TestCase):
    """owner 29 Oct: news only from Tamil-language articles; English pages are skipped (a hand-given link still goes)"""
    def test_english_article_skipped(self):
        a = {"title": "Coimbatore court sentences six to 10 years in prison in 2015 child trafficking case",
             "text": "A Coimbatore court on Wednesday sentenced six people to ten years in prison in a 2015 case of selling a one-year-old girl. " * 4}
        self.assertFalse(collect.tamil_source(a))

    def test_tamil_article_kept(self):
        a = {"title": "கோவையில் விளக்கேற்றும்போது சேலை தீப்பிடித்து மூதாட்டி உயிரிழப்பு",
             "text": "சாய்பாபா காலனி, கே.கே.புதூர் 7ஆம் வீதியில் வசிக்கும் லட்சுமி பூஜை அறையில் விளக்கேற்றியபோது சேலையில் தீ பற்றியது. Coimbatore."}
        self.assertTrue(collect.tamil_source(a))


class TamilOutletsOnly(unittest.TestCase):
    """owner 29 Oct: Coimbatore news only from Tamil-language websites of Tamil Nadu papers and channels"""
    def test_english_and_foreign_outlets_dropped(self):
        for it in ({"via": "bing", "url": "https://www.newindianexpress.com/cities/coimbatore/x"},
                   {"via": "google", "url": "https://news.google.com/rss/articles/a", "site": "https://www.dtnext.in"},
                   {"via": "bing", "url": "https://timesofindia.indiatimes.com/city/coimbatore/x"},
                   {"via": "bing", "url": "https://www.tamilmurasu.com.sg/x"}):
            self.assertFalse(allnews.tamil_outlet(it), it)

    def test_tamil_outlets_kept(self):
        for it in ({"via": "bing", "url": "https://www.dinamalar.com/news/tamil-nadu-district-news-coimbatore/x/1"},
                   {"via": "google", "url": "https://news.google.com/rss/articles/a", "site": "https://www.dailythanthi.com"},
                   {"via": "bing", "url": "https://tamil.news18.com/tamil-nadu/coimbatore/x"},
                   {"via": "listing", "url": "https://www.dinamani.com/x"}):
            self.assertTrue(allnews.tamil_outlet(it), it)
        self.assertNotIn("thehindu.com", allnews.SITES.values())


class ReelTooLong(unittest.TestCase):
    """owner 28 Oct (RN-153): a reel over 90 s is shortened automatically, never held"""
    SCRIPT = ("பொத்தனூர் சந்தையில் இரண்டு வாரங்களாக தேங்காய் ஏலம் நடைபெறவில்லை. விவசாயிகள் பாதிக்கப்பட்டுள்ளனர். "
              "வாரந்தோறும் செவ்வாய், வியாழக்கிழமைகளில் ஏலம் நடைபெறுவது வழக்கம். பல ஊர்களைச் சேர்ந்த விவசாயிகள் இங்கு வருகின்றனர். "
              "வியாபாரிகள் ஏலத்தில் பங்கேற்க மறுத்தனர். வெளிச் சந்தைகளில் குறைந்த விலையே கிடைக்கும். "
              "மேலும் செய்திகளுக்கு கோயம்புத்தூர் த்ரீ சிக்ஸ்டி பக்கத்தை பின்தொடருங்கள்.")

    def test_shorter_keeps_first_and_follow_line(self):
        out = post.shorten_script(self.SCRIPT, 0.5)
        self.assertLess(len(out), len(self.SCRIPT))
        self.assertTrue(out.startswith("பொத்தனூர் சந்தையில்"))
        self.assertTrue(out.endswith("பின்தொடருங்கள்."))
        self.assertGreaterEqual(len(re.split(r"(?<=[.!?])\s+", out)), 3)

    def test_short_script_unchanged(self):
        s = "ஒன்று. இரண்டு. மேலும் செய்திகளுக்கு பின்தொடருங்கள்."
        self.assertEqual(post.shorten_script(s, 0.5), s)


class OldEventAndSameEvent(unittest.TestCase):
    """owner 29 Oct: an old event re-told in a new article (Coimbatore RN-29, a Dec 2025 wedding) is not posted; the same event
    from another outlet in other words (Coimbatore RN-13 / RN-24 bus fight) is not posted twice"""
    def test_old_event(self):
        import freshness, datetime
        t = "நடிகை சமந்தா, இயக்குநர் ராஜ் திருமணம் செய்துகொண்டனர். 1 டிசம்பர் 2025 அன்று லிங்க பைரவி கோயிலில் திருமணம் நடந்தது."
        self.assertTrue(freshness.old_event(t, datetime.date(2026, 10, 29)))
        self.assertEqual(freshness.old_event("2015 ஜூலை 28 குழந்தை விற்பனை வழக்கில் புதன்கிழமை தீர்ப்பு: 6 பேருக்கு சிறை", datetime.date(2026, 10, 29)), "")
        self.assertEqual(freshness.old_event("பள்ளிப்பாளையத்தில் தெருநாய் தொல்லை அதிகரிப்பு, மக்கள் கோரிக்கை", datetime.date(2026, 10, 29)), "")

    def test_same_event_other_words(self):
        import freshness
        a = ("கோவையில் பேருந்து ஓட்டுநர்கள் நடுரோட்டில் தாக்கிக்கொண்ட சம்பவம் வைரல். இரண்டு தனியார் பேருந்துகளின் ஓட்டுநர்கள் மற்றும் நடத்துநர்கள் "
             "பயணிகளை ஏற்றுவதில் ஏற்பட்ட போட்டியால் நடுரோட்டில் அடிதடியில் ஈடுபட்டனர். வீடியோ இணையத்தில் பரவியது. பீளமேடு போக்குவரத்து பாதிப்பு.")
        b = ("பீளமேடுவில் இரண்டு பேருந்து ஊழியர்கள் நடுரோட்டில் அடிதடி. தனியார் பேருந்துகளின் ஓட்டுனர்கள் நடத்துனர்கள் பயணிகளை ஏற்றுவதில் "
             "போட்டியால் மோதல். நடுரோட்டில் சரமாரியாக தாக்கினர். காட்சிகள் இணையத்தில் பரவியது. பீளமேடு போக்குவரத்து பாதிப்பு.")
        other = ["எருமப்பட்டியில் குப்பை எரித்தபோது தீ விபத்து", "நாமக்கல்லில் முட்டை விலை ரூ.5.70", "மோகனூரில் மணல் திருட்டு"] * 10
        df = freshness.event_df([a, b] + other)
        self.assertTrue(freshness.same_event(a, b, df))
        self.assertFalse(freshness.same_event(a, other[0] * 3, df))


class ResearchedOutletsOnly(unittest.TestCase):
    """owner 29 Oct 17:59: Coimbatore news only from the researched outlets (13); nothing else is kept"""
    def test_list(self):
        self.assertEqual(len(allnews.SITES), 13)
        for keep in ("https://covaimail.com/x/", "https://arasiyaltoday.com/x/", "https://www.dinamani.com/all-editions/edition-coimbatore/x"):
            self.assertTrue(allnews.tamil_outlet({"via": "bing", "url": keep}), keep)
        for drop in ("https://tamil.oneindia.com/news/coimbatore/x", "https://www.vikatan.com/x", "https://tamil.abplive.com/x"):
            self.assertFalse(allnews.tamil_outlet({"via": "bing", "url": drop}), drop)


class TodayOnlyCoimbatore(unittest.TestCase):
    """owner 29 Oct 18:29: Coimbatore writes and posts only news whose article is published TODAY (IST)"""
    def test_published_today(self):
        now = collect.datetime.datetime.now(collect.IST)
        self.assertTrue(collect.published_today(now.isoformat()))
        self.assertFalse(collect.published_today((now - collect.datetime.timedelta(days=1)).isoformat()))
        self.assertFalse(collect.published_today(""))          # no date on the article = not taken

    def test_posting_gate_today_only(self):
        import os
        os.environ["POST_MAX_AGE_DAYS"] = "0"
        try:
            y = (post.datetime.now(post.IST) - post.timedelta(days=1)).isoformat()
            row = {"story_id": "RN-x", "headline_ta": "கோவையில் செய்தி", "headline_en": "x", "published": y,
                   "researched": post.datetime.now(post.IST).strftime("%d %b %Y, %H:%M"), "slides_spec": "{}"}
            self.assertIn("not today", post.skip_reason(row))
        finally:
            os.environ.pop("POST_MAX_AGE_DAYS", None)

    def test_utc_time_read_in_ist(self):
        import freshness, datetime
        self.assertEqual(freshness.pub_date("2026-10-28T22:17:23.761Z"), datetime.date(2026, 10, 29))


class SameEventAtWriteTime(unittest.TestCase):
    """29 Oct RN-193: the online cracker scam (posted as RN-168 on 28 Oct) was written again from another outlet,
    because the headlines differ by one number ('2 நாட்களில்') - the article text is now checked against filed reel scripts"""
    RN168 = 'ஆன்லைனில் குறைந்த விலை பட்டாசு என்ற போலி விளம்பரங்களை நம்பி நாமக்கல் மாவட்டத்தில் 25 பேர் ஏமாந்துள்ளனர். 2 நாட்களில் அவர்கள் மொத்தம் ரூ.1.50 லட்சம் இழந்துள்ளனர். தீபாவளி பண்டிகை நவம்பர் 8ஆம் தேதி கொண்டாடப்படுகிறது. இதையொட்டி பொதுமக்கள் பட்டாசுகளை ஆன்லைனில் ஆர்டர் செய்கின்றனர். இதை பயன்படுத்தி மோசடி கும்பல்கள் போலி இணையதளங்கள் மற்றும் சமூக வலைதளங்களில் விளம்பரம் செய்கின்றன. சிவகாசி பட்டாசுகளுக்கு 75 முதல் 80 சதவீதம் வரை தள்ளுபடி என்று கூறி ஏமாற்றுகின்றனர். முதலீடு செய்தால் இரட்டிப்பு பணம் கிடைக்கும் என்றும் ஆசை காட்டுகின்றனர். நாமக்கல் மாவட்ட சைபர் கிரைம் போலீஸ் ஏடிஎஸ்பி விஜயராகவன், பட்டாசு ஆர்டர் செய்வதற்கு முன் இணையதளம் அல்லது நிறுவனத்தின் நம்பகத்தன்மையை உறுதி செய்ய வேண்டும் என அறிவுறுத்தியுள்ளார்.'
    ART = 'ஆன்லைன் பட்டாசு விளம்பரத்தை நம்பி நாமக்கல் மாவட்டத்தில் 25 பேர் ரூ.1.50 லட்சம் பணத்தை இழந்துள்ள சம்பவம் பெரும் பரபரப்பை ஏற்படுத்தியுள்ளது. வரும் நவம்பர் 8ஆம் தேதி தீபாவளி பண்டிகை கொண்டாடப்பட உள்ள நிலையில், சிவகாசியில் இருந்து ஆன்லைன் மூலம் பொதுமக்கள் பட்டாசுகளைத் தேர்வு செய்து ஆர்டர் செய்து வருகின்றனர். இதைப் பயன்படுத்திக் கொள்ளும் மோசடிக் கும்பல்கள், போலி இணையதளங்கள் மற்றும் சமூக வலைதளங்கள் மூலம் விளம்பரம் செய்து பொதுமக்களை ஏமாற்றி வருகின்றன. குறிப்பாக, சிவகாசி பட்டாசுகளுக்கு 75 முதல் 80 சதவீதம் வரை தள்ளுபடி தருவதாகக் கூறி போலி விளம்பரங்கள் வாயிலாகப் பணம் பறிக்கப்படுகிறது. இது குறித்து எச்சரிக்கை விடுத்துள்ள நாமக்கல் மாவட்ட சைபர் கிரைம் காவல் கூடுதல் கண்காணிப்பாளர் விஜயராகவன், பொதுமக்கள் பட்டாசு ஆர்டர் செய்யும் முன் இணையதளத்தின் நம்பகத்தன்மையை உறுதி செய்ய வேண்டும் எனத் தெரிவித்துள்ளார்.'
    OTHER = [("RN-%d" % i, "நாமக்கல் %s சாலை பணி %d கோடி ரூபாய் ஒதுக்கீடு செய்யப்பட்டு பணிகள் தொடக்கம் ஊராட்சி தலைவர் தகவல்" % (w, i))
             for i, w in enumerate(["மோகனூர்", "சேந்தமங்கலம்", "எருமப்பட்டி", "கொல்லிமலை", "பரமத்தி", "வெண்ணந்தூர்"], 1)]

    def recent(self, when):
        rows = [{"story_id": "RN-168", "researched": when, "reel_script": self.RN168}]
        rows += [{"story_id": s, "researched": when, "reel_script": t} for s, t in self.OTHER]
        return rows

    def test_same_event_other_outlet_is_not_written(self):
        art = {"title": "ஆன்லைன் பட்டாசு மோகம்: நாமக்கல்லில் 2 நாட்களில் 25 பேர் ரூ.1.50 லட்சம் இழப்பு", "text": self.ART,
               "published": TODAY.isoformat()}
        y = (TODAY - datetime.timedelta(days=1)).strftime("%d %b %Y, 22:32")
        self.assertEqual(collect.same_event_filed(art, self.recent(y)), "RN-168")

    def test_old_story_or_other_news_is_not_a_duplicate(self):
        art = {"title": "x", "text": self.ART, "published": TODAY.isoformat()}
        old = (TODAY - datetime.timedelta(days=5)).strftime("%d %b %Y, 22:32")
        self.assertEqual(collect.same_event_filed(art, self.recent(old)), "")
        other = {"title": "ராசிபுரம் ஏரியில் கழிவுநீர்", "text": self.OTHER[0][1], "published": TODAY.isoformat()}
        rows = [r for r in self.recent(TODAY.strftime("%d %b %Y, 10:00")) if r["story_id"] != "RN-1"]
        self.assertEqual(collect.same_event_filed(other, rows), "")


class ListingPagesAreNotArticles(unittest.TestCase):
    """29 Oct RN-194: tamil.abplive.com/topic/missing-girl/page-2 (a list of stories from all districts) was written as one story"""
    def test_listing_urls(self):
        for u in ("https://tamil.abplive.com/topic/missing-girl/page-2/amp", "https://www.example.com/tag/namakkal",
                  "https://tamil.news18.com/author/x/", "https://site.in/news?page=3"):
            self.assertTrue(allnews.is_listing(u), u)
            self.assertFalse(allnews.local_ok(u, "நாமக்கல்லில் சிறுமி மீட்பு"), u)
        for u in ("https://www.dinamani.com/all-editions/edition-dharmapuri/namakkal/2026/Oct/29/x",
                  "https://www.dinamalar.com/news/tamil-nadu-district-news-namakkal/pallipalayam-farmers-worr/1"):
            self.assertFalse(allnews.is_listing(u), u)


class CaptionCleanRuns(unittest.TestCase):
    """29 Oct: clean_caption used verify without importing it - every post job crashed with NameError for ~2.5 hours"""
    def test_clean_caption_runs(self):
        out = post.clean_caption({"caption": "செய்தி வரி ஒன்று\n\n#News", "headline_ta": "செய்தி", "story_id": "RN-1"})
        self.assertIn(out, (True, False, None) if not isinstance(out, str) else (out,))      # it must simply run


class KnownIssuesNeverRepeat(unittest.TestCase):
    """owner 29 Oct: once an issue is found it must never repeat - every entry of research_free/known_issues.py catches its own
    bad example and lets its good example through, at writing (validate) and at posting (skip_reason)"""

    def test_every_issue_catches_its_example(self):
        import known_issues
        for iid, seen, check, bad, good in known_issues.ISSUES:
            self.assertIn(iid, [x for x, _ in known_issues.problems(bad)], f"{iid} ({seen}) no longer caught")
            self.assertNotIn(iid, [x for x, _ in known_issues.problems(good)], f"{iid} blocks a good story")

    def test_checked_at_posting(self):
        import known_issues
        post.ALL_ROWS = []
        for iid, seen, check, bad, good in known_issues.ISSUES:
            row = dict(bad, story_id="RN-T", source="", published="", researched="", notes="", batch="", review="Auto")
            import verify
            fixed = known_issues.repair(dict(row, **{k: verify.clean_text(row.get(k) or "") for k in ("headline_ta", "reel_script", "caption")}))
            repaired = iid not in [x for x, _ in known_issues.problems(fixed)]      # e.g. stray letters of another script are repaired
            self.assertTrue(repaired or f"known issue {iid}" in post.skip_reason(row), f"{iid} would be posted again")


class ReachPlan29Oct(unittest.TestCase):
    """owner 29 Oct views plan: 60 s reels, full details in the caption, English search line, 5 focused hashtags, no brand names in pictures"""
    ROW = {"headline_ta": "காந்திபுரத்தில் பஸ் மோதி விபத்து", "headline_en": "Bus accident at Gandhipuram", "location": "காந்திபுரம், கோவை",
           "caption": "🚌 காந்திபுரத்தில் பஸ் மோதி விபத்து\n\n📰 முழு விவரம்:\nகாந்திபுரம் பஸ் நிலையம் அருகே இன்று காலை விபத்து நடந்தது.\n\n"
                      "📍 காந்திபுரம், கோவை | 29 அக்டோபர் 2026\n\n#Coimbatore360 #Coimbatore #தீபுறம்போக்கு #விபத்து #CoimbatoreNews"}

    def test_five_focused_hashtags(self):
        tags = post.final_caption(dict(self.ROW)).strip().split("\n")[-1].split()
        self.assertEqual(5, len(tags))
        for t in ("#Coimbatore360", "#Coimbatore", "#Gandhipuram", "#Accident", "#CoimbatoreNews"):
            self.assertIn(t, tags)
        self.assertNotIn("#தீபுறம்போக்கு", tags)      # junk tag from the writer is dropped

    def test_english_search_line_added(self):
        out = post.final_caption(dict(self.ROW))
        self.assertIn("Bus accident at Gandhipuram | Coimbatore news", out)
        self.assertLess(out.index("Bus accident at Gandhipuram"), out.index("📍"))

    def test_caption_must_carry_full_details(self):
        import validate
        on = {"caption_full_details": True}
        self.assertTrue(validate.caption_problems("🚌 விபத்து\n\n#Coimbatore360", on))
        self.assertFalse(validate.caption_problems(
            "🚌 விபத்து\n\n📰 முழு விவரம்:\nகாந்திபுரம் பஸ் நிலையம் அருகே இன்று விபத்து நடந்தது.\nஇரண்டு பேர் காயமடைந்து மருத்துவமனையில் சேர்க்கப்பட்டனர்.\n"
            "போலீசார் வழக்குப் பதிவு செய்து விசாரணை நடத்தி வருகின்றனர்.", on))

    def test_switches_and_picture_rule(self):
        c = json.loads((ROOT / "poster" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(60, c["reel_max_seconds"])
        self.assertEqual(105, c["reach"]["script_max_words"])
        self.assertIn("no brand names", collect.IMG_TEMPLATE)


class CaptionAllFacts(unittest.TestCase):
    """owner 29 Oct: the caption must hold ALL the information of the news (Namakkal RN-175, 178, 181: a date, ages, a percentage were missing)"""
    ART = ("ராசிபுரம், அக்.29: ராசிபுரம் பகுதியில் தொடர்ந்து பைக்குகள் திருடப்பட்டு வந்தன. "
           "அதை தொடர்ந்து, கடந்த 17ல், பேளுக்குறிச்சி முத்துராஜ் என்பவரின் பைக் திருடப்பட்டது; அந்த திருட்டிலும் வாலிபர் சம்பந்தப்பட்டார். "
           "பைக் திருட்டு வழக்கில் போலீசார் 23 வயது வாலிபரை கைது செய்தனர். "
           "நாமக்கல்லில் நவ.1ல் குரூப் 2 தேர்வு: 14,199 பேர் பங்கேற்பு")      # the last line is another headline on the same page
    STORY = "ராசிபுரத்தில் பைக் திருட்டு: வாலிபர் கைது. பேளுக்குறிச்சி முத்துராஜ் பைக் திருடப்பட்டது. போலீசார் வாலிபரை கைது செய்தனர்."

    def test_missing_fact_found(self):
        import validate
        miss = validate.caption_missing_facts("📰 முழு விவரம்:\nபைக் திருட்டு வழக்கில் 23 வயது வாலிபர் கைது.", self.ART, self.STORY)
        self.assertTrue(any(m.startswith("17") for m in miss), miss)

    def test_other_headlines_and_dateline_ignored(self):
        import validate
        cap = "📰 முழு விவரம்:\nராசிபுரத்தில் 17ஆம் தேதி பைக் திருடப்பட்டது; பைக் திருட்டு வழக்கில் 23 வயது வாலிபர் கைது."
        self.assertEqual([], validate.caption_missing_facts(cap, self.ART, self.STORY))


class RepairNotLose(unittest.TestCase):
    """owner 30 Oct: RN-199, RN-200, RN-203 were held back for a card cut mid-phrase / a sentence said twice - repair them, never lose the news"""

    def test_card_and_repeat_repaired(self):
        import known_issues
        row = {"headline_ta": "பயிற்சி வகுப்பு", "caption": "📰 முழு விவரம்:\nவிவரம் இங்கே.",
               "reel_script": "இன்று பயிற்சி வகுப்பு தொடங்கியது. இன்று பயிற்சி வகுப்பு தொடங்கியது. மாணவர்கள் கலந்துகொண்டனர்.",
               "slides_spec": json.dumps({"slides": [{"lines": ["மாணவர்களுக்கு இலவச பயிற்சி வகுப்புகளுக்குப்", "நாளை தொடக்கம்"]}]}, ensure_ascii=False)}
        fixed = known_issues.repair(row)
        self.assertEqual([], known_issues.problems(fixed))
        self.assertEqual(1, fixed["reel_script"].count("இன்று பயிற்சி வகுப்பு தொடங்கியது"))
        self.assertIn("மாணவர்கள் கலந்துகொண்டனர்", fixed["reel_script"])
        post.ALL_ROWS = []
        self.assertNotIn("known issue", post.skip_reason(dict(row, story_id="RN-T", source="", published="", researched="", review="Auto")))

