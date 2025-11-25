# Samsung Frame TV API (2025 Update) – Remote Control & Art Mode Access

**Model:** Samsung The Frame 32” — **QE32LS03BBUXXU (LS03B)**  
**Environment:** Local LAN; also connected to SmartThings  
**As-of date:** 2025‑10‑25

---

## Executive summary
Samsung **The Frame** now exposes usable local APIs again for third‑party control. Using the community‑standard Python library **`samsungtvws`** (Samsung TV WebSocket API wrapper), you can:
- Turn the TV on/off (incl. Wake‑on‑LAN for deep standby).
- Detect whether **Art Mode** is active.
- Toggle **Art Mode** on/off directly.
- **Upload images** to the Frame’s art gallery.
- **Select** a specific uploaded image to show immediately (or queue it for the next Art Mode session).

While many basic operations are also available through **SmartThings Cloud API**, **local control** is preferred for responsiveness and for full **Art Mode** features (upload/select).

> **Tip:** The Frame treats “power” a bit differently than other TVs. A short press of **Power** usually toggles between *TV mode* and *Art Mode* rather than fully powering off the panel. This spec embraces that behavior.

---

## Capability matrix

| Capability | Local LAN API (WebSocket) | SmartThings Cloud API |
|---|---|---|
| a) Power on/off | ✅ Power toggle; ✅ WoL from deep standby | ✅ Power on/off (latency depends on cloud) |
| b) Detect Art Mode | ✅ Yes (`get_artmode`) | ⚠️ Limited/indirect |
| c) Set Art Mode on/off | ✅ Yes (`set_artmode(True/False)`) | ⚠️ Not consistently exposed |
| d) Upload image | ✅ Yes (`upload`) | ❌ Not directly (typically via app) |
| e) Activate a specific image | ✅ Yes (`select_image`) | ❌ Not directly |

---

## Prerequisites

1. **Python 3.9+** recommended.
2. Install libraries:
   ```bash
   pip install samsungtvws wakeonlan
   ```
3. Ensure the TV and your machine are on the **same LAN** (Wi‑Fi or Ethernet).
4. On the TV, enable any relevant **network/standby** options (names vary by firmware):
   - *Settings → General → Network → Expert* → "Power on with Mobile / IP remote" (or similar) **On**
   - *External Device Manager → AllShare/IP Control* (if present) **On**
5. Know the TV’s **IP address** (fixed DHCP reservation recommended) and **MAC address** (for Wake‑on‑LAN).

---

## One‑time pairing (token)

The first time your script connects, the TV will prompt you to **Allow** remote control from your “app” (your Python client). The library will save a **token** file locally and reuse it thereafter.

Example bootstrap:
```python
from samsungtvws import SamsungTVWS

TV_IP = "192.168.1.50"   # replace with your TV’s IP
tv = SamsungTVWS(host=TV_IP, name="Matt-Frame-Controller", token_file="frame_token.txt")

# First call will trigger on‑screen permission; accept it on the TV.
print("Paired. Token stored in frame_token.txt")
```

---

## Python control spec

This section defines a minimal, reusable interface to operate your Frame.

### Configuration
- `host`: TV IPv4 address (string, required)
- `mac`: TV MAC address (string, optional; only needed for Wake‑on‑LAN)
- `token_file`: path to persist pairing token (default: `frame_token.txt`)
- `client_name`: identifier shown on the TV when pairing (default: `FrameController`)

### Public API (proposed)
```python
class FrameTV:
    def __init__(self, host: str, token_file: str = "frame_token.txt", client_name: str = "FrameController"):
        ...  # establish WS client (lazy until needed)

    # ---------- Power ----------
    def power_toggle(self) -> None:
        """Simulate Power button (toggles TV mode <-> Art Mode)."""

    def power_on(self, mac: str) -> None:
        """Wake TV from deep standby using Wake-on-LAN (requires MAC)."""

    # ---------- Art Mode ----------
    def is_art_mode(self) -> bool:
        """Return True if Art Mode is active, else False."""

    def set_art_mode(self, on: bool) -> None:
        """Enter or exit Art Mode explicitly."""

    # ---------- Artwork management ----------
    def upload_image(self, image_bytes: bytes, file_type: str = "JPEG", *, matte: str | None = None) -> str:
        """Upload artwork; return content_id (e.g., "MY-F1234")."""

    def select_image(self, content_id: str, show: bool = True) -> None:
        """Select specific artwork; if show=False, queue it without switching to Art Mode."""

    def list_art(self) -> list[dict]:
        """Return metadata for available artworks (IDs, titles, etc.)."""

    def current_art(self) -> dict | None:
        """Return metadata for currently displayed art (if in Art Mode)."""
```

### Behavior notes
- **Power toggle**: Mirrors the remote’s short press. If the TV is in Art Mode, it will wake to TV mode; if in TV mode, it will switch to Art Mode.
- **Power on (WoL)**: Works if the TV’s network standby is enabled and the router/LAN permits broadcast.
- **Art mode control**: Uses dedicated Art Mode commands; no need to send power toggles to manage art explicitly.
- **Upload**: Accepts `JPEG` or `PNG`. Returns a **content ID**. Keep it for later selection or deletion.
- **Select**: If `show=False`, the TV stays in its current mode; the image becomes the next Art Mode item.

---

## Reference implementation (Python)

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict

from samsungtvws import SamsungTVWS
from wakeonlan import send_magic_packet


