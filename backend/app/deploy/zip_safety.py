"""
Safe ZIP extraction for uploaded website archives.

A ZIP is untrusted input from the moment it's uploaded. This module
rejects anything that could escape the extraction directory (path
traversal, absolute paths, symlinks) and enforces configurable size/
count limits -- all *before* extracting a single byte, so a malicious
or oversized archive never partially writes to disk.
"""

import stat
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, status

from app.config import settings


def validate_and_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """
    Safely extract `zip_path` into `dest_dir` (which must already
    exist). Raises HTTPException(400) with a specific reason on any
    unsafe or oversized entry, before writing anything.
    """
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive",
        )

    with zf:
        infos = zf.infolist()

        if len(infos) == 0:
            raise HTTPException(status_code=400, detail="ZIP archive is empty")
        if len(infos) > settings.max_website_files:
            raise HTTPException(
                status_code=400,
                detail=f"ZIP contains too many files (max {settings.max_website_files})",
            )

        safe_members = []
        total_uncompressed = 0

        for info in infos:
            name = info.filename

            if not name or name.strip() in (".", ""):
                continue

            # Reject absolute paths (both Unix "/etc/passwd" and
            # Windows "C:\..." / "\..." style).
            if name.startswith("/") or name.startswith("\\"):
                raise HTTPException(400, f"ZIP entry has an absolute path: {name}")
            if len(name) > 1 and name[1] == ":":
                raise HTTPException(400, f"ZIP entry has a drive path: {name}")
            if "\\" in name:
                raise HTTPException(400, f"ZIP entry contains a backslash: {name}")

            # Reject any ".." path component -- belt-and-suspenders on
            # top of the containment check below.
            parts = PurePosixPath(name).parts
            if ".." in parts:
                raise HTTPException(400, f"ZIP entry attempts path traversal: {name}")

            # Reject symlinks. The upper 16 bits of external_attr hold
            # the Unix file mode when the archive was created on a
            # Unix system (zero on most Windows-created archives, so
            # this check is a no-op but harmless there).
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if unix_mode and stat.S_ISLNK(unix_mode):
                raise HTTPException(400, f"ZIP entry is a symlink, which is not allowed: {name}")

            # The real traversal guard: the resolved destination must
            # stay inside dest_dir no matter what the name looks like.
            target = (dest_dir / name).resolve()
            if target != dest_dir and dest_dir not in target.parents:
                raise HTTPException(400, f"ZIP entry escapes the extraction directory: {name}")

            total_uncompressed += info.file_size
            if total_uncompressed > settings.max_website_extracted_size_bytes:
                raise HTTPException(
                    400,
                    "ZIP extracted size exceeds the allowed limit "
                    f"({settings.max_website_extracted_size_bytes} bytes)",
                )

            safe_members.append(info)

        for info in safe_members:
            zf.extract(info, dest_dir)
