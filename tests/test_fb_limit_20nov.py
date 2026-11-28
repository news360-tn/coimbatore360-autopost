"""owner 20 Nov: Facebook gets 15-20 news a day per page (every news, 45 min apart); the 368 pause stays"""
import importlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "poster"))


class FacebookLimit(unittest.TestCase):
    def test_settings(self):
        import facebook
        importlib.reload(facebook)
        self.assertEqual(facebook.TOP_PER_DAY, 25)      # owner 21 Nov: every news on Facebook too
        self.assertEqual(facebook.GAP_MIN, 30)      # owner 21 Nov: a sooner news waits
        self.assertFalse(facebook.TOP_ONLY)
        self.assertLess(facebook.TOP_PER_DAY, facebook.REEL_CAP)      # under Facebook's 30 API reels a day
        ok, why = facebook.top_news({"urgent": False, "topic": "education", "weight": -0.5, "best": False})
        self.assertTrue(ok, why)
        self.assertEqual(facebook.PAUSE_HOURS, 24)      # owner 28 Nov: a block with no stated time waits 24 hours again (2 hours kept five pages blocked)

    def test_a_368_block_pauses_the_page_for_24_hours(self):      # owner 28 Nov: with 2 hours the page tried, and was refused, every 2 hours
        import json
        import tempfile
        from unittest import mock
        import facebook
        why = ("Facebook video_reels: 400 368/1390008 We limit how often you can post, comment or do other things in a given amount of time "
               "in order to help protect the community from spam. You can try again later. Learn More")

        def hours_paused(folder):
            until = facebook.dt.datetime.fromisoformat(json.loads((Path(folder) / "_paused-salem.json").read_text(encoding="utf-8"))["until"])
            return (until - facebook._now()).total_seconds() / 3600

        with tempfile.TemporaryDirectory() as d, mock.patch.object(facebook, "STATE", Path(d)):
            facebook._pause("salem", why)
            self.assertAlmostEqual(hours_paused(d), 24, delta=0.05)
            self.assertIn("paused until", facebook.paused("salem"))      # nothing is tried while the pause runs
            facebook._pause("salem", "You're temporarily blocked. Please try again in 3 hours.")
            self.assertAlmostEqual(hours_paused(d), 3, delta=0.05)      # a time Facebook itself states still wins


if __name__ == "__main__":
    unittest.main()
