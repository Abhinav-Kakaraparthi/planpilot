from datetime import datetime
from pathlib import Path

from mss import mss
from PIL import Image


class ScreenCaptureService:
    def __init__(self, save_screenshots: bool, captures_dir: Path) -> None:
        self.save_screenshots = save_screenshots
        self.captures_dir = captures_dir
        if self.save_screenshots:
            self.captures_dir.mkdir(parents=True, exist_ok=True)

    def capture_primary_display(self) -> tuple[Image.Image, str | None]:
        with mss() as sct:
            monitor = sct.monitors[1]
            raw = sct.grab(monitor)
            image = Image.frombytes("RGB", raw.size, raw.rgb)

        path = None
        if self.save_screenshots:
            filename = f"capture-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.png"
            output = self.captures_dir / filename
            image.save(output)
            path = str(output)

        return image, path