class FrameTV:
    def __init__(self, host: str, token_file: str = "frame_token.txt", client_name: str = "FrameController"):
        self.host = host
        self.token_file = token_file
        self.client_name = client_name
        self._tv: Optional[SamsungTVWS] = None

    # Internal: lazy init of WS client
    def _client(self) -> SamsungTVWS:
        if self._tv is None:
            self._tv = SamsungTVWS(host=self.host, name=self.client_name, token_file=self.token_file)
        return self._tv

    # ---------- Power ----------
    def power_toggle(self) -> None:
        tv = self._client()
        tv.shortcuts().power()

    def power_on(self, mac: str) -> None:
        # Wake from deep standby
        send_magic_packet(mac)

    # ---------- Art Mode ----------
    def is_art_mode(self) -> bool:
        tv = self._client()
        status = tv.art().get_artmode()
        # Library may return bool or dict with 'artmode' field depending on version
        if isinstance(status, bool):
            return status
        if isinstance(status, dict) and "artmode" in status:
            return bool(status["artmode"])
        # Fallback: not in Art Mode
        return False

    def set_art_mode(self, on: bool) -> None:
        tv = self._client()
        tv.art().set_artmode(bool(on))

    # ---------- Artwork management ----------
    def upload_image(self, image_bytes: bytes, file_type: str = "JPEG", *, matte: str | None = None) -> str:
        tv = self._client()
        if matte is None:
            content_id = tv.art().upload(image_bytes, file_type=file_type)
        else:
            content_id = tv.art().upload(image_bytes, file_type=file_type, matte=matte)
        # Expect something like 'MY-Fxxxx' for user uploads
        return content_id

    def select_image(self, content_id: str, show: bool = True) -> None:
        tv = self._client()
        tv.art().select_image(content_id, show=bool(show))

    def list_art(self) -> List[Dict]:
        tv = self._client()
        return tv.art().available()

    def current_art(self) -> Optional[Dict]:
        tv = self._client()
        return tv.art().get_current()


def demo():
    # ---- CONFIGURE THESE ----
    TV_IP = "192.168.1.50"       # replace with your TV’s IP
    TV_MAC = "AA:BB:CC:DD:EE:FF" # replace with your TV’s MAC for WoL
    IMAGE_PATH = "my_photo.jpg"  # replace with a local test image

    frame = FrameTV(host=TV_IP, token_file="frame_token.txt", client_name="Matt-Frame-Controller")

    # If the TV is fully off, wake it
    frame.power_on(TV_MAC)

    # Ensure we end up in Art Mode
    if not frame.is_art_mode():
        frame.set_art_mode(True)

    # Upload and display an image
    data = Path(IMAGE_PATH).read_bytes()
    cid = frame.upload_image(data, file_type="JPEG")
    print(f"Uploaded content id: {cid}")
    frame.select_image(cid, show=True)
    print("Displayed uploaded image.")

    # Inspect current artwork
    current = frame.current_art()
    print("Current art:", current)

    # List available art (IDs)
    listing = frame.list_art()
    print(f"Found {len(listing)} artworks.")
    for art in listing[:5]:
        print("-", art.get("content_id"), art.get("title"))


if __name__ == "__main__":
    demo()
```

---

## SmartThings alternative (optional)

You can also integrate via **SmartThings Cloud API** using a personal access token and the TV’s device ID. This enables basic power and input commands, but **does not** offer direct **Art Mode image upload/select**. Latency can be higher, and operation depends on Samsung’s cloud availability.

Use local control for Art Mode management; reserve SmartThings for scenarios where local WS is unreachable or where you need broader home‑automation orchestration.

---

## Troubleshooting & tips

- **Pairing prompt never appears:** Ensure the TV is on the same LAN; disable VPNs; try power‑cycling the TV. Confirm the IP is correct and reachable (`ping`).  
- **Wake‑on‑LAN doesn’t work:** Verify "Power on with Mobile" (or similar) is enabled, and that your router allows broadcast. Try sending WoL from a wired device on the same subnet.  
- **Upload succeeds but image doesn’t show:** Ensure Art Mode is **on** or call `select_image(..., show=True)`. If you used `show=False`, the image is queued for the next time Art Mode is activated.  
- **File formats:** Prefer high‑quality **JPEG** for photos; **PNG** also works. Very large images may be resized by the TV.  
- **Multiple controllers:** The TV may remember multiple tokens. If control becomes flaky, delete the token file locally and re‑pair to refresh permissions.

---

## Security considerations
- The TV’s WebSocket control runs on your LAN. Treat your home network as a trusted environment.  
- Token files grant control; store them securely.  
- Consider creating a dedicated VLAN/SSID for IoT devices if you need tighter segmentation.

---

## Notes for your model (QE32LS03BBUXXU, “LS03B”)
- This 32" model is part of the **LS03B** generation of The Frame. Earlier 2022 firmware limited Art Mode control; subsequent updates restored third‑party access. If you’re running very old firmware, upgrade to the latest version to ensure Art Mode APIs work as shown.  
- Menu paths and option names can differ slightly by firmware region/version.

---

## Quick‑start checklist
1. `pip install samsungtvws wakeonlan`  
2. Run a short script to pair; accept the on‑screen prompt.  
3. Test: `power_toggle()`, `is_art_mode()`, `set_art_mode(True)`.  
4. Upload: read bytes from a `.jpg`, call `upload_image(...)`, capture the returned **content_id**.  
5. Display: `select_image(content_id, show=True)`.  

You’re set! Enjoy full **Art Mode** automation on your Frame.
