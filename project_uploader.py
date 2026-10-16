
import shutil
import tempfile
import zipfile
from pathlib import Path


MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_EXTRACTED_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_FILES = 5000


def extract_python_project(uploaded_file):
    """Safely extract a ZIP containing Python source files."""
    if uploaded_file.size > MAX_ZIP_SIZE:
        raise ValueError("ZIP file must be 50 MB or smaller.")

    temp_dir = Path(tempfile.mkdtemp(prefix="reposage_"))

    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            entries = archive.infolist()

            if len(entries) > MAX_FILES:
                raise ValueError("ZIP contains too many files.")

            total_size = sum(entry.file_size for entry in entries)
            if total_size > MAX_EXTRACTED_SIZE:
                raise ValueError(
                    "Extracted project exceeds the 200 MB limit."
                )

            root = temp_dir.resolve()

            for entry in entries:
                destination = (temp_dir / entry.filename).resolve()

                # Prevent ZIP path traversal.
                if destination != root and root not in destination.parents:
                    raise ValueError(
                        "ZIP contains an unsafe file path."
                    )

                # Reject symbolic links.
                unix_mode = entry.external_attr >> 16
                if (unix_mode & 0o170000) == 0o120000:
                    raise ValueError(
                        "ZIP contains a symbolic link."
                    )

            archive.extractall(temp_dir)

        python_files = list(temp_dir.rglob("*.py"))

        if not python_files:
            raise ValueError(
                "No Python files were found in the ZIP."
            )

        return temp_dir

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
