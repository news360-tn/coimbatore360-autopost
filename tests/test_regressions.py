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
        rest = (score("கோவையில் தனியார் வேலைவாய்ப்பு முகாம்"), score("கோவை கோயில் திருவிழா"))
        self.assertTrue(cut > crime > acc > civic > max(rest), (cut, crime, acc, civic, rest))
        rain = score("கோவையில் கனமழை")      # owner 31 Oct scale: rain warning 9 - just below a power cut, level with crime
        self.assertTrue(cut > rain >= crime, (cut, rain, crime))

    def test_today_only(self):
        self.assertEqual(1, collect.FRESH_DAYS)
        self.assertTrue(collect.fresh(datetime.datetime.now(IST).isoformat()))
        self.assertFalse(collect.fresh((datetime.datetime.now(IST) - datetime.timedelta(days=1)).isoformat()))
        self.assertTrue(collect.fresh((datetime.datetime.now(IST) - datetime.timedelta(hours=2)).isoformat()))      # 11:30 pm news at the 1 am round

    def test_ten_rounds_cap_30(self):      # owner 31 Oct: rounds IST 04:00-22:00 every 2 h, top 3 each (29 Oct: every 2 h, cap 50)
        wf = ROOT / ".github" / "workflows"
        self.assertIn('cron: "30 22,0,2,4,6,8,10,12,14,16 * * *"', (wf / "research_free.yml").read_text())
        self.assertIn('age("collect") > 160', (wf / "post.yml").read_text())
        for f in ("post.yml", "research_free.yml", "write_stories.yml"):
            self.assertIn('DAILY_CAP: "30"', (wf / f).read_text(), f)
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
        self.assertEqual(2, len(d["scenes"]))      # owner 30 Oct: 2 pictures per reel (cover + detail)
        d["scenes"] = [d["scenes"][0]] * 3
        self.assertTrue([x for x in validate.validate(d, "") if x.startswith("scenes must")], "three image prompts must be refused")
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
        self.assertFalse(hasattr(llm, "GHM_MODELS"))      # owner 30 Oct: GitHub Models removed (bad answer every time)
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
        self.assertIn("fit_max(work, len(texts), lead, gap, max_seconds(spec))", (ROOT / "reel" / "reel4.py").read_text(encoding="utf-8"))

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


class CodeBugsNeverRepeat(unittest.TestCase):
    """owner 30 Oct: a bug fixed once must never come back. 29 Oct every posting job crashed: 'verify' was used in clean_caption without
    being imported. (1) No file may use a name that is not defined (checked by pyflakes on GitHub). (2) The caption and posting-check
    steps are run end to end on a sample story, so a crash there fails the tests, not the live posting."""

    def test_no_undefined_names(self):
        try:
            from pyflakes import api, reporter
        except ImportError:
            self.skipTest("pyflakes is installed by tests.yml on GitHub")
        import io, glob
        out, err = io.StringIO(), io.StringIO()
        for f in sorted(glob.glob(str(ROOT / "poster" / "*.py")) + glob.glob(str(ROOT / "research_free" / "*.py")) + glob.glob(str(ROOT / "reel" / "*.py"))):
            api.checkPath(f, reporter.Reporter(out, err))
        bad = [l for l in out.getvalue().splitlines() if "undefined name" in l or "referenced before assignment" in l]
        self.assertEqual([], bad)

    def test_posting_text_steps_run(self):
        post.ALL_ROWS = []
        row = {"story_id": "RN-T", "headline_ta": "சோதனை செய்தி: சாலை விபத்து", "headline_en": "Road accident test", "category": "Accident",
               "location": "", "source": "", "published": "", "researched": "", "notes": "", "batch": "", "review": "Auto", "post_to": "",
               "caption": "🚗 சோதனை செய்தி\n\n📰 முழு விவரம்:\nசாலையில் விபத்து நடந்தது.\n\n#Test",
               "reel_script": "சாலையில் விபத்து நடந்தது. மேலும் செய்திகளுக்கு பின்தொடருங்கள்.", "slides_spec": json.dumps({"v": 3, "slides": []})}
        post.clean_caption(dict(row))
        post.final_caption(dict(row))
        post.check_text(dict(row), json.loads(row["slides_spec"]))
        post.skip_reason(dict(row))


