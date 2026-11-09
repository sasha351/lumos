"""Plain-text safety checks on the ESPHome YAML (stdlib only, no ESPHome needed)."""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ESPHOME = REPO / "esphome"
MAIN = ESPHOME / "lamp-controller.yaml"


def strip_comments(text):
    """Drop YAML comments so explanatory prose does not trip the checks."""
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        lines.append(re.sub(r"\s+#.*$", "", line))
    return "\n".join(lines)


def yaml_files():
    files = sorted(p for p in ESPHOME.glob("*.yaml") if p.name != "secrets.yaml")
    assert MAIN in files, "lamp-controller.yaml is missing"
    return files


class EsphomeStaticSafetyTests(unittest.TestCase):
    def test_no_automatic_transmit_triggers(self):
        forbidden = ["on_boot", "on_connect", "on_client_connected", "interval:", "on_loop", "on_shutdown"]
        for path in yaml_files():
            body = strip_comments(path.read_text(encoding="utf-8"))
            for word in forbidden:
                with self.subTest(file=path.name, word=word):
                    self.assertNotIn(word, body)

    def test_no_stateful_entities(self):
        for path in yaml_files():
            body = strip_comments(path.read_text(encoding="utf-8"))
            for key in ("switch", "light", "number", "fan", "select"):
                with self.subTest(file=path.name, key=key):
                    self.assertIsNone(re.search(rf"^{key}:", body, flags=re.MULTILINE))
            with self.subTest(file=path.name, key="restore_mode"):
                self.assertNotIn("restore_mode", body)

    def test_wired_gpio_numbers_present(self):
        body = strip_comments(MAIN.read_text(encoding="utf-8"))
        for gpio, role in [(12, "SCK"), (11, "MOSI"), (13, "MISO"), (10, "CS"), (4, "GDO0 TX"), (5, "GDO2 RX")]:
            with self.subTest(role=role):
                self.assertRegex(body, rf"\bGPIO{gpio}\b")

    def test_transmit_pin_is_open_drain(self):
        body = strip_comments(MAIN.read_text(encoding="utf-8"))
        block = body.split("remote_transmitter:", 1)[1].split("\nremote_receiver:", 1)[0]
        self.assertIn("number: GPIO4", block)
        self.assertIn("open_drain: true", block)
        self.assertIn("eot_level: false", block)

    def test_serial_logs_do_not_reset_into_download_mode(self):
        body = strip_comments(MAIN.read_text(encoding="utf-8"))
        logger = body.split("\nlogger:", 1)[1].split("\napi:", 1)[0]
        self.assertIn("hardware_uart: USB_SERIAL_JTAG", logger)
        self.assertIn("deassert_rts_dtr: true", logger)

    def test_radio_returns_to_rx_after_transmit(self):
        body = strip_comments(MAIN.read_text(encoding="utf-8"))
        complete = body.split("on_complete:", 1)[1]
        self.assertIn("cc1101.begin_rx", complete)

    def test_secrets_are_referenced_not_inlined(self):
        body = strip_comments(MAIN.read_text(encoding="utf-8"))
        for key in ("wifi_ssid", "wifi_password", "api_encryption_key"):
            with self.subTest(key=key):
                self.assertIn(f"!secret {key}", body)

    def test_secrets_example_has_only_placeholders(self):
        text = (ESPHOME / "secrets.example.yaml").read_text(encoding="utf-8")
        self.assertIn("your-wifi-ssid", text)
        self.assertIn("your-wifi-password", text)
        self.assertIn("placeholder", text)

    def test_secrets_yaml_is_git_ignored(self):
        ignore = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("secrets.yaml", ignore)
        self.assertIn("*.bin", ignore)

    def test_commands_come_from_generated_package(self):
        body = strip_comments(MAIN.read_text(encoding="utf-8"))
        self.assertIn("!include lamp-commands.generated.yaml", body)
        self.assertNotIn("transmit_raw", body)


if __name__ == "__main__":
    unittest.main()
