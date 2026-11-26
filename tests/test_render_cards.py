import json
import datetime as dt
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import render_cards


class RenderCardsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(render_cards.DATA_FILE.read_text(encoding="utf-8"))
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_static_render_produces_img_safe_card_stack(self):
        paths = render_cards.render_cards(self.data, self.output_dir, static=True)
        self.assertEqual(len(paths), 9)
        for path in paths:
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            svg = path.read_text(encoding="utf-8")
            self.assertNotIn("<animate", svg)
            self.assertNotIn("animation:rise", svg)

    def test_animated_render_has_staggered_css_and_reduced_motion_fallback(self):
        paths = render_cards.render_cards(self.data, self.output_dir)
        first = paths[0].read_text(encoding="utf-8")
        last = paths[-1].read_text(encoding="utf-8")
        self.assertIn("@keyframes rise", first)
        self.assertIn("prefers-reduced-motion:reduce", first)
        self.assertIn("<animate", first)
        self.assertIn("3.36s both", last)

    def test_subsets_are_embedded_as_font_data_uris(self):
        paths = render_cards.render_cards(
            self.data, self.output_dir, static=True, fonts={"Manrope:100 900": "d09GRg=="}
        )
        self.assertIn("data:font/woff;base64,d09GRg==", paths[0].read_text(encoding="utf-8"))

    def test_metrics_include_streak_active_days_and_busiest_weekday(self):
        today = dt.date.today()
        days = [(today - dt.timedelta(days=1), 3), (today, 2)]

        metrics = render_cards.contribution_metrics(days)

        self.assertEqual(metrics["streak"], 2)
        self.assertEqual(metrics["active_days"], 2)
        self.assertEqual(metrics["busiest"], render_cards.WEEKDAYS[((today - dt.timedelta(days=1)).weekday() + 1) % 7])

    def test_font_subsetting_fails_clearly_when_pyftsubset_is_missing(self):
        with patch("render_cards.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "pyftsubset is required"):
                render_cards.subset_fonts("profile card")

    def test_busiest_weekday_is_blank_when_calendar_has_no_contributions(self):
        metrics = render_cards.contribution_metrics([(dt.date.today(), 0)])
        self.assertEqual(metrics["busiest"], "—")


if __name__ == "__main__":
    unittest.main()
