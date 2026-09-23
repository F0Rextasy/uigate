"""Contract tests for uigate. Run: python -m unittest discover -s tests -v

Pages are written to temp dirs and linted by the real CLI; the red example
must fail every objective rule with its exact measured value, and the
clean example must pass. A gate that needs the network is a gate that
flakes -- uigate never makes one.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "uigate")
RED = os.path.join(ROOT, "examples", "red", "index.html")
CLEAN = os.path.join(ROOT, "examples", "clean", "index.html")


def run_cli(*args):
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=ROOT)
    return proc.returncode, proc.stdout, proc.stderr


def write_page(tmp, body, name="page.html"):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    return path


def findings_json(*args):
    code, out, _ = run_cli(*args, "--format", "json")
    return code, json.loads(out)


def rule_map(data):
    rows = {}
    for finding in data["findings"]:
        rows.setdefault(finding["rule"], []).append(finding)
    return rows


CLEAN_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>t</title>
<style>
:root { --ink: #1a1a1a; --paper: #ffffff; }
body { color: var(--ink); background: var(--paper); font-size: 16px;
       font-family: "Bakery Sans", Georgia, serif; }
a:focus-visible { outline: 3px solid #0b5cad; }
</style></head>
<body><h1>Fresh bread every morning</h1>
<img src="a.png" alt="A sourdough loaf">
<button style="width: 48px; height: 48px;">Buy</button></body></html>
"""


def styled(body_css, extra=""):
    return ("<!DOCTYPE html><html><head><style>:focus-visible "
            "{ outline: 2px solid #000; }\n%s</style></head>"
            "<body>%s</body></html>" % (body_css, extra))


