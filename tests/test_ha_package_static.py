"""Plain-text safety checks on the Home Assistant light package (stdlib only).

homeassistant/desk_lamp.yaml turns the Lumos buttons into an assumed-state
light. These checks keep it from pressing anything it should not, or pressing
on its own. Its behavior was checked against a real Home Assistant; see
docs/home-assistant-light.md.
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "homeassistant" / "desk_lamp.yaml"
MANIFEST = REPO / "captures" / "commands.json"

MODES = ["Warm 100%", "Warm 50%", "Neutral 100%", "Neutral 50%", "Cool 100%", "Cool 50%", "Night mode"]


def strip_comments(text):
    """Drop YAML comments so explanatory prose does not trip the checks."""
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        lines.append(re.sub(r"\s+#.*$", "", line))
    return "\n".join(lines)


def slug(label):
    """Home Assistant's entity ID for an ESPHome button named `label`."""
    return "button.lumos_lamp_" + re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def body():
    return strip_comments(PACKAGE.read_text(encoding="utf-8"))


def section(text, key):
    """The top-level `key:` block, up to the next top-level key."""
    match = re.search(rf"(?ms)^{key}:\n(.*?)(?=^\S|\Z)", text)
    assert match, f"no top-level {key}: section"
    return match.group(1)


def commands():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["commands"]


class HomeAssistantPackageSafetyTests(unittest.TestCase):
    def test_presses_only_exposed_verified_buttons(self):
        allowed = {slug(c["label"]) for c in commands() if c["expose"] and c["verified"]}
        used = set(re.findall(r"button\.lumos_lamp_[a-z0-9_]+", body()))
        self.assertTrue(used, "no Lumos buttons referenced")
        self.assertLessEqual(used, allowed, f"not exposed or not verified: {sorted(used - allowed)}")

    def test_never_presses_hidden_buttons(self):
        text = body()
        for c in commands():
            if not c["expose"]:
                with self.subTest(command=c["id"]):
                    self.assertNotIn(slug(c["label"]), text)
                    self.assertNotIn(f"button.lumos_lamp_{c['id']}", text)

    def test_every_mode_maps_to_its_own_button(self):
        text = body()
        options = re.findall(r"(?m)^\s+- (.+)$", section(text, "input_select"))
        self.assertEqual(options, MODES)
        labels = {c["label"] for c in commands() if c["expose"]}
        for mode in MODES:
            with self.subTest(mode=mode):
                self.assertIn(mode, labels)
                self.assertRegex(text, rf'(?m)^\s+"{re.escape(mode)}": {re.escape(slug(mode))}$')

    def test_nothing_presses_on_its_own(self):
        text = body()
        for word in ("automation:", "trigger", "homeassistant_start", "time_pattern", "interval", "initial:"):
            with self.subTest(word=word):
                self.assertNotIn(word, text)

    def test_only_the_script_presses_buttons(self):
        text = body()
        self.assertIn("button.press", section(text, "script"))
        for key in ("input_boolean", "input_select", "template"):
            with self.subTest(section=key):
                self.assertNotIn("button.press", section(text, key))

    def test_power_is_pressed_only_when_assumed_state_differs(self):
        lines = body().splitlines()
        hits = [i for i, line in enumerate(lines) if line.strip() == "entity_id: button.lumos_lamp_power"]
        self.assertEqual(len(hits), 2, "expected one Power press for on and one for off")
        guards = []
        for i in hits:
            before = "\n".join(lines[max(0, i - 8) : i])
            guard = re.findall(r"value_template: \"\{\{ (not was_on|was_on) \}\}\"", before)
            self.assertTrue(guard, f"Power press at line {i + 1} is not guarded by was_on")
            guards.append(guard[-1])
        self.assertEqual(sorted(guards), ["not was_on", "was_on"])

    def test_assumed_state_is_read_when_the_run_starts(self):
        # Script-level variables render when a run is queued, so a queued run
        # would see stale state and could press Power twice. Read it in the
        # sequence instead.
        script = section(body(), "script")
        self.assertIn("mode: queued", script)
        head, _, sequence = script.partition("    sequence:\n")
        self.assertNotIn("was_on:", head)
        self.assertIn("was_on:", sequence)
        self.assertIn("new_mode:", sequence)

    def test_light_hands_every_request_to_the_queue(self):
        template = section(body(), "template")
        for action in ("turn_on", "turn_off", "set_level", "set_temperature"):
            with self.subTest(action=action):
                block = re.search(rf"(?ms)^        {action}:\n(.*?)(?=^        \S|\Z)", template)
                self.assertIsNotNone(block, f"{action} missing")
                self.assertIn("action: script.turn_on", block.group(1))
                self.assertIn("entity_id: script.desk_lamp_set", block.group(1))
        self.assertNotIn("action: script.desk_lamp_set", template)

    def test_light_is_unavailable_while_the_board_is_offline(self):
        template = section(body(), "template")
        self.assertRegex(template, r"availability: >-\n\s+\{\{ states\.button\.lumos_lamp_power is not none")


if __name__ == "__main__":
    unittest.main()
