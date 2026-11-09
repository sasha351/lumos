"""Print serial output from the board and reconnect whenever the port drops.

The ESP32-S3's native USB port disappears for a moment on every reset, so
`esphome logs` exits and misses the boot messages. This keeps retrying.

Needs pyserial, which ESPHome already installs. On macOS with ESPHome
installed by `uv tool install`, run it with ESPHome's Python:

    ~/.local/share/uv/tools/esphome/bin/python scripts/serial_monitor.py

Then tap RST on the board. Press Ctrl+C to stop.
"""

import sys
import time

try:
    import serial
except ImportError:
    sys.exit("pyserial not found: run this with ESPHome's Python (see the docstring).")

DEFAULT_PORT = "/dev/cu.usbmodem101"


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    print(f"Waiting for {port}. Tap RST on the board now. Ctrl+C to stop.", flush=True)
    connected_once = False
    while True:
        try:
            ser = serial.Serial()
            ser.port, ser.baudrate, ser.timeout = port, 115200, 0.2
            ser.dtr = ser.rts = False  # do not reset or hold the chip when opening
            ser.open()
            print("\n--- connected ---", flush=True)
            connected_once = True
            while True:
                data = ser.read(4096)
                if data:
                    sys.stdout.write(data.decode("utf-8", "replace"))
                    sys.stdout.flush()
        except (serial.SerialException, OSError):
            if connected_once:
                print("\n--- port dropped, reconnecting ---", flush=True)
                connected_once = False
            time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n--- stopped ---")
            return 0


if __name__ == "__main__":
    sys.exit(main())
