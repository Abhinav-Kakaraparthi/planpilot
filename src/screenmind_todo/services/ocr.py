import os
import re
import cv2
import numpy as np
import pytesseract
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


class OCRService:
    def extract_text(self, image):
        try:
            if isinstance(image, Image.Image):
                image = np.array(image)

            if not isinstance(image, np.ndarray):
                image = np.array(image)

            if image is None or image.size == 0:
                return ""

            # Focus on center content area to avoid browser bars and app chrome
            image = self._crop_center_content(image)

            if len(image.shape) == 2:
                gray = image
            elif len(image.shape) == 3 and image.shape[2] == 4:
                gray = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                return ""

            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, processed = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            text = pytesseract.image_to_string(
                processed,
                config="--oem 3 --psm 6"
            )

            return self.clean_text(text)

        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def _crop_center_content(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]

        top = int(h * 0.10)
        bottom = int(h * 0.92)
        left = int(w * 0.08)
        right = int(w * 0.92)

        return image[top:bottom, left:right]

    def clean_text(self, text: str) -> str:
        text = " ".join(text.split())

        noise_phrases = [
            "screenmind todo",
            "local ai screen watcher",
            "scan now",
            "recent activity",
            "add manual task",
            "complete",
            "stop watching",
            "start watching",
            "127.0.0.1",
            "localhost",
            "swagger ui",
            "response body",
            "server response",
            "try it out",
            "execute",
            "google chrome",
            "system idle process",
        ]

        lower_text = text.lower()
        for phrase in noise_phrases:
            lower_text = lower_text.replace(phrase, " ")

        words = lower_text.split()

        cleaned_words = []
        for word in words:
            word = re.sub(r"[^a-zA-Z0-9@:/._-]", "", word)

            if len(word) <= 1:
                continue
            if word.isdigit():
                continue
            if len(set(word)) == 1 and len(word) > 3:
                continue

            cleaned_words.append(word)

        deduped = []
        prev = None
        for word in cleaned_words:
            if word != prev:
                deduped.append(word)
            prev = word

        return " ".join(deduped[:300]).strip()