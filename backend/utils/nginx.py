from pathlib import PurePath
from typing import Any
from urllib.parse import quote

from anyio import Path
from fastapi.responses import Response


class FileRedirectResponse(Response):
    """Response class for serving a file download by using the X-Accel-Redirect header."""

    def __init__(
        self,
        *,
        download_path: Path | PurePath,
        filename: str | None = None,
        disposition: str = "attachment",
        **kwargs: Any,
    ):
        """
        Arguments:
          - download_path: Path to the file to be served. Only its name and string
              form are read, so either flavour of Path works.
          - filename: Name of the file to be served. If not provided, the file name from the
              download_path is used.
          - disposition: "attachment" (default) forces a download; "inline" lets the
              browser render/stream the file (required for <audio> to issue Range
              requests and seek). Nginx itself still handles the Range parsing.
        """
        media_type = kwargs.pop("media_type", "application/octet-stream")
        filename = filename or download_path.name
        kwargs.setdefault("headers", {}).update(
            {
                "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename)}; filename=\"{quote(filename)}\"",
                "X-Accel-Redirect": quote(str(download_path)),
            }
        )

        super().__init__(media_type=media_type, **kwargs)
