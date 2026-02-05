"""
Screenshot annotation and downsampling.

Provides functions to:
- Downsample screenshots for faster LLM processing
- Annotate screenshots with numbered element markers
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


def downsample_image(
    img: "Image.Image",
    max_width: int = 1280,
    max_height: int = 720
) -> tuple["Image.Image", float]:
    """
    Downsample an image while maintaining aspect ratio.

    Does not upscale images smaller than the target size.

    Args:
        img: PIL Image to downsample
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels

    Returns:
        Tuple of (downsampled image, scale factor)
        Scale factor is < 1 if downsampled, 1.0 if unchanged
    """
    orig_width, orig_height = img.size

    # Calculate scale factors for width and height
    width_scale = max_width / orig_width if orig_width > max_width else 1.0
    height_scale = max_height / orig_height if orig_height > max_height else 1.0

    # Use the smaller scale to maintain aspect ratio
    scale = min(width_scale, height_scale)

    if scale >= 1.0:
        # No downsampling needed
        return img, 1.0

    new_width = int(orig_width * scale)
    new_height = int(orig_height * scale)

    # Use LANCZOS for high-quality downsampling
    from PIL import Image as PILImage
    downsampled = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)

    return downsampled, scale


def annotate_elements(
    img: "Image.Image",
    elements: list,
    scale: float = 1.0,
    circle_radius: int = 12,
    circle_color: str = "red",
    text_color: str = "white",
    font_size: int = 14
) -> "Image.Image":
    """
    Annotate an image with numbered element markers.

    Draws red circles with white ID numbers at element centers.

    Args:
        img: PIL Image to annotate
        elements: List of Element objects with center property
        scale: Scale factor if image was downsampled
        circle_radius: Radius of the marker circles
        circle_color: Color of the marker circles
        text_color: Color of the ID numbers
        font_size: Size of the ID numbers

    Returns:
        Annotated copy of the image
    """
    from PIL import ImageDraw, ImageFont

    # Create a copy to avoid modifying the original
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    for idx, element in enumerate(elements, start=1):
        # Get element center, applying scale factor
        cx, cy = element.center
        cx = int(cx * scale)
        cy = int(cy * scale)

        # Ensure coordinates are within image bounds
        img_width, img_height = img.size
        cx = max(circle_radius, min(cx, img_width - circle_radius))
        cy = max(circle_radius, min(cy, img_height - circle_radius))

        # Draw circle
        bbox = [
            cx - circle_radius,
            cy - circle_radius,
            cx + circle_radius,
            cy + circle_radius
        ]
        draw.ellipse(bbox, fill=circle_color, outline="white", width=2)

        # Draw ID number centered in circle
        id_text = str(idx)

        # Get text bounding box for centering
        text_bbox = draw.textbbox((0, 0), id_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = cx - text_width // 2
        text_y = cy - text_height // 2 - 1  # Small adjustment for visual centering

        draw.text((text_x, text_y), id_text, fill=text_color, font=font)

    return annotated


def annotate_screenshot(
    img: "Image.Image",
    elements: list,
    max_width: int = 1280,
    max_height: int = 720
) -> tuple["Image.Image", "Image.Image", float]:
    """
    Downsample and annotate a screenshot with element markers.

    Args:
        img: PIL Image (original screenshot)
        elements: List of Element objects
        max_width: Maximum width for downsampled image
        max_height: Maximum height for downsampled image

    Returns:
        Tuple of (original image, annotated downsampled image, scale factor)
    """
    # Downsample
    downsampled, scale = downsample_image(img, max_width, max_height)

    # Annotate
    annotated = annotate_elements(downsampled, elements, scale)

    return img, annotated, scale
