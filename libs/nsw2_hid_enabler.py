"""nsw2_hid_enabler.py - Nintendo Switch 2 Pro Controller HID Enabler & Smart Stick Calibration.

This module is **NSw2 Pro Controller-specific**.

It provides:
  1) USB HID initialization (enables input streaming over USB).
  2) Smart stick calibration that preserves partial tilt and reaches full range
     in every direction by normalizing with a per-angle max-radius table.

Key points
----------
- We avoid any "outer snap" threshold hack.
- Calibration learns the stick gate shape: r_max(theta).
- We also infer Y-axis sign by asking the user to hold UP then DOWN; we store an
  `invert_y` flag so the *internal* coordinate becomes pygame-standard:
      UP => negative vertical

Downstream expectation
---------------------
After this module's correction, your app should treat axes as:
  - horizontal: right positive
  - vertical:   up negative
so SerialWorker can always convert to device protocol with:
  y = round((-v) * 127.5 + 127.5)

Dependencies
------------
- pyusb
- On Windows: libusb backend (recommended: pip install libusb-package)

"""

from __future__ import annotations

import logging
import math
import platform
import time
from dataclasses import dataclass, field
from typing import Optional

_logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  USB constants (NSw2 controllers)
# ═══════════════════════════════════════════════════════════════════════════

VENDOR_ID = 0x057E
PRODUCT_IDS = {
    0x2066: "Joy-Con (L)",
    0x2067: "Joy-Con (R)",
    0x2069: "Pro Controller",
    0x2073: "GCN Controller",
}
PROCON2_PID = 0x2069
USB_INTERFACE_NUMBER = 1