class FreePicturesFirst30Oct(unittest.TestCase):
    """owner 30 Oct: free pictures first - Cloudflare (pictures only) -> SiliconFlow -> Together -> Pollinations -> NVIDIA -> FAL last;
    2 pictures per reel; a service without its key is skipped (nothing changes until the owner adds it)"""

    def run_order(self, fail, keys):
        import imagegen
        calls = []
        def src(name):
            def f(*a, **k):
                calls.append(name)
                if name in fail:
                    raise RuntimeError(name + " 429: daily limit (per day)")
                return b"img"
            return f
        saved = {k: getattr(imagegen, k) for k in ("_cf", "generate_nvidia", "_fal", "to_story_size", "EXTRA_FREE")}
        names = ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "NVIDIA_API_KEY", "FAL_KEY", "TOGETHER_API_KEY", "POLLINATIONS_API_KEY")
        env = {k: os.environ.get(k) for k in names}
        imagegen._cf, imagegen.generate_nvidia, imagegen.to_story_size = src("cloudflare"), src("nvidia"), (lambda b: b)
        imagegen._fal = lambda p, s, k, model=None: src("fal")()
        imagegen.EXTRA_FREE = [(n, e, src(n)) for n, e, _ in saved["EXTRA_FREE"]]
        for k in names:
            os.environ.pop(k, None)
        os.environ.update({k: "test" for k in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "NVIDIA_API_KEY", "FAL_KEY") + keys})
        imagegen.DEAD.clear()
        real_sleep, imagegen.time.sleep = imagegen.time.sleep, (lambda *a: None)      # no real waiting between retries in tests
        try:
            imagegen.generate("A police jeep at Rasipuram bus stand", 1)
        except Exception:
            pass
        finally:
            imagegen.time.sleep = real_sleep
            for k, v in saved.items():
                setattr(imagegen, k, v)
            for k, v in env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
            imagegen.DEAD.clear()
        return calls

    def test_order_with_all_keys(self):      # owner 30 Oct: Cloudflare -> Pollinations -> NVIDIA -> FAL (SiliconFlow removed, Together not used)
        keys = ("POLLINATIONS_API_KEY",)
        self.assertEqual(["cloudflare"], self.run_order(set(), keys))
        self.assertEqual("pollinations", self.run_order({"cloudflare"}, keys)[-1])
        calls = self.run_order({"cloudflare", "pollinations", "nvidia"}, keys)
        self.assertEqual("fal", calls[-1], calls)      # paid FAL only after every free one
        self.assertNotIn("fal", self.run_order({"cloudflare"}, keys))
        import imagegen
        self.assertNotIn("siliconflow", [n for n, _, _ in imagegen.EXTRA_FREE])

    def test_missing_key_means_skipped(self):
        calls = self.run_order({"cloudflare"}, ())
        self.assertNotIn("pollinations", calls)
        self.assertEqual("nvidia", calls[-1])      # without the new keys the order is exactly as before

    def test_cloudflare_kept_for_pictures(self):
        import llm
        old = {k: os.environ.get(k) for k in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "GEMINI_API_KEY", "GROQ_API_KEY", "GH_MODELS_TOKEN", "NVIDIA_API_KEY", "MISTRAL_API_KEY", "OPENROUTER_API_KEY")}
        for k in old:
            os.environ.pop(k, None)
        os.environ.update(CLOUDFLARE_API_TOKEN="t", CLOUDFLARE_ACCOUNT_ID="a")
        try:
            self.assertFalse([c for c in llm.chain() if c[0] == "cloudflare"])
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_two_pictures_per_reel(self):
        self.assertEqual(2, collect.pictures_per_reel())
        self.assertEqual(2, json.loads((ROOT / "poster" / "config.json").read_text(encoding="utf-8"))["free_images"]["pictures_per_reel"])


