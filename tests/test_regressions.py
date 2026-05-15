import importlib.util
import pathlib
import sys
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from desktop_control import atspi, ocr
from desktop_control.element import Element, ElementSource
from desktop_control.finder import ElementFinder

SCRIPT_PATH = ROOT / "scripts" / "desktop.py"

_SPEC = importlib.util.spec_from_file_location("desktop_cli", SCRIPT_PATH)
desktop = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(desktop)


class CliValidationTests(unittest.TestCase):
    def test_click_rejects_partial_percent_coordinates(self):
        args = Namespace(
            right=False,
            middle=False,
            x_percent=0.5,
            y_percent=None,
            double=False,
            x=0,
            y=0,
            display=":10.0",
        )
        result = desktop.cmd_click(args)
        self.assertIn("error", result)
        self.assertIn("Both --x-percent and --y-percent", result["error"])

    def test_click_element_requires_selector(self):
        args = Namespace(
            name=None,
            role=None,
            app=None,
            right=False,
            double=False,
            verify=False,
            display=":10.0",
        )
        result = desktop.cmd_click_element(args)
        self.assertIn("error", result)
        self.assertIn("requires at least one selector", result["error"])

    def test_click_element_verify_requires_non_empty_text(self):
        fake_element = Element(
            name="",
            x=10,
            y=20,
            width=40,
            height=20,
            source=ElementSource.ATSPI,
            role_name="push button",
            states=["visible", "showing"],
            actions=["click"],
        )
        args = Namespace(
            name=None,
            role="button",
            app=None,
            right=False,
            double=False,
            verify=True,
            display=":10.0",
        )

        with patch.object(desktop, "ElementFinder") as finder_cls, patch.object(
            desktop.ocr, "is_available", return_value=True
        ):
            finder_cls.return_value.find.return_value = fake_element
            result = desktop.cmd_click_element(args)

        self.assertIn("error", result)
        self.assertIn("verification requires text", result["error"].lower())

    def test_wait_for_rejects_ambiguous_text_and_element_selectors(self):
        args = Namespace(
            name="Confirm",
            role=None,
            app=None,
            text="Confirm",
            exact=False,
            gone=False,
            timeout=1.0,
            display=":10.0",
        )
        result = desktop.cmd_wait_for(args)
        self.assertIn("error", result)
        self.assertIn("either --text or element selectors", result["error"])

    def test_wait_for_requires_selectors(self):
        args = Namespace(
            name=None,
            role=None,
            app=None,
            text=None,
            exact=False,
            gone=False,
            timeout=1.0,
            display=":10.0",
        )
        result = desktop.cmd_wait_for(args)
        self.assertIn("error", result)
        self.assertIn("requires --text", result["error"])

    def test_wait_for_gone_text_uses_disappearance_path(self):
        calls = []

        class FakeWaiter:
            def wait_for_text(self, *args, **kwargs):
                raise AssertionError("wait_for_text should not be called for --gone")

            def wait_until_gone(self, **kwargs):
                calls.append(kwargs)
                return True

        args = Namespace(
            name=None,
            role=None,
            app=None,
            text="Loading",
            exact=True,
            gone=True,
            timeout=2.0,
            display=":10.0",
        )

        with patch.object(desktop, "Waiter", return_value=FakeWaiter()):
            result = desktop.cmd_wait_for(args)

        self.assertEqual(result["gone"], True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["text"], "Loading")
        self.assertEqual(calls[0]["exact"], True)

    def test_click_id_rejects_cache_when_screen_size_changed(self):
        fake_cache = SimpleNamespace(
            screen_size=(100, 100),
            check_screen_size=lambda _: False,
        )
        args = Namespace(
            element_id=1,
            right=False,
            double=False,
            display=":10.0",
        )

        with patch.object(desktop.element_cache, "is_cache_valid", return_value=True), patch.object(
            desktop.element_cache, "get_cache", return_value=fake_cache
        ), patch.object(desktop.xdotool, "get_screen_size", return_value=(200, 200)), patch.object(
            desktop.element_cache, "get_element"
        ) as get_element:
            result = desktop.cmd_click_id(args)

        self.assertIn("error", result)
        self.assertEqual(result["cache_valid"], False)
        self.assertEqual(result["expected_screen_size"]["width"], 100)
        self.assertEqual(result["current_screen_size"]["width"], 200)
        get_element.assert_not_called()


class CoreBehaviorTests(unittest.TestCase):
    def test_atspi_clickable_filter_accepts_press_action(self):
        elem = atspi.ATSPIElement(
            name="Submit",
            role="",
            role_name="push button",
            description="",
            x=0,
            y=0,
            width=10,
            height=10,
            states=["visible", "showing"],
            actions=["press"],
            app_name="Demo",
        )

        def fake_traverse_tree(*, app_filter=None, filter_fn=None):
            if filter_fn is None or filter_fn(elem):
                yield elem

        with patch.object(atspi, "traverse_tree", side_effect=fake_traverse_tree):
            results = atspi.find_elements(clickable_only=True, max_results=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Submit")

    def test_ocr_find_text_empty_query_returns_empty(self):
        with patch.object(ocr, "TESSERACT_AVAILABLE", True), patch.object(
            ocr, "ocr_image", side_effect=AssertionError("ocr_image should not be called")
        ):
            self.assertEqual(ocr.find_text(image=None, text="   "), [])

    def test_find_all_skips_ocr_when_atspi_finds_semantic_matches(self):
        atspi_elem = atspi.ATSPIElement(
            name="Confirm",
            role="",
            role_name="push button",
            description="",
            x=10,
            y=20,
            width=100,
            height=30,
            states=["visible", "showing", "enabled"],
            actions=["click"],
            app_name="Demo",
        )

        with patch.object(atspi, "is_available", return_value=True), patch.object(
            ocr, "is_available", return_value=True
        ), patch.object(atspi, "find_elements", return_value=[atspi_elem]) as find_elements, patch.object(
            ocr, "find_text", side_effect=AssertionError("OCR should be fallback-only when AT-SPI matched")
        ), patch.object(
            ElementFinder, "_get_screenshot", side_effect=AssertionError("Screenshot should not be captured")
        ):
            results = ElementFinder().find_all(name="Confirm", role="button")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Confirm")
        self.assertEqual(results[0].source, ElementSource.ATSPI)
        find_elements.assert_called_once()

    def test_find_all_still_uses_ocr_when_atspi_has_no_matches(self):
        ocr_match = ocr.OCRMatch(
            text="Confirm",
            x=10,
            y=20,
            width=100,
            height=30,
            confidence=92.0,
        )

        with patch.object(atspi, "is_available", return_value=True), patch.object(
            ocr, "is_available", return_value=True
        ), patch.object(atspi, "find_elements", return_value=[]), patch.object(
            ElementFinder, "_get_screenshot", return_value=object()
        ) as get_screenshot, patch.object(
            ocr, "find_text", return_value=[ocr_match]
        ) as find_text:
            results = ElementFinder().find_all(name="Confirm", role="button")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Confirm")
        self.assertEqual(results[0].source, ElementSource.OCR)
        get_screenshot.assert_called_once()
        find_text.assert_called_once()


if __name__ == "__main__":
    unittest.main()
