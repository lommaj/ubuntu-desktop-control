"""
OCR-based text detection using Tesseract.

Provides fallback element finding when AT-SPI is unavailable or
doesn't expose the needed elements.
"""

from dataclasses import dataclass, field
from typing import Optional
import re

# OCR imports
try:
    import pytesseract
    from PIL import Image
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    Image = None
    np = None

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None


@dataclass
class OCRMatch:
    """Represents a text match found via OCR."""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    word_index: int = 0  # Index within multi-word matches

    @property
    def center(self) -> tuple[int, int]:
        """Get center coordinates of the text."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "bounds": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height
            },
            "center": {"x": self.center[0], "y": self.center[1]},
            "confidence": self.confidence
        }


@dataclass
class OCRResult:
    """Full OCR result with all detected text."""
    words: list[OCRMatch] = field(default_factory=list)
    full_text: str = ""

    def to_dict(self) -> dict:
        return {
            "words": [w.to_dict() for w in self.words],
            "full_text": self.full_text
        }


def is_available() -> bool:
    """Check if OCR is available on this system."""
    if not TESSERACT_AVAILABLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def preprocess_image(image: "Image.Image", upscale: bool = True) -> "Image.Image":
    """
    Preprocess image for better OCR results.

    Args:
        image: PIL Image object
        upscale: Whether to upscale small images

    Returns:
        Preprocessed PIL Image
    """
    if not TESSERACT_AVAILABLE:
        return image

    # Convert to grayscale
    if image.mode != "L":
        gray = image.convert("L")
    else:
        gray = image.copy()

    # Upscale if image is small
    if upscale:
        w, h = gray.size
        if w < 1000 or h < 500:
            scale = max(2, min(4, 2000 // w))
            gray = gray.resize(
                (w * scale, h * scale),
                Image.Resampling.LANCZOS
            )

    # Apply adaptive threshold if OpenCV is available
    if CV2_AVAILABLE:
        try:
            img_array = np.array(gray)

            # Apply adaptive threshold for better contrast
            thresh = cv2.adaptiveThreshold(
                img_array,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )

            return Image.fromarray(thresh)
        except Exception:
            pass

    return gray


def ocr_image(
    image: "Image.Image",
    preprocess: bool = True,
    psm: int = 11,
    min_confidence: float = 30.0
) -> OCRResult:
    """
    Perform OCR on an image and return word-level results.

    Args:
        image: PIL Image object
        preprocess: Whether to preprocess the image
        psm: Page segmentation mode (11 = sparse text)
        min_confidence: Minimum confidence threshold (0-100)

    Returns:
        OCRResult with detected words
    """
    if not TESSERACT_AVAILABLE:
        return OCRResult()

    # Preprocess if requested
    if preprocess:
        processed = preprocess_image(image)
    else:
        processed = image

    # Get scaling factor if image was resized
    scale_x = image.width / processed.width
    scale_y = image.height / processed.height

    # Perform OCR with data output
    try:
        config = f"--psm {psm}"
        data = pytesseract.image_to_data(
            processed,
            config=config,
            output_type=pytesseract.Output.DICT
        )
    except Exception:
        return OCRResult()

    words = []
    full_text_parts = []

    n_boxes = len(data["text"])
    for i in range(n_boxes):
        text = data["text"][i].strip()
        if not text:
            continue

        conf = float(data["conf"][i])
        if conf < min_confidence:
            continue

        # Scale coordinates back to original image size
        x = int(data["left"][i] * scale_x)
        y = int(data["top"][i] * scale_y)
        w = int(data["width"][i] * scale_x)
        h = int(data["height"][i] * scale_y)

        words.append(OCRMatch(
            text=text,
            x=x,
            y=y,
            width=w,
            height=h,
            confidence=conf,
            word_index=len(words)
        ))

        full_text_parts.append(text)

    return OCRResult(
        words=words,
        full_text=" ".join(full_text_parts)
    )


def find_text(
    image: "Image.Image",
    text: str,
    exact: bool = False,
    case_sensitive: bool = False,
    min_confidence: float = 30.0
) -> list[OCRMatch]:
    """
    Find text on screen via OCR.

    Args:
        image: PIL Image object (screenshot)
        text: Text to find
        exact: Require exact match (vs. partial)
        case_sensitive: Case-sensitive matching
        min_confidence: Minimum OCR confidence

    Returns:
        List of OCRMatch objects for found text
    """
    if not TESSERACT_AVAILABLE:
        return []

    # Perform OCR
    result = ocr_image(image, min_confidence=min_confidence)

    # Normalize search text
    search_text = text if case_sensitive else text.lower()
    search_words = search_text.split()

    matches = []

    if len(search_words) == 1:
        # Single word search
        for word in result.words:
            word_text = word.text if case_sensitive else word.text.lower()

            if exact:
                if word_text == search_text:
                    matches.append(word)
            else:
                if search_text in word_text:
                    matches.append(word)
    else:
        # Multi-word phrase search
        # Look for consecutive words matching the phrase
        for i in range(len(result.words) - len(search_words) + 1):
            phrase_words = result.words[i:i + len(search_words)]
            phrase_text = " ".join(
                w.text if case_sensitive else w.text.lower()
                for w in phrase_words
            )

            if exact:
                match = phrase_text == search_text
            else:
                match = search_text in phrase_text

            if match:
                # Create a combined match spanning all words
                first = phrase_words[0]
                last = phrase_words[-1]

                combined = OCRMatch(
                    text=" ".join(w.text for w in phrase_words),
                    x=first.x,
                    y=min(w.y for w in phrase_words),
                    width=last.x + last.width - first.x,
                    height=max(w.y + w.height for w in phrase_words) - min(w.y for w in phrase_words),
                    confidence=min(w.confidence for w in phrase_words),
                    word_index=first.word_index
                )
                matches.append(combined)

    return matches


def find_text_regex(
    image: "Image.Image",
    pattern: str,
    min_confidence: float = 30.0
) -> list[OCRMatch]:
    """
    Find text matching a regex pattern.

    Args:
        image: PIL Image object (screenshot)
        pattern: Regex pattern to match
        min_confidence: Minimum OCR confidence

    Returns:
        List of OCRMatch objects for found text
    """
    if not TESSERACT_AVAILABLE:
        return []

    result = ocr_image(image, min_confidence=min_confidence)

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return []

    matches = []
    for word in result.words:
        if regex.search(word.text):
            matches.append(word)

    return matches


def get_all_text(
    image: "Image.Image",
    min_confidence: float = 30.0
) -> str:
    """
    Get all text from an image.

    Args:
        image: PIL Image object
        min_confidence: Minimum OCR confidence

    Returns:
        Full text extracted from image
    """
    if not TESSERACT_AVAILABLE:
        return ""

    result = ocr_image(image, min_confidence=min_confidence)
    return result.full_text
