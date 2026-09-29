"""Managed immutable portraits with self-contained SQLite backup storage."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

PORTRAIT_NAME = re.compile(r"[0-9a-f]{64}\.png\Z")


def valid_reference(value):
    return value == "" or bool(PORTRAIT_NAME.fullmatch(value))


class Assets:
    def __init__(self, database):
        self.database = database
        self.folder = Path(str(database.path) + ".assets")

    def import_image(self, source):
        """Normalize a copy to a bounded PNG; never change the user's original."""
        source = Path(source)
        if source.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Choose a portrait smaller than 20 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(source) as image:
                    if image.width * image.height > 20_000_000:
                        raise ValueError("Choose a portrait smaller than 20 megapixels.")
                    image = ImageOps.exif_transpose(image).convert("RGBA")
                    image.thumbnail((1024, 1024))
                    output = BytesIO()
                    image.save(output, format="PNG")
                    content = output.getvalue()
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ValueError("This file is not a supported, safely sized image.") from error
        filename = sha256(content).hexdigest() + ".png"
        # Commit bytes first; a folder-write failure cannot lose the image.
        with self.database.connection:
            self.database.connection.execute("INSERT OR IGNORE INTO portrait_assets VALUES (?,?)", (filename, content))
        self.resolve(filename)
        return filename

    def resolve(self, filename):
        """Rebuild a missing cache copy after restoration, or return no image."""
        if not filename or not valid_reference(filename):
            return None
        row = self.database.connection.execute("SELECT content FROM portrait_assets WHERE filename=?", (filename,)).fetchone()
        if row is None:
            return None
        content = bytes(row["content"])
        if len(content) > 20 * 1024 * 1024 or sha256(content).hexdigest() + ".png" != filename:
            return None
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / filename
        # SQLite is authoritative; never use an externally modified cache file.
        if not path.exists() or sha256(path.read_bytes()).hexdigest() + ".png" != filename:
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(content)
            temporary.replace(path)
        return path

    def thumbnail(self, filename, size=(150, 150)):
        try:
            path = self.resolve(filename)
            if path is None:
                return None
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path) as image:
                    if image.width * image.height > 20_000_000:
                        return None
                    image.thumbnail(size)
                    return image.copy()
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            return None
