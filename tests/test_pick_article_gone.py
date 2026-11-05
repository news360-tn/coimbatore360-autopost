import sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research_free"))
import pick


class ArticleGone(unittest.TestCase):
    """5 Nov: a picked article the paper deleted (404) is skipped, not waited on for 2.5 hours; a timeout is not 'gone'"""

    def resp(self, code):
        return mock.Mock(status_code=code)

    def test_404_and_410_are_gone(self):
        for c in (404, 410):
            with mock.patch("requests.get", return_value=self.resp(c)):
                self.assertTrue(pick._article_gone("https://x/a"))

    def test_200_500_timeout_are_not_gone(self):
        for c in (200, 500, 503):
            with mock.patch("requests.get", return_value=self.resp(c)):
                self.assertFalse(pick._article_gone("https://x/a"))
        import requests
        with mock.patch("requests.get", side_effect=requests.exceptions.ReadTimeout("slow")):
            self.assertFalse(pick._article_gone("https://x/a"))
        self.assertFalse(pick._article_gone(""))

    def test_verify_counts_gone_as_skipped(self):
        st = {"pool": {"A": {"url": "https://x/a", "title": "t"}}}
        with mock.patch.object(pick, "load_state", return_value=st), \
                mock.patch.object(pick, "current_round", return_value=("r", {"decided": {"ids": ["A"]}})), \
                mock.patch.object(pick, "bridge_get", return_value={"rows": []}), \
                mock.patch.object(pick, "_article_gone", return_value=True):
            self.assertEqual(pick.cmd_verify(), 0)
        with mock.patch.object(pick, "load_state", return_value=st), \
                mock.patch.object(pick, "current_round", return_value=("r", {"decided": {"ids": ["A"]}})), \
                mock.patch.object(pick, "bridge_get", return_value={"rows": []}), \
                mock.patch.object(pick, "_article_gone", return_value=False):
            self.assertEqual(pick.cmd_verify(), 3)


if __name__ == "__main__":
    unittest.main()