class FreeWriters30Oct(unittest.TestCase):
    """owner 30 Oct: only free writing models that really work - Gemini 3.6/3.5 first (3.8/3.7 skipped), Sarvam, Gemma 4, Groq;
    Cerebras removed (needs a card);
    GitHub Models, Mistral, OpenRouter, NVIDIA text removed; a provider without its key is skipped; Claude (paid) only after all of them"""
    KEYS = ("GEMINI_API_KEY", "SARVAM_API_KEY", "CEREBRAS_API_KEY", "GROQ_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
            "GH_MODELS_TOKEN", "MISTRAL_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY")

    def build(self, keys):
        import llm
        old = {k: os.environ.get(k) for k in self.KEYS}
        saved = (llm.gemini_models, llm.groq_models)
        for k in self.KEYS:
            os.environ.pop(k, None)
        os.environ.update({k: "t" for k in keys})
        llm.gemini_models = lambda key: ["gemini-3.6-flash", "gemini-3.5-flash"]
        llm.groq_models = lambda key: ["openai/gpt-oss-120b"]
        try:
            return [(p, m) for p, m, _, _ in llm.chain()]
        finally:
            llm.gemini_models, llm.groq_models = saved
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_order_and_removed(self):
        everything = ("GEMINI_API_KEY", "SARVAM_API_KEY", "CEREBRAS_API_KEY", "GROQ_API_KEY", "GH_MODELS_TOKEN", "MISTRAL_API_KEY",
                      "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")
        ch = self.build(everything)
        providers = list(dict.fromkeys(p for p, _ in ch))
        self.assertEqual(["gemini", "groq"], providers)      # Sarvam off until writer-compare proves it (30 Oct: empty answers)      # Gemma ready but not live until proven (30 Oct test: 503/500)
        self.assertEqual(("gemini", "gemini-3.6-flash"), ch[0])
        import llm
        self.assertFalse(hasattr(llm, "_cerebras"))      # 30 Oct: Cerebras needs a card - paid, not used

    def test_without_new_keys_same_as_before(self):
        providers = list(dict.fromkeys(p for p, _ in self.build(("GEMINI_API_KEY", "GROQ_API_KEY"))))
        self.assertEqual(["gemini", "groq"], providers)      # Sarvam skipped until its key exists
        os.environ["WRITERS_ORDER"] = "gemma"
        try:
            self.assertEqual(["gemma"], list(dict.fromkeys(p for p, _ in self.build(("GEMINI_API_KEY",)))))      # writer-compare can test one
        finally:
            os.environ.pop("WRITERS_ORDER", None)

    def test_gemini_never_answering_models_last(self):
        import llm
        class R:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {"models": [{"name": "models/" + n, "supportedGenerationMethods": ["generateContent"]}
                                   for n in ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash")]}
        real = llm.requests.get
        llm.requests.get = lambda *a, **k: R()
        try:
            got = llm.gemini_models("k")
        finally:
            llm.requests.get = real
        self.assertEqual(["gemini-3.6-flash", "gemini-3.5-flash"], got[:2])
        self.assertNotIn("gemini-3.8-flash", got)

    def test_gemma_reads_the_answer_not_the_thinking(self):
        import llm
        class R:
            status_code = 200
            text = ""
            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": "thinking...", "thought": True}, {"text": '{"ta": "சரி"}'}]}}]}
        real = llm.requests.post
        llm.requests.post = lambda *a, **k: R()
        try:
            self.assertEqual('{"ta": "சரி"}', llm._gemma("gemma-4-26b-a4b-it", "s", "u", "k"))
        finally:
            llm.requests.post = real

    def test_groq_retries_shorter_prompt_on_413(self):
        import llm
        sent = []
        class R:
            def __init__(self, code): self.status_code, self.text = code, "Request too large"
            def json(self): return {"choices": [{"message": {"content": "{}"}}]}
        def post(url, headers=None, json=None, timeout=None):
            sent.append(json["messages"][1]["content"])
            return R(413 if len(sent) == 1 else 200)
        real = llm.requests.post
        llm.requests.post = post
        try:
            llm._groq("m", "rules", "EXAMPLE ARTICLE: long example\n\nTODAY (IST): 30 Oct\nARTICLE: news", "k")
        finally:
            llm.requests.post = real
        self.assertEqual(2, len(sent))
        self.assertTrue(sent[1].startswith("TODAY (IST)") and "EXAMPLE" not in sent[1])

    def test_empty_answer_is_explained(self):
        import llm
        class R:
            status_code = 200
            def json(self):
                return {"choices": [{"finish_reason": "length", "message": {"content": None, "reasoning_content": "x" * 50}}]}
        old = llm.requests.post
        llm.requests.post = lambda *a, **k: R()
        try:
            with self.assertRaisesRegex(RuntimeError, "empty answer .*length"):
                llm._sarvam("sarvam-105b", "s", "u", "k")
        finally:
            llm.requests.post = old


class SameEventShortScripts(unittest.TestCase):
    """30 Oct RN-214 = RN-209: the Salem-road poultry-feed godown fire from two outlets, short scripts, 8 shared rare words.
    The poster picked RN-214 eight times and its last check refused it every time (same news on Instagram)"""
    A = ("நாமக்கல்லில் கோழித்தீவன குடோனில் திடீர் தீ விபத்து ஏற்பட்டது. நாமக்கல்-சேலம் சாலையில் கண்ணன் என்பவருக்குச் சொந்தமான குடோன் உள்ளது. "
         "கோழித்தீவன மூலப்பொருள் மூட்டைகள் அடுக்கி வைக்கப்பட்டிருந்த குடோனில் புகை வந்தது. தகவல் அறிந்த நாமக்கல் தீயணைப்புத் துறையினர் "
         "விரைந்து சென்று தீயை அணைத்தனர். இந்த தீ விபத்தில் 10 மூட்டைகள் மட்டும் சேதமடைந்தன.")
    B = ("நாமக்கல் சேலம் சாலை சுவாமி நகரில் கோழித்தீவன குடோனில் தீ விபத்து ஏற்பட்டது. இதில் ரூ.5 லட்சம் மதிப்புள்ள பொருட்கள் எரிந்து நாசமடைந்தன. "
         "கண்ணன் (48 வயது) என்பவர் இந்தக் குடோனை நடத்தி வருகிறார். இங்கு கோழித்தீவன மூலப்பொருட்கள் சேகரித்து வைக்கப்பட்டிருந்தன. "
         "தகவல் அறிந்து தீயணைப்பு வீரர்கள் சம்பவ இடத்திற்கு வந்தனர். பின்னர் தீயணைப்பு வீரர்கள் தீயை அணைத்தனர்.")
    OTHER = ["மோகனூர் சாலையில் புதிய பேருந்து நிழற்குடை திறப்பு விழா நடைபெற்றது ஊராட்சி தலைவர் திறந்து வைத்தார் பயணிகள் மகிழ்ச்சி",
             "ராசிபுரம் உழவர் சந்தையில் தக்காளி வரத்து அதிகரிப்பு விலை சரிவு விவசாயிகள் கவலை வியாபாரிகள் தகவல்",
             "கொல்லிமலை அரப்பளீஸ்வரர் கோவிலில் ஐப்பசி திருவிழா கொடியேற்றம் பக்தர்கள் திரளாக பங்கேற்பு சிறப்பு பூஜை"]

    def test_short_reports_of_one_event(self):
        self.assertTrue(fr.same_event(self.A, self.B, fr.event_df([self.A, self.B] + self.OTHER * 3)))

    def test_writer_sees_stories_of_its_own_round(self):
        today = datetime.datetime.now(IST).strftime("%d %b %Y, %H:%M")
        recent = [{"story_id": "a story filed this round", "researched": today, "reel_script": self.A}] + \
                 [{"story_id": f"RN-{i}", "researched": today, "reel_script": t} for i, t in enumerate(self.OTHER * 3)]
        self.assertTrue(collect.same_event_filed({"title": "குடோனில் தீ", "text": self.B, "published": TODAY.isoformat()}, recent))


class PowerCutRules(unittest.TestCase):
    """owner 30 Oct (Coimbatore): power-cut news of the whole district is never skipped - judged by the day of the CUT, never held back
    by a daily cap, and its reel may run to 88 s (every area read out) while every other reel stays at 60 s / 105 words"""
    YESTERDAY = (datetime.datetime.now(IST) - datetime.timedelta(days=1)).isoformat()

    def test_power_cut_is_found(self):
        for h in ("பொள்ளாச்சியில் நாளை மின் தடை", "சூலூரில் நாளை மின்தடை", "மேட்டுப்பாளையத்தில் மின் நிறுத்தம்", "Kovai power shutdown tomorrow"):
            self.assertTrue(fr.is_power_cut(h), h)
        self.assertFalse(fr.is_power_cut("கோவையில் 47 ஆயிரம் தெரு நாய்களுக்கு கருத்தடை"))
        self.assertFalse(fr.is_power_cut("டாஸ்மாக் கடைகள் மூடல்", "TASMAC shops shutdown tomorrow"))      # a shop shutdown is not a power cut

    def test_tomorrow_notice_of_yesterday_is_todays_cut(self):
        self.assertTrue(fr.power_cut_ahead("பொள்ளாச்சியில் நாளை மின் தடை", self.YESTERDAY))
        two_days = (datetime.datetime.now(IST) - datetime.timedelta(days=2)).isoformat()
        self.assertFalse(fr.power_cut_ahead("பொள்ளாச்சியில் நாளை மின் தடை", two_days))      # that cut was yesterday
        self.assertFalse(fr.power_cut_ahead("கோவையில் நாளை கனமழை", self.YESTERDAY))         # not a power cut: the today-only rule stays

    def test_cut_date_in_headline_decides(self):
        mon = ["ஜனவரி", "பிப்ரவரி", "மார்ச்", "ஏப்ரல்", "மே", "ஜூன்", "ஜூலை", "ஆகஸ்ட்", "செப்டம்பர்", "அக்டோபர்", "நவம்பர்", "டிசம்பர்"]
        d = lambda k: TODAY + datetime.timedelta(days=k)
        self.assertTrue(fr.power_cut_ahead(f"சூலூரில் {d(0).day} {mon[d(0).month - 1]} மின் தடை", self.YESTERDAY))
        self.assertFalse(fr.power_cut_ahead(f"சூலூரில் {d(-1).day} {mon[d(-1).month - 1]} மின் தடை", self.YESTERDAY))
        two_days = (datetime.datetime.now(IST) - datetime.timedelta(days=2)).isoformat()
        self.assertTrue(fr.power_cut_ahead(f"{d(0):%d.%m.%y} கோவையில் இங்கெல்லாம் மின்தடை", two_days))      # 'நாளை 29.10.26' style (Covai Mail, 28 Oct)
        self.assertTrue(fr.power_cut_ahead(f"முக்கிய இடங்களில் ({d(1):%d.%m.%Y}) மின்தடை அறிவிப்பு", two_days))
        self.assertFalse(fr.power_cut_ahead(f"நாளை {d(-1):%d.%m.%y} கோவையில் மின்தடை", two_days))      # that cut was yesterday
        self.assertFalse(fr.power_cut_ahead("மின் தடை: ரூ.2.50 லட்சம் இழப்பு", two_days))      # an amount is not a date

    def test_posting_keeps_yesterdays_notice_for_today(self):
        old = os.environ.get("POST_MAX_AGE_DAYS")
        os.environ["POST_MAX_AGE_DAYS"] = "0"
        try:
            row = {"headline_ta": "பொள்ளாச்சியில் நாளை மின் தடை", "headline_en": "Pollachi power cut tomorrow", "published": self.YESTERDAY}
            self.assertFalse(post.skip_reason(row).startswith("stale: published"))
            row = {"headline_ta": "கோவையில் தெரு நாய்களுக்கு கருத்தடை", "headline_en": "Stray dogs", "published": self.YESTERDAY}
            self.assertTrue(post.skip_reason(row).startswith("stale: published"))      # every other story: published today only
        finally:
            os.environ.pop("POST_MAX_AGE_DAYS") if old is None else os.environ.__setitem__("POST_MAX_AGE_DAYS", old)

    def test_power_cut_found_by_headline_is_urgent(self):
        self.assertTrue(post.is_urgent({"headline_ta": "சூலூரில் நாளை மின்தடை", "category": "Civic Issues", "importance": "Medium"}))
        self.assertFalse(post.is_urgent({"headline_ta": "கோவையில் விழிப்புணர்வு பேரணி", "category": "Health", "importance": "Medium"}))

    def test_power_cut_reel_limits(self):
        c = json.loads((ROOT / "poster" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(88, c["power_cut"]["max_seconds"])      # under verify.py's 90 s check
        self.assertEqual(160, c["power_cut"]["script_max_words"])
        ns = from_file(ROOT / "reel" / "reel4.py", {"max_seconds"})
        self.assertEqual(88, ns["max_seconds"]({"cat": "மின் தடை", "mini": "பொள்ளாச்சியில் நாளை மின் தடை", "hook": ["", ""]}))
        self.assertEqual(88, ns["max_seconds"]({"cat": "Civic Issues", "mini": "சூலூரில் நாளை மின்தடை", "hook": ["", ""]}))
        self.assertEqual(60, ns["max_seconds"]({"cat": "Crime & Safety", "mini": "கோவையில் திருட்டு: 2 பேர் கைது", "hook": ["", ""]}))
        self.assertEqual(60, ns["max_seconds"]())

    def test_power_cut_script_may_be_longer(self):
        import validate
        ex = json.loads((ROOT / "research_free" / "examples.json").read_text(encoding="utf-8"))
        pc = dict(next(e["output"] for e in ex if fr.is_power_cut(e["output"]["tamil_headline"])))
        other = dict(ex[1]["output"])
        art = " ".join(f"சொல்{i}" for i in range(300))
        for d in (pc, other):
            d["reel_script"] = " ".join(["தகவல்"] * 140) + " " + validate.LAST
        words = lambda d: [x for x in validate.validate(d, art) if x.startswith("reel_script has")]
        self.assertFalse(words(pc))      # 140 words + every area: allowed for a power cut
        self.assertTrue(words(other))    # 140 words: too long for any other reel (105)
        pc["reel_script"] = " ".join(["தகவல்"] * 90) + " " + validate.LAST
        self.assertFalse(words(pc))      # a short notice is not forced longer: the minimum stays the normal one


class NoRepost(unittest.TestCase):
    """owner 30 Oct (Coimbatore): already posted news is never posted again. The same power cut comes from several outlets in other
    words ('நாளை காளப்பட்டியில் மின் தடை' posted 29 Oct night; 'காளப்பட்டி பகுதியில் இன்று மின் தடை' next morning) and the headline
    check missed it; the posted-script lookup lost 21 of 46 scripts (RN-x.json hid RN-x_coimbatore_text.json)"""
    NOW = datetime.datetime.now(IST)
    POSTED = "கோவை காளப்பட்டியில் நாளை மின் தடை: காலை 9 – மாலை 5 மணி வரை"
    FILED_YESTERDAY = (NOW - datetime.timedelta(days=1)).strftime("%d %b %Y, 20:00")

    def test_same_power_cut_in_other_words(self):
        today = self.NOW.isoformat()
        for h in ("நாளைய மின்தடை: காளப்பட்டி துணை மின் நிலையம்", "காளப்பட்டி பகுதியில் இன்று மின் தடை",
                  "காளப்பட்டி, வீரியம்பாளையம், நேரு நகர் பகுதிகளில் இன்று மின்தடை"):
            self.assertTrue(fr.same_power_cut(self.POSTED, self.FILED_YESTERDAY, h, today), h)

    def test_other_power_cut_is_never_a_false_duplicate(self):
        today = self.NOW.isoformat()
        for h in ("சூலூரில் இன்று மின் தடை", "நாளைய மின்தடை: கோயம்புத்தூர்", "காந்தி நகர் பகுதியில் இன்று மின் தடை"):
            self.assertFalse(fr.same_power_cut(self.POSTED, self.FILED_YESTERDAY, h, today), h)
        next_week = (self.NOW + datetime.timedelta(days=7)).strftime("%d.%m.%Y")
        self.assertFalse(fr.same_power_cut(self.POSTED, self.FILED_YESTERDAY, f"காளப்பட்டியில் {next_week} மின் தடை", today))

    def test_posting_skips_the_same_power_cut(self):
        old = post.ALL_ROWS
        post.ALL_ROWS = [{"story_id": "RN-61", "headline_ta": self.POSTED, "researched": self.FILED_YESTERDAY, "post_status": "Posted"}]
        try:
            row = {"story_id": "RN-70", "headline_ta": "கோவை காளப்பட்டி பகுதியில் இன்று மின் தடை", "published": self.NOW.isoformat()}
            self.assertEqual("duplicate of RN-61", post.skip_reason(row))
            row = {"story_id": "RN-71", "headline_ta": "கோவை சூலூரில் இன்று மின் தடை", "published": self.NOW.isoformat()}
            self.assertFalse(post.skip_reason(row).startswith("duplicate"))
        finally:
            post.ALL_ROWS = old

    def test_instagram_feed_check_finds_the_same_power_cut(self):
        old = dict(post.IG_RECENT)
        post.IG_RECENT["coimbatore"] = [((self.NOW - datetime.timedelta(hours=10)).isoformat(), "⚡ " + self.POSTED + "\n\nமுழு விவரம்")]
        try:
            self.assertTrue(post.ig_duplicate({"headline_ta": "காளப்பட்டி பகுதியில் இன்று மின் தடை", "published": self.NOW.isoformat()}, "coimbatore"))
            self.assertFalse(post.ig_duplicate({"headline_ta": "சூலூரில் இன்று மின் தடை", "published": self.NOW.isoformat()}, "coimbatore"))
        finally:
            post.IG_RECENT.clear(); post.IG_RECENT.update(old)

    def test_writer_skips_the_same_power_cut(self):
        recent = [{"story_id": "RN-61", "headline_ta": self.POSTED, "researched": self.FILED_YESTERDAY, "source": "https://a"}]
        art = {"url": "https://b", "title": "காளப்பட்டி பகுதியில் இன்று மின் தடை", "published": self.NOW.isoformat()}
        self.assertTrue(collect.is_dup(art, {"tamil_headline": art["title"]}, recent))
        art = {"url": "https://c", "title": "சூலூரில் இன்று மின் தடை", "published": self.NOW.isoformat()}
        self.assertFalse(collect.is_dup(art, {"tamil_headline": art["title"]}, recent))

    def test_posted_script_is_not_hidden_by_the_media_file(self):
        old_cache, old_scripts = post.CACHE, post._SCRIPTS
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "RN-999.json").write_text(json.dumps({"reel": "x"}), encoding="utf-8")
            (Path(d) / "RN-999_coimbatore_text.json").write_text(json.dumps({"reel_script": "காளப்பட்டியில் மின் தடை."}), encoding="utf-8")
            post.CACHE, post._SCRIPTS = Path(d), None
            try:
                self.assertEqual("காளப்பட்டியில் மின் தடை.", post.script_of({"story_id": "RN-999"}))
                self.assertEqual("காளப்பட்டியில் மின் தடை.", collect._filed_script({"story_id": "RN-999"}))      # the writer's same-event check
            finally:
                post.CACHE, post._SCRIPTS = old_cache, old_scripts


class RefusedNotWrittenAgain(unittest.TestCase):
    """30 Oct: drafts refused as 'not Coimbatore city news (Thondamuthur / Periyanaickenpalayam)' were written again 4-5 times - the
    refusal looked like a model failure, so the story went back to the queue every round (a free-model call each time); and the
    'notcity' verdict of the collection check did not stop the next check either"""
    CITY = "all free models failed: not Coimbatore city news (Thondamuthur)"

    def blocked(self, st):
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        verdicts = re.search(r'st\.get\("s"\) in \(([^)]*)\)', src).group(1)      # the 'checked earlier' rule at the start of every round
        return st.get("s") is not None and f'"{st["s"]}"' in verdicts

    def test_outside_city_gets_one_more_try_then_stops(self):
        st = {"n": 1}
        self.assertEqual("", collect.refusal_verdict(self.CITY, st))
        st["s"] = collect.refusal_verdict(self.CITY, st)
        self.assertEqual("notcity", st["s"])
        self.assertTrue(self.blocked(st))

    def test_collection_notcity_verdict_now_stops_the_next_check(self):
        self.assertTrue(self.blocked({"s": "notcity"}))

    def test_date_old_event_and_duplicate_stop_at_once(self):
        for why, v in (("stale: announced date 28 Oct has passed", "old"), ("old event: the story is about 12 Mar 2024", "old"),
                       ("duplicate after write", "dup")):
            self.assertEqual(v, collect.refusal_verdict(why, {}), why)
            self.assertTrue(self.blocked({"s": v}))

    def test_real_model_failures_are_always_tried_again(self):
        st = {}
        for _ in range(5):
            self.assertEqual("", collect.refusal_verdict("all free models failed: no usable answer from the models", st))
            self.assertEqual("", collect.refusal_verdict("all free models failed: groq 429: rate limit", st))
            self.assertEqual("", collect.refusal_verdict("bad draft: 'scenes'", st))

    def test_power_cut_is_never_refused_as_outside_the_city(self):
        self.assertEqual("", allnews.outside_city("பெரியநாயக்கன்பாளையத்தில் நாளை மின் தடை"))

    def test_every_refusal_of_file_story_is_known(self):
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        body = src[src.index("def file_story("):src.index("\ndef ", src.index("def file_story(") + 10)]
        known = [k for k, _ in collect.REFUSED_FINAL + collect.REFUSED_ONCE_MORE] + ["all free models failed", "bad draft"]
        for r in re.findall(r'return None, f?"([^"{:]+)', body):
            self.assertTrue(any(r.startswith(k.rstrip(":")) or k.startswith(r) for k in known), r)


class OnlyWatchedNews(unittest.TestCase):
    """owner 31 Oct: Coimbatore 360 writes only news Instagram users watch. Posted 30-31 Oct although nobody watches such posts:
    recipes, health / building tips, an editorial, awareness days, awards, trophies, a tender, a walkout, a tribute"""
    LOW = [("சுவையான ஆப்பிள் ரப்டி தயாரிப்பது எப்படி?", ""),                                  # RN-91 recipe
           ("ஆந்திரா ஸ்டைல் காரசாரமான மட்டன் கறி", "https://www.dinamalar.com/news/x/andhra-style-spicy-mutton-curry/4363834"),
           ("அடிக்கடி வயிறு உப்புசம் ஏற்பட 6 காரணங்கள்", ""),                                   # RN-89 health tips
           ("கான்கிரீட்டின் தரம்: M20, M25 எண்கள் எதைக் குறிக்கின்றன?", ""),                     # RN-75 building tips
           ("இனி தமிழ்நாட்டுக்கு நிறைய விமானங்கள் வந்து போகும்", "https://www.dailythanthi.com/others/thalayangam/x"),      # RN-84 editorial
           ("உலக பக்கவாத தினத்தில் கேஎம்சிஎச் மருத்துவமனை நீல நிறத்தில் ஒளிர்ந்தது", ""),          # RN-74
           ("கோவை எக்கி பம்ப்ஸுக்கு சர்வதேச சிறப்பு அங்கீகார விருது", ""),                        # RN-34
           ("நீலாம்பூர் – மதுக்கரை பைபாஸ்: பராமரிப்புக்கு டெண்டர் அழைப்பு", ""),                  # RN-18
           ("கோவை இருகூரில் தேவர் சிலைக்கு கனிமொழி சந்தோஷ் மரியாதை", ""),                         # RN-70
           ("சர்வதேச கராத்தே போட்டிகளில் கோவை அணிக்கு சாம்பியன் பட்டம்; 19 பதக்கங்கள்", "")]       # RN-68
    KEEP = ["இடையர்பாளையத்தில் 2.2 டன் ரேஷன் அரிசி பறிமுதல்; ஒருவர் கைது", "கற்பகம் ஜங்ஷனில் 3 ஆண்டுகளில் 23 விபத்து; 5 பேர் உயிரிழப்பு",
            "குடிநீருக்கு 20 மடங்கு கூடுதல் கட்டணம்: சூயஸ் நிறுவனத்தால் அதிர்ச்சி", "ரூ.11.15 கோடி போலி ஜிஎஸ்டி ரசீது மோசடி: கோவை தொழிலதிபருக்கு 5 ஆண்டுகள் சிறை",
            "தீபாவளி கூட்ட நெரிசல்: கோவை மாநகரில் 1,000 போலீசார் பாதுகாப்புப் பணியில்", "கோவை முன்சிப் கோர்ட்கள் டாடாபாத்துக்கு மாற்றம்",
            "நவம்பர் 2ல் கோவை, நீலகிரியில் ஓரிரு இடங்களில் கனமழை வாய்ப்பு", "கோவையில் 47 ஆயிரம் தெரு நாய்களுக்கு கருத்தடை அறுவை சிகிச்சை",
            "கோவை இருகூரில் தேவர் ஜெயந்தி விழாவில் பட்டாசு தீப்பொறியால் பந்தல் தீப்பற்றியது", "நவம்பர் 1ஆம் தேதி கோவையில் குரூப் 2 தேர்வு: 73 மையங்களில் நடைபெறுகிறது",
            "தொண்டாமுத்தூரில் காட்டு யானை புகுந்து பயிர்கள் சேதம்", "சூலூர் துணை மின் நிலையத்தில் விழிப்புணர்வு நிகழ்ச்சி: நாளை மின் தடை",
            "கவுண்டம்பாளையத்தில் குடிநீர் பிரச்சினைக்கு தீர்வு காண கோரிக்கை"]

    def test_unwatched_types_are_not_written(self):
        for title, url in self.LOW:
            self.assertTrue(collect.low_interest(title, url), title)

    def test_real_news_is_always_written(self):
        for title in self.KEEP:
            self.assertEqual("", collect.low_interest(title), title)

    def test_switch_off_writes_everything(self):
        real = collect._selection
        collect._selection = lambda: {"skip_low_interest": False}
        try:
            self.assertEqual("", collect.low_interest("சுவையான ஆப்பிள் ரப்டி தயாரிப்பது எப்படி?"))
        finally:
            collect._selection = real

    def test_low_interest_is_final_and_checked_before_any_model_call(self):
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        prep = src[src.index("    def prepare("):]
        self.assertLess(prep.index("low_interest(art[\"title\"]"), prep.index("ask_json") if "ask_json" in prep else prep.index("run."))
        self.assertIn('"not written: " + low, "s": "notext"', src)      # notext = checked earlier, never opened again

    def test_writer_has_no_schedule_of_its_own(self):      # owner 31 Oct: the rounds write the stories (top 3 each)
        wf = (ROOT / ".github" / "workflows" / "write_stories.yml").read_text(encoding="utf-8")
        self.assertNotIn("schedule:", wf)


class RoundsTopThree(unittest.TestCase):
    """owner 31 Oct: 10 rounds a day (IST 04:00 ... 22:00, every 2 hours). Each round collects today's WHOLE-district news, compares it
    with today's earlier collected news that was not posted yet, writes the TOP 3 by expected views (every power cut on top) and posts
    them at once. A new day starts fresh. A slow or failed story never holds the next round."""
    WF = ROOT / ".github" / "workflows"

    def test_rounds_at_the_owners_times(self):
        cron = re.search(r'cron: "(\d+) ([\d,]+) \* \* \*"', (self.WF / "research_free.yml").read_text(encoding="utf-8"))
        times = sorted(((int(h) * 60 + int(cron.group(1)) + 330) % 1440) // 60 for h in cron.group(2).split(","))
        self.assertEqual([4, 6, 8, 10, 12, 14, 16, 18, 20, 22], times)      # UTC + 5:30 = IST, on the hour
        self.assertEqual(0, (int(cron.group(1)) + 30) % 60)

    def test_each_round_writes_top_3_of_the_whole_district(self):
        wf = (self.WF / "research_free.yml").read_text(encoding="utf-8")
        for s in ("COLLECT_MODE: both", 'MAX_STORIES: "3"', 'CITY_ONLY: "0"', 'FRESH_DAYS: "1"'):
            self.assertIn(s, wf)
        self.assertIn('CITY_ONLY: "0"', (self.WF / "post.yml").read_text(encoding="utf-8"))

    def test_power_cuts_are_written_on_top_of_the_3(self):
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        self.assertIn("target = {AREA: MAX_STORIES + len(pcs)}", src)
        self.assertIn("queues[AREA] = pcs + [q for q in queues[AREA] if q not in pcs]", src)

    def test_leftovers_compete_next_round_and_a_new_day_starts_fresh(self):
        old = collect.QUEUE
        with tempfile.TemporaryDirectory() as d:
            now = datetime.datetime.now(IST)
            collect.QUEUE = Path(d) / "queue.json"
            collect.QUEUE.write_text(json.dumps([
                {"key": "a", "url": "u1", "title": "இன்று காலை சேகரித்தது", "queued_at": now.replace(hour=0, minute=5).isoformat()},
                {"key": "b", "url": "u2", "title": "நேற்று சேகரித்தது", "queued_at": (now - datetime.timedelta(days=1)).isoformat()}]), encoding="utf-8")
            try:
                self.assertEqual(["a"], [q["key"] for q in collect.load_queue()])
            finally:
                collect.QUEUE = old
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        self.assertIn('or MODE == "both") and allnews.local_ok', src)      # a round's unwritten news is kept for the next round

    def test_city_story_wins_a_tie(self):
        n = {"title": "திருட்டு வழக்கில் 2 பேர் கைது", "snippet": "", "mentions": 1, "published": ""}
        city = dict(n, title="காந்திபுரத்தில் திருட்டு வழக்கில் 2 பேர் கைது")
        self.assertEqual(collect.score(n) + 1, collect.score(city))

    def test_rain_warning_ranks_just_below_power_cut(self):
        self.assertGreaterEqual(collect.interest({"title": "கோவையில் கனமழை எச்சரிக்கை", "text": ""}), 10)
        self.assertGreater(collect.interest({"title": "நாளை மின் தடை", "text": ""}), collect.interest({"title": "கோவில் திருவிழா", "text": ""}))

    def test_no_round_waits_for_a_writer_chain(self):
        src = (ROOT / "research_free" / "collect.py").read_text(encoding="utf-8")
        self.assertIn('if left and MODE == "collect":', src)      # a writer run never restarts itself
        self.assertNotIn("write_stories.yml && echo", (self.WF / "post.yml").read_text(encoding="utf-8"))      # watchdog restarts rounds only

    def test_every_python_snippet_in_the_workflows_compiles(self):
        # 31 Oct: a '#' comment inside the watchdog's print(...) broke it - the 03:59 UTC posting run failed (SyntaxError)
        for f in sorted(self.WF.glob("*.yml")):
            for block in re.findall(r"python3? - <<'PY'[^\n]*\n(.*?)\n\s*PY\n", f.read_text(encoding="utf-8"), re.S):
                lines = block.split("\n")
                pad = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
                compile("\n".join(l[pad:] for l in lines), f.name, "exec")