class UigateContract(unittest.TestCase):
    def test_clean_page_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = write_page(tmp, CLEAN_PAGE)
            code, out, _ = run_cli(target, "--no-color")
            self.assertEqual(code, 0, out)
            self.assertIn("ok --", out)

    def test_red_example_fails_all_objective_rules(self):
        code, data = findings_json(RED)
        self.assertEqual(code, 1)
        rows = rule_map(data)
        self.assertEqual(len(rows["low-contrast"]), 3)
        ratios = sorted(f["measured"] for f in rows["low-contrast"])
        self.assertEqual(ratios, ["2.85:1", "3.85:1", "4.11:1"])
        self.assertEqual(len(rows["missing-alt"]), 2)
        self.assertEqual(len(rows["missing-focus-style"]), 1)
        self.assertEqual(len(rows["small-text"]), 2)
        sizes = sorted(f["measured"] for f in rows["small-text"])
        self.assertEqual(sizes, ["10px", "11px"])
        targets = sorted(f["measured"] for f in rows["small-target"])
        self.assertEqual(targets, ["20px", "32px"])

    def test_red_example_warns_all_slop_tells(self):
        code, data = findings_json(RED)
        self.assertEqual(code, 1)
        rows = rule_map(data)
        gradient = rows["ai-gradient"][0]
        self.assertIn("#6366f1", gradient["measured"])
        self.assertIn("#8b5cf6", gradient["measured"])
        self.assertIn("Inter", rows["system-font-only"][0]["measured"])
        self.assertTrue(rows["card-grid"])
        self.assertEqual(len(rows["emoji-heading"]), 2)
        self.assertTrue(any("unlock the power of" in f["measured"]
                            for f in rows["hero-boilerplate"]))
        self.assertTrue(rows["hardcoded-palette"])

    def test_clean_example_passes(self):
        code, out, _ = run_cli(CLEAN, "--no-color")
        self.assertEqual(code, 0, out)
        self.assertIn("ok --", out)
        code, data = findings_json(CLEAN)
        self.assertEqual(code, 0, out)
        self.assertEqual(data["findings"], [])

    def test_low_contrast_exact_ratio(self):
        # #777777 on #ffffff is 4.48:1 -- must fail; #767676 is 4.54:1.
        failing = styled("p { color: #777777; background-color: #ffffff; "
                         "font-size: 16px; }", "<p>hi</p>")
        passing = styled("p { color: #767676; background-color: #ffffff; "
                         "font-size: 16px; }", "<p>hi</p>")
        with tempfile.TemporaryDirectory() as tmp:
            code, data = findings_json(write_page(tmp, failing))
            self.assertEqual(code, 1)
            fails = [f for f in data["findings"]
                     if f["rule"] == "low-contrast"]
            self.assertEqual(len(fails), 1)
            self.assertEqual(fails[0]["measured"], "4.48:1")
            self.assertEqual(fails[0]["threshold"], "4.5:1")
            target = write_page(tmp, passing, name="ok.html")
            code, out, _ = run_cli(target, "--no-color")
            self.assertEqual(code, 0, out)
            self.assertNotIn("low-contrast", out)

    def test_large_text_uses_3_to_1(self):
        big = styled("p { color: #777777; background-color: #ffffff; "
                     "font-size: 24px; }", "<p>hi</p>")
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = run_cli(write_page(tmp, big), "--no-color")
            self.assertEqual(code, 0, out)
            self.assertNotIn("low-contrast", out)

    def test_focus_alt_targets_text_each_fire(self):
        with tempfile.TemporaryDirectory() as tmp:
            no_focus = write_page(
                tmp, "<!DOCTYPE html><html><head><style>"
                "p { color: #111; background: #fff; }</style></head>"
                "<body><p>hi</p></body></html>", name="a.html")
            code, data = findings_json(no_focus)
            self.assertEqual(code, 1)
            self.assertEqual(
                rule_map(data)["missing-focus-style"][0]["measured"],
                "0 focus selectors")
            with_focus = write_page(
                tmp, "<!DOCTYPE html><html><head><style>"
                "p { color: #111; background: #fff; }"
                "a:focus { outline: 2px solid red; }</style></head>"
                "<body><img src='a.png' alt='A loaf'><p>hi</p>"
                "</body></html>", name="b.html")
            code, out, _ = run_cli(with_focus, "--no-color")
            self.assertEqual(code, 0, out)

            img = write_page(
                tmp, styled("", "<img src='a.png'>"), name="c.html")
            code, data = findings_json(img)
            rows = rule_map(data)["missing-alt"]
            self.assertEqual(rows[0]["measured"], "no alt attribute")

            tiny = write_page(
                tmp, styled("p { color: #111; background: #fff; "
                            "font-size: 9px; }", "<p>hi</p>"),
                name="d.html")
            code, data = findings_json(tiny)
            rows = rule_map(data)["small-text"]
            self.assertEqual(rows[0]["measured"], "9px")
            self.assertEqual(rows[0]["threshold"], "min 12px")

            small = write_page(
                tmp, styled("", "<button style='width: 24px; height: 24px;'>"
                            "x</button>"), name="e.html")
            code, data = findings_json(small)
            rows = rule_map(data)["small-target"]
            self.assertEqual(rows[0]["measured"], "24px")
            self.assertEqual(rows[0]["threshold"], "min 40px")

    def test_missing_inputs_are_usage_errors(self):
        code, _, err = run_cli(os.path.join("nope", "dir"))
        self.assertEqual(code, 2)
        self.assertIn("not a file or directory", err)
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = run_cli(tmp)
            self.assertEqual(code, 2)
            self.assertIn("no HTML/CSS files", err)
            target = write_page(tmp, "<p>hi</p>", name="note.txt")
            code, _, err = run_cli(target)
            self.assertEqual(code, 2)
            self.assertIn("not an HTML/CSS file", err)

    def test_allow_exempts_with_a_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            tiny = write_page(
                tmp, styled("p { color: #111; background: #fff; "
                            "font-size: 9px; }", "<p>hi</p>"))
            code, out, _ = run_cli(tiny, "--allow", "small-text=footnote",
                                   "--no-color")
            self.assertEqual(code, 0, out)
            self.assertIn("exempt", out)
            self.assertIn("ok --", out)

    def test_var_background_is_skipped_not_assumed(self):
        # A literal foreground over an unresolvable var() background must be
        # skipped, never measured against an assumed white page (the false
        # positive that failed white-on-brand-color buttons).
        with tempfile.TemporaryDirectory() as tmp:
            var_page = write_page(
                tmp,
                styled(":root { --brand: #0d6e56; }\n"
                       "button { color: #ffffff; background: var(--brand); "
                       "font-size: 16px; }", "<button>Go</button>"),
                "var.html")
            _, data = findings_json(var_page)
            self.assertNotIn("low-contrast", rule_map(data))
            # the measuring path stays armed: a failing literal still fires
            fail_page = write_page(
                tmp,
                styled("button { color: #777777; background: #ffffff; "
                       "font-size: 16px; }", "<button>Go</button>"),
                "fail.html")
            _, data = findings_json(fail_page)
            self.assertIn("low-contrast", rule_map(data))

    def test_strict_blocks_on_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = write_page(tmp, CLEAN_PAGE)
            code, out, _ = run_cli(target, "--no-color")
            self.assertEqual(code, 0, out)
            code, _, _ = run_cli(RED, "--strict", "--no-color")
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