# HID initialization command sequence (community reverse-engineered)
_INIT_COMMANDS: list[tuple[bytes, str]] = [
    (bytes([0x03, 0x91, 0x00, 0x0D, 0x00, 0x08, 0x00, 0x00,
            0x01, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
     "Init 0x03"),
    (bytes([0x07, 0x91, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]), "Handshake 0x07"),
    (bytes([0x16, 0x91, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]), "Unknown 0x16"),
    (bytes([0x15, 0x91, 0x00, 0x01, 0x00, 0x0E, 0x00, 0x00,
            0x00, 0x02, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]), "Request MAC"),
    (bytes([0x15, 0x91, 0x00, 0x02, 0x00, 0x11, 0x00, 0x00,
            0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]), "LTK Request"),
    (bytes([0x15, 0x91, 0x00, 0x03, 0x00, 0x01, 0x00, 0x00, 0x00]), "Unknown 0x15 arg3"),
    (bytes([0x09, 0x91, 0x00, 0x07, 0x00, 0x08, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "Unknown 0x09"),
    (bytes([0x0C, 0x91, 0x00, 0x02, 0x00, 0x04, 0x00, 0x00,
            0x27, 0x00, 0x00, 0x00]), "IMU 0x02"),
    (bytes([0x11, 0x91, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00]), "OUT Unknown 0x11"),
    (bytes([0x0A, 0x91, 0x00, 0x08, 0x00, 0x14, 0x00, 0x00,
            0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0x35, 0x00, 0x46, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00]), "Unknown 0x0A"),
    (bytes([0x0C, 0x91, 0x00, 0x04, 0x00, 0x04, 0x00, 0x00,
            0x27, 0x00, 0x00, 0x00]), "IMU 0x04"),
    (bytes([0x03, 0x91, 0x00, 0x0A, 0x00, 0x04, 0x00, 0x00,
            0x09, 0x00, 0x00, 0x00]), "Enable Haptics"),
    (bytes([0x10, 0x91, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]), "OUT Unknown 0x10"),
    (bytes([0x01, 0x91, 0x00, 0x0C, 0x00, 0x00, 0x00, 0x00]), "OUT Unknown 0x01"),
    (bytes([0x03, 0x91, 0x00, 0x01, 0x00, 0x00, 0x00]), "OUT Unknown 0x03"),
    (bytes([0x0A, 0x91, 0x00, 0x02, 0x00, 0x04, 0x00, 0x00,
            0x03, 0x00, 0x00]), "OUT Unknown 0x0A alt"),
]

_PLAYER_LED_MASKS = {1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, "all": 0x0F}


class NSw2HidEnableResult:
    def __init__(self, success: bool, device_name: str = "", message: str = ""):
        self.success = success
        self.device_name = device_name
        self.message = message


def _get_backend():
    try:
        import usb.backend.libusb1
        backend = usb.backend.libusb1.get_backend()
        if backend is not None:
            return backend
        try:
            import libusb_package
            return usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        except ImportError:
            return None
    except ImportError:
        return None


def is_pyusb_available() -> bool:
    try:
        import usb.backend.libusb1  # noqa: F401
        return _get_backend() is not None
    except ImportError:
        return False


def find_nsw2_devices() -> list[dict]:
    """Enumerate connected NSw2 controllers via USB (pyusb)."""
    try:
        import usb.core
    except ImportError:
        return []

    backend = _get_backend()
    if backend is None:
        return []

    devices: list[dict] = []
    for pid, name in PRODUCT_IDS.items():
        found = usb.core.find(find_all=True, idVendor=VENDOR_ID, idProduct=pid, backend=backend)
        for dev in found:
            devices.append({"vid": VENDOR_ID, "pid": pid, "name": name, "device": dev})
    return devices


def _send_usb(ep_out, ep_in, data: bytes, _description: str = "") -> None:
    import usb.core
    ep_out.write(data)
    time.sleep(0.01)
    if ep_in is None:
        return
    try:
        _ = ep_in.read(64, timeout=100)
    except usb.core.USBError:
        return


def _set_player_led(ep_out, ep_in, led_mask: int) -> None:
    command = bytes([
        0x09, 0x91, 0x00, 0x07, 0x00, 0x08, 0x00, 0x00,
        led_mask, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])
    _send_usb(ep_out, ep_in, command)


def enable_hid(target_pid: int = PROCON2_PID, player_number: int = 1) -> NSw2HidEnableResult:
    """Enable HID streaming for NSw2 controller over USB."""
    try:
        import usb.core
        import usb.util
    except ImportError:
        return NSw2HidEnableResult(False, "", "pyusb is not installed. Run: pip install pyusb")

    backend = _get_backend()
    if backend is None:
        msg = "libusb backend not found. Windows: pip install libusb-package | macOS: brew install libusb"
        return NSw2HidEnableResult(False, "", msg)

    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=target_pid, backend=backend)
    if dev is None:
        return NSw2HidEnableResult(False, "", "Switch 2 controller not found via USB")

    device_name = PRODUCT_IDS.get(target_pid, "Unknown")

    try:
        if dev.is_kernel_driver_active(USB_INTERFACE_NUMBER):
            dev.detach_kernel_driver(USB_INTERFACE_NUMBER)
    except Exception:
        pass

    try:
        dev.set_configuration()
    except Exception:
        pass

    try:
        usb.util.claim_interface(dev, USB_INTERFACE_NUMBER)
    except Exception as exc:
        return NSw2HidEnableResult(False, device_name, f"Could not claim interface: {exc}")

    try:
        cfg = dev.get_active_configuration()
        intf = cfg[(USB_INTERFACE_NUMBER, 0)]
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT,
        )
        ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN,
        )
        if ep_out is None:
            return NSw2HidEnableResult(False, device_name, "Could not find OUT endpoint")

        for cmd, desc in _INIT_COMMANDS:
            _send_usb(ep_out, ep_in, cmd, desc)

        _set_player_led(ep_out, ep_in, _PLAYER_LED_MASKS.get(player_number, 0x01))
        return NSw2HidEnableResult(True, device_name, "HID enabled successfully")

    except Exception as exc:
        return NSw2HidEnableResult(False, device_name, f"Init failed: {exc}")

    finally:
        try:
            usb.util.release_interface(dev, USB_INTERFACE_NUMBER)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
#  Smart stick correction
# ═══════════════════════════════════════════════════════════════════════════


def _angle_of(x: float, y: float) -> float:
    return math.atan2(y, x)  # [-pi, pi]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass
class AngleRadiusTable:
    """Stores max radius per angle bin and provides interpolation."""

    bins: int = 72  # 5 deg
    rmax: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.rmax:
            self.rmax = [0.0] * self.bins

    def update(self, theta: float, r: float) -> None:
        idx = int(((theta + math.pi) / (2 * math.pi)) * self.bins) % self.bins
        if r > self.rmax[idx]:
            self.rmax[idx] = r

    def finalize(self, fallback: float = 1.0) -> None:
        """Fill empty bins by propagation."""
        if max(self.rmax) <= 1e-6:
            self.rmax = [fallback] * self.bins
            return

        last = None
        for i in range(self.bins):
            if self.rmax[i] > 1e-6:
                last = self.rmax[i]
            elif last is not None:
                self.rmax[i] = last

        last = None
        for i in range(self.bins - 1, -1, -1):
            if self.rmax[i] > 1e-6:
                last = self.rmax[i]
            elif last is not None:
                self.rmax[i] = last

        for i in range(self.bins):
            if self.rmax[i] <= 1e-6:
                self.rmax[i] = fallback

        self.rmax = [max(0.2, v) for v in self.rmax]

    def rmax_at(self, theta: float) -> float:
        pos = ((theta + math.pi) / (2 * math.pi)) * self.bins
        i0 = int(math.floor(pos)) % self.bins
        t = pos - math.floor(pos)
        i1 = (i0 + 1) % self.bins
        return _lerp(self.rmax[i0], self.rmax[i1], t)

    def to_dict(self) -> dict:
        return {"bins": self.bins, "rmax": list(self.rmax)}

    @classmethod
    def from_dict(cls, data: dict) -> "AngleRadiusTable":
        bins = int(data.get("bins", 72))
        rmax = data.get("rmax", [])
        if not isinstance(rmax, list):
            rmax = []
        table = cls(bins=bins, rmax=[float(v) for v in rmax])
        if len(table.rmax) != table.bins:
            table.rmax = (table.rmax + [0.0] * table.bins)[:table.bins]
        table.finalize(fallback=max(table.rmax) if table.rmax else 1.0)
        return table


@dataclass
class StickProfile:
    """A calibrated stick profile."""

    center_x: float = 0.0
    center_y: float = 0.0
    invert_y: bool = False  # convert device sign -> pygame standard (up negative)

    max_abs_x: float = 1.0
    max_abs_y: float = 1.0

    table: AngleRadiusTable = field(default_factory=AngleRadiusTable)

    def correct(self, raw_x: float, raw_y: float) -> tuple[float, float]:
        # normalize sign to pygame standard
        x = float(raw_x)
        y = -float(raw_y) if self.invert_y else float(raw_y)

        # center
        x -= self.center_x
        y -= self.center_y

        # axis scaling (fallback)
        if self.max_abs_x > 1e-6:
            x /= self.max_abs_x
        if self.max_abs_y > 1e-6:
            y /= self.max_abs_y

        r = math.sqrt(x * x + y * y)
        if r <= 1e-9:
            return 0.0, 0.0

        theta = _angle_of(x, y)
        rmax = self.table.rmax_at(theta)
        if rmax <= 1e-6:
            return 0.0, 0.0

        # normalize by directional max
        s = 1.0 / rmax
        x2, y2 = x * s, y * s

        # clamp unit circle
        r2 = math.sqrt(x2 * x2 + y2 * y2)
        if r2 > 1.0:
            x2 /= r2
            y2 /= r2

        return x2, y2

    def to_dict(self) -> dict:
        return {
            "center_x": self.center_x,
            "center_y": self.center_y,
            "invert_y": self.invert_y,
            "max_abs_x": self.max_abs_x,
            "max_abs_y": self.max_abs_y,
            "table": self.table.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StickProfile":
        prof = cls()
        prof.center_x = float(data.get("center_x", 0.0))
        prof.center_y = float(data.get("center_y", 0.0))
        prof.invert_y = bool(data.get("invert_y", False))
        prof.max_abs_x = float(data.get("max_abs_x", 1.0))
        prof.max_abs_y = float(data.get("max_abs_y", 1.0))
        prof.table = AngleRadiusTable.from_dict(data.get("table", {}))
        return prof


@dataclass
class NSw2StickCorrector:
    """Holds profiles for left/right sticks."""

    enabled: bool = False
    left: StickProfile = field(default_factory=StickProfile)
    right: StickProfile = field(default_factory=StickProfile)

    def correct_left(self, raw_x: float, raw_y: float) -> tuple[float, float]:
        return self.left.correct(raw_x, raw_y) if self.enabled else (raw_x, raw_y)

    def correct_right(self, raw_x: float, raw_y: float) -> tuple[float, float]:
        return self.right.correct(raw_x, raw_y) if self.enabled else (raw_x, raw_y)

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "left": self.left.to_dict(), "right": self.right.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "NSw2StickCorrector":
        c = cls()
        c.enabled = bool(data.get("enabled", False))
        c.left = StickProfile.from_dict(data.get("left", {}))
        c.right = StickProfile.from_dict(data.get("right", {}))
        return c

    @classmethod
    def default_nsw2(cls) -> "NSw2StickCorrector":
        c = cls(enabled=True)
        c.left.table.finalize(fallback=1.0)
        c.right.table.finalize(fallback=1.0)
        return c


class StickCalibrator:
    """Collect samples for smart StickProfile.

    Flow:
      - record_center() while sticks are neutral
      - record_y_up() while holding UP
      - record_y_down() while holding DOWN
      - record_range() while swirling full circle
    """

    def __init__(self, bins: int = 72) -> None:
        self._center_x: list[float] = []
        self._center_y: list[float] = []
        self._up_y: list[float] = []
        self._down_y: list[float] = []
        self._range_samples: list[tuple[float, float]] = []
        self._bins = int(bins)

    def record_center(self, x: float, y: float) -> None:
        self._center_x.append(float(x))
        self._center_y.append(float(y))

    def record_y_up(self, y: float) -> None:
        self._up_y.append(float(y))

    def record_y_down(self, y: float) -> None:
        self._down_y.append(float(y))

    def record_range(self, x: float, y: float) -> None:
        self._range_samples.append((float(x), float(y)))

    def build_profile(self) -> StickProfile:
        # center
        cx = sum(self._center_x) / len(self._center_x) if self._center_x else 0.0
        cy = sum(self._center_y) / len(self._center_y) if self._center_y else 0.0

        # infer invert_y so that UP becomes negative
        invert_y = False
        if self._up_y and self._down_y:
            up = sum(self._up_y) / len(self._up_y)
            down = sum(self._down_y) / len(self._down_y)
            invert_y = up > down

        # compute axis scaling maxima
        max_abs_x = 1e-6
        max_abs_y = 1e-6
        for x, y in self._range_samples:
            y2 = -y if invert_y else y
            x2 = x - cx
            y2 = y2 - cy
            max_abs_x = max(max_abs_x, abs(x2))
            max_abs_y = max(max_abs_y, abs(y2))
        max_abs_x = max(max_abs_x, 0.2)
        max_abs_y = max(max_abs_y, 0.2)

        table = AngleRadiusTable(bins=self._bins)
        for x, y in self._range_samples:
            y2 = -y if invert_y else y
            x2 = (x - cx) / max_abs_x
            y2 = (y2 - cy) / max_abs_y
            r = math.sqrt(x2 * x2 + y2 * y2)
            if r <= 1e-6:
                continue
            theta = _angle_of(x2, y2)
            table.update(theta, r)

        table.finalize(fallback=max(table.rmax) if table.rmax else 1.0)
        # conservative margin to avoid over-amplifying edge noise
        table.rmax = [v * 0.98 for v in table.rmax]

        return StickProfile(
            center_x=cx,
            center_y=cy,
            invert_y=invert_y,
            max_abs_x=max_abs_x,
            max_abs_y=max_abs_y,
            table=table,
        )


def get_nsw2_default_keymap() -> dict[str, str]:
    """Default keymap for NSw2 Pro Controller (post-HID init)."""
    return {
        "button.0":  "A",
        "button.1":  "B",
        "button.2":  "X",
        "button.3":  "Y",
        "button.4":  "R",
        "button.5":  "ZR",
        "button.6":  "PLUS",
        "button.7":  "RCLICK",
        "button.8":  "BTM",
        "button.9":  "RIGHT",
        "button.10": "LEFT",
        "button.11": "TOP",
        "button.12": "L",
        "button.13": "ZL",
        "button.14": "MINUS",
        "button.15": "LCLICK",
        "button.16": "HOME",
        "button.17": "CAPTURE",
    }


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

    if not is_pyusb_available():
        print("pyusb/libusb backend not available")
        print("pip install pyusb")
        if platform.system() == "Windows":
            print("pip install libusb-package")
        return

    devices = find_nsw2_devices()
    if not devices:
        print("No NSw2 controller detected")
        return

    for d in devices:
        print(f"Enabling HID for {d['name']} (PID=0x{d['pid']:04X})")
        res = enable_hid(target_pid=d["pid"], player_number=1)
        print("OK" if res.success else "FAIL", res.message)


if __name__ == "__main__":
    main()
