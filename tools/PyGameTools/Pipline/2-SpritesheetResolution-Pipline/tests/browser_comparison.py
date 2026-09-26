"""Optional offline Chromium tests: python tests/browser_comparison.py -v.

Requires Playwright and its Chromium installation in the test environment.
The pipeline and generated HTML themselves require neither dependency.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from playwright.sync_api import sync_playwright

from test_cli_modes import DIRECTIONS, SCRIPTS, make_pose


class BrowserComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pygraphics-browser-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        make_pose(cls.root, "Jump # 100%", ((4, 2), (4, 4)), DIRECTIONS, (64, 48))
        make_pose(cls.root, "Walk", ((4, 2), (7, 7)), DIRECTIONS, (64, 48))
        subprocess.run([sys.executable, str(SCRIPTS / "PyPiplineStart-SpritesheetResolution.py"), "-s-a", str(cls.root)],
                       check=True, capture_output=True, timeout=90)
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1440, "height": 1100})
        self.addCleanup(self.page.close)
        self.errors = []
        self.requests = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("request", lambda request: self.requests.append(request.url))
        self.page.goto((self.root / "positionsvergleich.html").as_uri())
        self.ready()

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertFalse([url for url in self.requests if url.startswith(("http:", "https:"))])

    def ready(self):
        self.page.wait_for_selector('body[data-ready="true"]')

    def slider(self, selector, value):
        self.page.locator(selector).evaluate(
            "(input, value) => { input.value = value; input.dispatchEvent(new Event('input', {bubbles:true})); }",
            str(value))

    def centers(self):
        return self.page.locator(".sprite:not([hidden])").evaluate_all(
            "nodes => nodes.map(n => {const r=n.getBoundingClientRect(); return r.x+r.width/2;})")

    def test_overlay_spread_native_size_and_visibility(self):
        self.assertEqual(self.page.locator(".sprite:not([hidden]) canvas").count(), 8)
        centers = self.centers()
        self.assertLess(max(centers) - min(centers), 0.1)
        self.slider("#spread", 100)
        centers = self.centers()
        self.assertGreater(max(centers) - min(centers), 500)
        self.slider("#spread", 0)
        centers = self.centers()
        self.assertLess(max(centers) - min(centers), 0.1)
        self.page.select_option("#units", "native")
        widths = self.page.locator(".sprite:not([hidden])").evaluate_all(
            "nodes => nodes.map(n => n.getBoundingClientRect().width)")
        self.assertGreater(len(set(widths)), 1)
        self.page.click("#hideAll")
        self.assertTrue(self.page.locator("#empty").is_visible())
        self.page.click("#showAll")
        self.assertEqual(self.page.locator(".sprite:not([hidden])").count(), 8)

    def test_two_poses_directions_timeline_and_original_gifs(self):
        self.page.select_option("#poseB", "1")
        self.ready()
        self.assertEqual(self.page.locator(".sprite:not([hidden]) canvas").count(), 16)
        self.assertEqual(self.page.locator("#frame").get_attribute("max"), "48")
        for direction in DIRECTIONS:
            self.page.get_by_role("button", name=direction, exact=True).click()
            self.ready()
            self.assertIn(direction, self.page.locator("#status").inner_text())
            self.assertEqual(self.page.locator(".sprite:not([hidden]) canvas").count(), 16)
        self.page.select_option("#sync", "frame")
        self.slider("#frame", 12)
        values = self.page.locator("#tracks tr td:nth-child(4)").all_text_contents()
        self.assertIn("5 / 8", values)
        self.assertIn("13 / 16", values)
        self.assertIn("13 / 49", values)
        self.page.select_option("#fps", "24")
        self.page.click("#play")
        self.page.wait_for_function("document.querySelector('#frame').value !== '12'")
        self.page.click("#play")
        self.page.select_option("#source", "gif")
        self.ready()
        self.assertEqual(self.page.locator(".sprite:not([hidden]) img").count(), 16)
        self.assertTrue(self.page.locator("#fps").is_disabled())
        self.assertTrue(self.page.locator("#play").is_disabled())
        self.slider("#spread", 100)
        self.assertGreater(max(self.centers()) - min(self.centers()), 1000)
        self.page.select_option("#source", "sheet")
        self.ready()
        self.assertFalse(self.page.locator("#fps").is_disabled())

    def test_filters_reference_measurements_and_missing_files(self):
        self.page.locator('#variants input[value="comic_high"]').check()
        self.ready()
        self.assertEqual(self.page.locator(".sprite:not([hidden])").count(), 10)
        self.page.select_option("#reference", "0:0:comic_high")
        self.assertEqual(self.page.locator("#tracks tr").first.locator("td").nth(4).inner_text(), "0.0 / 0.0")
        self.page.locator('#layouts input[value="4×4 · 16 Frames"]').uncheck()
        self.ready()
        self.assertEqual(self.page.locator(".sprite:not([hidden])").count(), 5)
        source = next((self.root / "Jump # 100%/comic_mid").glob("spritesheet-fram8/*.png"))
        backup = source.read_bytes()
        source.unlink()
        try:
            self.page.reload()
            self.ready()
            self.assertIn("nicht lesbar", self.page.locator("#tracks").inner_text())
        finally:
            source.write_bytes(backup)

    def test_gif_only_resolution_page_and_mobile_layout(self):
        target = self.root / "GIFs ohne PNGs"
        shutil.copytree(self.root / "Walk", target)
        for path in target.rglob("*.png"):
            path.unlink()
        try:
            subprocess.run([sys.executable, str(SCRIPTS / "PyPiplineStart-SpritesheetResolution.py"), str(target), "--html-only"],
                           capture_output=True, check=True, timeout=60)
            self.page.goto((target / "aufloesungsvergleich.html").as_uri())
            self.page.wait_for_selector('body[data-ready="true"]')
            self.assertEqual(self.page.locator(".stage img").count(), 4)
            self.assertTrue(self.page.locator("#fps").is_disabled())
            self.page.goto((self.root / "positionsvergleich.html").as_uri())
            self.ready()
            self.page.set_viewport_size({"width": 390, "height": 844})
            self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 391)
        finally:
            shutil.rmtree(target)


if __name__ == "__main__":
    unittest.main()
