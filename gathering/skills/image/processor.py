"""
Image Skill for GatheRing.
Provides image manipulation and processing using Pillow.
"""

import os
import io
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class ImageSkill(BaseSkill):
    """
    Skill for image manipulation and processing.

    Features:
    - Resize, crop, rotate images
    - Format conversion
    - Filters and effects
    - Text and watermarks
    - Image information extraction
    - Thumbnail generation

    Security:
    - Configurable allowed paths
    - File size limits
    - Format validation
    """

    name = "image"
    description = "Image manipulation and processing"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ, SkillPermission.WRITE]

    SUPPORTED_FORMATS = {"JPEG", "PNG", "GIF", "BMP", "WEBP", "TIFF", "ICO"}
    MAX_FILE_SIZE_MB = 50  # Maximum file size

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.allowed_paths = self.config.get("allowed_paths", []) if self.config else []
        self.max_size_mb = self.config.get("max_size_mb", self.MAX_FILE_SIZE_MB) if self.config else self.MAX_FILE_SIZE_MB

    def _check_path(self, path: str) -> bool:
        """Check if path is allowed."""
        if not self.allowed_paths:
            return True
        return any(path.startswith(p) for p in self.allowed_paths)

    def _check_file_size(self, path: str) -> bool:
        """Check if file size is within limits."""
        if not os.path.exists(path):
            return True
        size_mb = os.path.getsize(path) / (1024 * 1024)
        return size_mb <= self.max_size_mb

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "image_info",
                "description": "Get information about an image",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "image_resize",
                "description": "Resize an image",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path (optional, overwrites if not specified)"
                        },
                        "width": {
                            "type": "integer",
                            "description": "Target width in pixels"
                        },
                        "height": {
                            "type": "integer",
                            "description": "Target height in pixels"
                        },
                        "maintain_aspect": {
                            "type": "boolean",
                            "description": "Maintain aspect ratio",
                            "default": True
                        },
                        "resample": {
                            "type": "string",
                            "description": "Resampling filter",
                            "enum": ["nearest", "bilinear", "bicubic", "lanczos"],
                            "default": "lanczos"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "image_crop",
                "description": "Crop an image",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path"
                        },
                        "left": {
                            "type": "integer",
                            "description": "Left coordinate"
                        },
                        "top": {
                            "type": "integer",
                            "description": "Top coordinate"
                        },
                        "right": {
                            "type": "integer",
                            "description": "Right coordinate"
                        },
                        "bottom": {
                            "type": "integer",
                            "description": "Bottom coordinate"
                        }
                    },
                    "required": ["path", "left", "top", "right", "bottom"]
                }
            },
            {
                "name": "image_rotate",
                "description": "Rotate an image",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path"
                        },
                        "angle": {
                            "type": "number",
                            "description": "Rotation angle in degrees (counter-clockwise)"
                        },
                        "expand": {
                            "type": "boolean",
                            "description": "Expand canvas to fit rotated image",
                            "default": True
                        },
                        "fill_color": {
                            "type": "string",
                            "description": "Fill color for empty areas (hex or name)",
                            "default": "white"
                        }
                    },
                    "required": ["path", "angle"]
                }
            },
            {
                "name": "image_convert",
                "description": "Convert image format",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path (format determined by extension)"
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format",
                            "enum": ["JPEG", "PNG", "GIF", "BMP", "WEBP", "TIFF", "ICO"]
                        },
                        "quality": {
                            "type": "integer",
                            "description": "Quality for lossy formats (1-100)",
                            "default": 85
                        }
                    },
                    "required": ["path", "output"]
                }
            },
            {
                "name": "image_filter",
                "description": "Apply filter to image",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path"
                        },
                        "filter": {
                            "type": "string",
                            "description": "Filter to apply",
                            "enum": ["blur", "sharpen", "contour", "detail", "edge_enhance", "emboss", "smooth", "grayscale", "sepia", "invert"]
                        },
                        "intensity": {
                            "type": "number",
                            "description": "Filter intensity (0-1 for some filters)",
                            "default": 1.0
                        }
                    },
                    "required": ["path", "filter"]
                }
            },
            {
                "name": "image_adjust",
                "description": "Adjust image properties",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path"
                        },
                        "brightness": {
                            "type": "number",
                            "description": "Brightness factor (1.0 = original)"
                        },
                        "contrast": {
                            "type": "number",
                            "description": "Contrast factor (1.0 = original)"
                        },
                        "saturation": {
                            "type": "number",
                            "description": "Saturation factor (1.0 = original)"
                        },
                        "sharpness": {
                            "type": "number",
                            "description": "Sharpness factor (1.0 = original)"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "image_thumbnail",
                "description": "Create a thumbnail",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path"
                        },
                        "size": {
                            "type": "integer",
                            "description": "Maximum dimension (width or height)",
                            "default": 128
                        }
                    },
                    "required": ["path", "output"]
                }
            },
            {
                "name": "image_watermark",
                "description": "Add text or image watermark",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path"
                        },
                        "text": {
                            "type": "string",
                            "description": "Watermark text"
                        },
                        "watermark_image": {
                            "type": "string",
                            "description": "Path to watermark image (alternative to text)"
                        },
                        "position": {
                            "type": "string",
                            "description": "Watermark position",
                            "enum": ["top-left", "top-right", "bottom-left", "bottom-right", "center"],
                            "default": "bottom-right"
                        },
                        "opacity": {
                            "type": "number",
                            "description": "Watermark opacity (0-1)",
                            "default": 0.5
                        },
                        "font_size": {
                            "type": "integer",
                            "description": "Font size for text watermark",
                            "default": 24
                        },
                        "color": {
                            "type": "string",
                            "description": "Text color (hex or name)",
                            "default": "white"
                        }
                    },
                    "required": ["path", "output"]
                }
            },
            {
                "name": "image_compose",
                "description": "Compose multiple images",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "images": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Paths to images to compose"
                        },
                        "output": {
                            "type": "string",
                            "description": "Output path"
                        },
                        "layout": {
                            "type": "string",
                            "description": "Layout mode",
                            "enum": ["horizontal", "vertical", "grid", "overlay"],
                            "default": "horizontal"
                        },
                        "gap": {
                            "type": "integer",
                            "description": "Gap between images in pixels",
                            "default": 0
                        },
                        "background": {
                            "type": "string",
                            "description": "Background color",
                            "default": "white"
                        }
                    },
                    "required": ["images", "output"]
                }
            },
            {
                "name": "image_to_base64",
                "description": "Convert image to base64 string",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the image file"
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format",
                            "enum": ["JPEG", "PNG", "WEBP"],
                            "default": "PNG"
                        }
                    },
                    "required": ["path"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute image tool."""
        try:
            from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont  # noqa: F401

            path = tool_input.get("path")

            # Path validation
            if path and not self._check_path(path):
                return SkillResponse(
                    success=False,
                    message=f"Path not allowed: {path}",
                    error="access_denied"
                )

            if path and not self._check_file_size(path):
                return SkillResponse(
                    success=False,
                    message=f"File too large (max {self.max_size_mb}MB)",
                    error="file_too_large"
                )

            if tool_name == "image_info":
                return self._get_info(path)
            elif tool_name == "image_resize":
                return self._resize(tool_input)
            elif tool_name == "image_crop":
                return self._crop(tool_input)
            elif tool_name == "image_rotate":
                return self._rotate(tool_input)
            elif tool_name == "image_convert":
                return self._convert(tool_input)
            elif tool_name == "image_filter":
                return self._apply_filter(tool_input)
            elif tool_name == "image_adjust":
                return self._adjust(tool_input)
            elif tool_name == "image_thumbnail":
                return self._thumbnail(tool_input)
            elif tool_name == "image_watermark":
                return self._watermark(tool_input)
            elif tool_name == "image_compose":
                return self._compose(tool_input)
            elif tool_name == "image_to_base64":
                return self._to_base64(tool_input)
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool"
                )

        except ImportError as e:
            return SkillResponse(
                success=False,
                message=f"Pillow not installed: {e}. Install: pip install Pillow",
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Image tool error: {e}")
            return SkillResponse(
                success=False,
                message=f"Image operation failed: {str(e)}",
                error=str(e)
            )

    def _get_info(self, path: str) -> SkillResponse:
        """Get image information."""
        from PIL import Image
        from PIL.ExifTags import TAGS

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"File not found: {path}",
                error="not_found"
            )

        with Image.open(path) as img:
            info = {
                "path": path,
                "format": img.format,
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
                "size_bytes": os.path.getsize(path),
                "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
            }

            # Get EXIF data if available
            exif = {}
            if hasattr(img, "_getexif") and img._getexif():
                for tag_id, value in img._getexif().items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, bytes):
                        continue
                    exif[tag] = str(value)[:100]  # Limit value length

            if exif:
                info["exif"] = exif

            # Animation info
            if hasattr(img, "n_frames"):
                info["frames"] = img.n_frames
                info["is_animated"] = img.n_frames > 1

        return SkillResponse(
            success=True,
            message=f"Image: {info['width']}x{info['height']} {info['format']}",
            data=info
        )

    def _resize(self, params: Dict[str, Any]) -> SkillResponse:
        """Resize image."""
        from PIL import Image

        path = params["path"]
        output = params.get("output", path)
        width = params.get("width")
        height = params.get("height")
        maintain_aspect = params.get("maintain_aspect", True)
        resample = params.get("resample", "lanczos")

        resample_filters = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "bicubic": Image.Resampling.BICUBIC,
            "lanczos": Image.Resampling.LANCZOS,
        }

        with Image.open(path) as img:
            original_size = img.size

            if maintain_aspect:
                if width and height:
                    img.thumbnail((width, height), resample_filters[resample])
                elif width:
                    ratio = width / img.width
                    height = int(img.height * ratio)
                    img = img.resize((width, height), resample_filters[resample])
                elif height:
                    ratio = height / img.height
                    width = int(img.width * ratio)
                    img = img.resize((width, height), resample_filters[resample])
            else:
                if width and height:
                    img = img.resize((width, height), resample_filters[resample])

            img.save(output)

        return SkillResponse(
            success=True,
            message=f"Resized from {original_size} to {img.size}",
            data={"output": output, "original_size": original_size, "new_size": img.size}
        )

    def _crop(self, params: Dict[str, Any]) -> SkillResponse:
        """Crop image."""
        from PIL import Image

        path = params["path"]
        output = params.get("output", path)

        with Image.open(path) as img:
            box = (params["left"], params["top"], params["right"], params["bottom"])
            cropped = img.crop(box)
            cropped.save(output)

        return SkillResponse(
            success=True,
            message=f"Cropped to {cropped.size[0]}x{cropped.size[1]}",
            data={"output": output, "size": cropped.size, "crop_box": box}
        )

    def _rotate(self, params: Dict[str, Any]) -> SkillResponse:
        """Rotate image."""
        from PIL import Image

        path = params["path"]
        output = params.get("output", path)
        angle = params["angle"]
        expand = params.get("expand", True)
        fill_color = params.get("fill_color", "white")

        with Image.open(path) as img:
            rotated = img.rotate(angle, expand=expand, fillcolor=fill_color)
            rotated.save(output)

        return SkillResponse(
            success=True,
            message=f"Rotated {angle} degrees",
            data={"output": output, "angle": angle, "size": rotated.size}
        )

    def _convert(self, params: Dict[str, Any]) -> SkillResponse:
        """Convert image format."""
        from PIL import Image

        path = params["path"]
        output = params["output"]
        format_name = params.get("format")
        quality = params.get("quality", 85)

        # Determine format from extension if not specified
        if not format_name:
            ext = Path(output).suffix.upper().lstrip(".")
            if ext == "JPG":
                ext = "JPEG"
            format_name = ext

        with Image.open(path) as img:
            # Convert mode if necessary for JPEG
            if format_name == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            save_kwargs = {}
            if format_name in ("JPEG", "WEBP"):
                save_kwargs["quality"] = quality

            img.save(output, format=format_name, **save_kwargs)

        return SkillResponse(
            success=True,
            message=f"Converted to {format_name}",
            data={"output": output, "format": format_name}
        )

    def _apply_filter(self, params: Dict[str, Any]) -> SkillResponse:
        """Apply filter to image."""
        from PIL import Image, ImageFilter, ImageOps

        path = params["path"]
        output = params.get("output", path)
        filter_name = params["filter"]
        intensity = params.get("intensity", 1.0)

        with Image.open(path) as img:
            if filter_name == "blur":
                filtered = img.filter(ImageFilter.GaussianBlur(radius=intensity * 5))
            elif filter_name == "sharpen":
                filtered = img.filter(ImageFilter.SHARPEN)
            elif filter_name == "contour":
                filtered = img.filter(ImageFilter.CONTOUR)
            elif filter_name == "detail":
                filtered = img.filter(ImageFilter.DETAIL)
            elif filter_name == "edge_enhance":
                filtered = img.filter(ImageFilter.EDGE_ENHANCE)
            elif filter_name == "emboss":
                filtered = img.filter(ImageFilter.EMBOSS)
            elif filter_name == "smooth":
                filtered = img.filter(ImageFilter.SMOOTH)
            elif filter_name == "grayscale":
                filtered = ImageOps.grayscale(img)
            elif filter_name == "sepia":
                # Apply sepia effect
                gray = ImageOps.grayscale(img)
                sepia = Image.merge("RGB", (
                    gray.point(lambda x: min(255, x + 40)),
                    gray.point(lambda x: min(255, x + 20)),
                    gray,
                ))
                filtered = sepia
            elif filter_name == "invert":
                if img.mode == "RGBA":
                    r, g, b, a = img.split()
                    rgb = Image.merge("RGB", (r, g, b))
                    inverted = ImageOps.invert(rgb)
                    r, g, b = inverted.split()
                    filtered = Image.merge("RGBA", (r, g, b, a))
                else:
                    filtered = ImageOps.invert(img.convert("RGB"))
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown filter: {filter_name}",
                    error="unknown_filter"
                )

            filtered.save(output)

        return SkillResponse(
            success=True,
            message=f"Applied {filter_name} filter",
            data={"output": output, "filter": filter_name}
        )

    def _adjust(self, params: Dict[str, Any]) -> SkillResponse:
        """Adjust image properties."""
        from PIL import Image, ImageEnhance

        path = params["path"]
        output = params.get("output", path)

        with Image.open(path) as img:
            if params.get("brightness"):
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(params["brightness"])

            if params.get("contrast"):
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(params["contrast"])

            if params.get("saturation"):
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(params["saturation"])

            if params.get("sharpness"):
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(params["sharpness"])

            img.save(output)

        adjustments = {k: v for k, v in params.items() if k in ["brightness", "contrast", "saturation", "sharpness"] and v}

        return SkillResponse(
            success=True,
            message=f"Adjusted {', '.join(adjustments.keys())}",
            data={"output": output, "adjustments": adjustments}
        )

    def _thumbnail(self, params: Dict[str, Any]) -> SkillResponse:
        """Create thumbnail."""
        from PIL import Image

        path = params["path"]
        output = params["output"]
        size = params.get("size", 128)

        with Image.open(path) as img:
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            img.save(output)

        return SkillResponse(
            success=True,
            message=f"Thumbnail created: {img.size}",
            data={"output": output, "size": img.size}
        )

    def _watermark(self, params: Dict[str, Any]) -> SkillResponse:
        """Add watermark to image."""
        from PIL import Image, ImageDraw, ImageFont

        path = params["path"]
        output = params["output"]
        text = params.get("text")
        watermark_image = params.get("watermark_image")
        position = params.get("position", "bottom-right")
        opacity = params.get("opacity", 0.5)
        font_size = params.get("font_size", 24)
        color = params.get("color", "white")

        with Image.open(path) as img:
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            if text:
                # Text watermark
                txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(txt_layer)

                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except (IOError, OSError):
                    font = ImageFont.load_default()

                # Get text size
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Calculate position
                padding = 10
                positions = {
                    "top-left": (padding, padding),
                    "top-right": (img.width - text_width - padding, padding),
                    "bottom-left": (padding, img.height - text_height - padding),
                    "bottom-right": (img.width - text_width - padding, img.height - text_height - padding),
                    "center": ((img.width - text_width) // 2, (img.height - text_height) // 2),
                }

                pos = positions.get(position, positions["bottom-right"])
                alpha = int(255 * opacity)

                # Parse color
                if color.startswith("#"):
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                    fill = (r, g, b, alpha)
                else:
                    fill = (*ImageDraw.Draw(Image.new("RGB", (1, 1))).textcolor, alpha)

                draw.text(pos, text, font=font, fill=fill)
                img = Image.alpha_composite(img, txt_layer)

            elif watermark_image:
                # Image watermark
                with Image.open(watermark_image) as wm:
                    if wm.mode != "RGBA":
                        wm = wm.convert("RGBA")

                    # Apply opacity
                    wm_with_opacity = wm.copy()
                    alpha = wm_with_opacity.split()[3]
                    alpha = alpha.point(lambda p: int(p * opacity))
                    wm_with_opacity.putalpha(alpha)

                    # Calculate position
                    padding = 10
                    positions = {
                        "top-left": (padding, padding),
                        "top-right": (img.width - wm.width - padding, padding),
                        "bottom-left": (padding, img.height - wm.height - padding),
                        "bottom-right": (img.width - wm.width - padding, img.height - wm.height - padding),
                        "center": ((img.width - wm.width) // 2, (img.height - wm.height) // 2),
                    }

                    pos = positions.get(position, positions["bottom-right"])
                    img.paste(wm_with_opacity, pos, wm_with_opacity)

            img.save(output)

        return SkillResponse(
            success=True,
            message="Watermark added",
            data={"output": output, "position": position}
        )

    def _compose(self, params: Dict[str, Any]) -> SkillResponse:
        """Compose multiple images."""
        from PIL import Image

        images = params["images"]
        output = params["output"]
        layout = params.get("layout", "horizontal")
        gap = params.get("gap", 0)
        background = params.get("background", "white")

        # Load all images
        imgs = [Image.open(p) for p in images]

        try:
            if layout == "horizontal":
                total_width = sum(img.width for img in imgs) + gap * (len(imgs) - 1)
                max_height = max(img.height for img in imgs)
                result = Image.new("RGB", (total_width, max_height), background)

                x = 0
                for img in imgs:
                    result.paste(img, (x, (max_height - img.height) // 2))
                    x += img.width + gap

            elif layout == "vertical":
                max_width = max(img.width for img in imgs)
                total_height = sum(img.height for img in imgs) + gap * (len(imgs) - 1)
                result = Image.new("RGB", (max_width, total_height), background)

                y = 0
                for img in imgs:
                    result.paste(img, ((max_width - img.width) // 2, y))
                    y += img.height + gap

            elif layout == "grid":
                import math
                cols = math.ceil(math.sqrt(len(imgs)))
                rows = math.ceil(len(imgs) / cols)
                cell_width = max(img.width for img in imgs)
                cell_height = max(img.height for img in imgs)

                result = Image.new("RGB", (
                    cols * cell_width + (cols - 1) * gap,
                    rows * cell_height + (rows - 1) * gap
                ), background)

                for i, img in enumerate(imgs):
                    row = i // cols
                    col = i % cols
                    x = col * (cell_width + gap) + (cell_width - img.width) // 2
                    y = row * (cell_height + gap) + (cell_height - img.height) // 2
                    result.paste(img, (x, y))

            elif layout == "overlay":
                # Stack images on top of each other
                max_width = max(img.width for img in imgs)
                max_height = max(img.height for img in imgs)
                result = Image.new("RGBA", (max_width, max_height), background)

                for img in imgs:
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    x = (max_width - img.width) // 2
                    y = (max_height - img.height) // 2
                    result.paste(img, (x, y), img)

            result.save(output)

        finally:
            for img in imgs:
                img.close()

        return SkillResponse(
            success=True,
            message=f"Composed {len(images)} images ({layout})",
            data={"output": output, "layout": layout, "size": result.size}
        )

    def _to_base64(self, params: Dict[str, Any]) -> SkillResponse:
        """Convert image to base64."""
        from PIL import Image

        path = params["path"]
        format_name = params.get("format", "PNG")

        with Image.open(path) as img:
            buffer = io.BytesIO()

            if format_name == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.save(buffer, format=format_name)
            b64 = base64.b64encode(buffer.getvalue()).decode()

        mime_types = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }

        return SkillResponse(
            success=True,
            message=f"Converted to base64 ({len(b64)} chars)",
            data={
                "base64": b64,
                "data_uri": f"data:{mime_types.get(format_name, 'image/png')};base64,{b64}",
                "format": format_name,
                "size_bytes": len(b64),
            }
        )
