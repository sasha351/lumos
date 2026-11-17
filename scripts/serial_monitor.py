"""Print serial output from the board and reconnect whenever the port drops.

On the old ESP32-S3 the native USB port disappeared for a moment on every reset,
so `esphome logs` exited and missed the boot messages. This keeps retrying, and
opens the port without pulsing DTR/RTS, so it does not reset the board.

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

DEFAULT_PORT = "/dev/cu.usbserial-0001"  # ESP32 CP2102; the S3 was /dev/cu.usbmodem101


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT
    print(f"Waiting for {port}. Tap RST on the board now. Ctrl+C to stop.", flush=True)
    connected_once = False
    last_error = None
    while True:
        try:
            ser = serial.Serial()
            ser.port, ser.baudrate, ser.timeout = port, 115200, 0.2
            ser.dtr = ser.rts = False  # do not reset or hold the chip when opening
            ser.open()
            print("\n--- connected ---", flush=True)
            connected_once = True
            last_error = None
            while True:
                data = ser.read(4096)
                if data:
                    sys.stdout.write(data.decode("utf-8", "replace"))
                    sys.stdout.flush()
        except (serial.SerialException, OSError) as exc:
            if connected_once:
                print("\n--- port dropped, reconnecting ---", flush=True)
                connected_once = False
            elif str(exc) != last_error:
                # Show each new reason once (e.g. port busy) instead of retrying silently.
                print(f"--- cannot open yet: {exc}", flush=True)
            last_error = str(exc)
            time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n--- stopped ---")
            return 0


if __name__ == "__main__":
    sys.exit(main())
