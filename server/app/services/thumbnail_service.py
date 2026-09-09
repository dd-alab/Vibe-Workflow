import os
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import ServiceValidationError, UnsupportedMediaTypeError

SUPPORTED_FORMATS = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
}


@dataclass(frozen=True)
class ImageInfo:
    media_type: str
    canonical_extension: str
    width: int
    height: int


class ThumbnailService:
    def __init__(
        self,
        *,
        max_width: int,
        max_height: int,
        max_pixels: int,
        thumbnail_max_dimension: int,
    ) -> None:
        self.max_width = max_width
        self.max_height = max_height
        self.max_pixels = max_pixels
        self.thumbnail_max_dimension = thumbnail_max_dimension

    def inspect_and_create(
        self,
        source_path: Path,
        thumbnail_path: Path,
    ) -> ImageInfo:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(source_path) as image:
                    format_name = image.format
                    if format_name not in SUPPORTED_FORMATS:
                        raise UnsupportedMediaTypeError(
                            "Seules les images PNG, JPEG et WebP sont acceptees."
                        )
                    self._validate_dimensions(*image.size)
                    image.verify()

                with Image.open(source_path) as image:
                    image.load()
                    oriented = ImageOps.exif_transpose(image)
                    width, height = oriented.size
                    self._validate_dimensions(width, height)
                    thumbnail = oriented.copy()
                    thumbnail.thumbnail(
                        (self.thumbnail_max_dimension, self.thumbnail_max_dimension),
                        Image.Resampling.LANCZOS,
                    )
                    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                    thumbnail.convert("RGBA").save(thumbnail_path, format="PNG")
        except ServiceValidationError:
            raise
        except UnsupportedMediaTypeError:
            raise
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            raise ServiceValidationError(
                "Les dimensions de l'image depassent les limites autorisees."
            ) from error
        except (OSError, UnidentifiedImageError, ValueError) as error:
            raise UnsupportedMediaTypeError(
                "Le fichier n'est pas une image PNG, JPEG ou WebP valide."
            ) from error

        with thumbnail_path.open("r+b") as thumbnail_file:
            os.fsync(thumbnail_file.fileno())
        media_type, extension = SUPPORTED_FORMATS[format_name]
        return ImageInfo(
            media_type=media_type,
            canonical_extension=extension,
            width=width,
            height=height,
        )

    def _validate_dimensions(self, width: int, height: int) -> None:
        if (
            width > self.max_width
            or height > self.max_height
            or width * height > self.max_pixels
        ):
            raise ServiceValidationError(
                "Les dimensions de l'image depassent les limites autorisees."
            )
