import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.core.config import get_settings


class InvalidImportFileExtension(ValueError):
    pass


class ImportFileStorageError(RuntimeError):
    pass


def clean_original_filename(original_filename: str) -> str:
    filename = PureWindowsPath(original_filename).name
    filename = PurePosixPath(filename).name
    filename = filename or "companies.csv"

    if len(filename) <= 255:
        return filename

    suffix = Path(filename).suffix
    stem_limit = 255 - len(suffix)
    return f"{Path(filename).stem[:stem_limit]}{suffix}"


def _get_storage_dir() -> Path:
    settings = get_settings()
    storage_dir = Path(settings.import_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def _ensure_csv_filename(filename: str) -> None:
    if Path(filename).suffix.lower() != ".csv":
        raise InvalidImportFileExtension("Only CSV files are supported")


def store_import_file(
    file_content: bytes,
    original_filename: str,
) -> tuple[str, Path]:
    safe_original_filename = clean_original_filename(original_filename)
    _ensure_csv_filename(safe_original_filename)

    stored_filename = f"{uuid.uuid4()}.csv"

    try:
        storage_dir = _get_storage_dir()
        file_path = storage_dir / stored_filename
        file_path.write_bytes(file_content)
    except OSError as exc:
        raise ImportFileStorageError("Unable to store import file") from exc

    return stored_filename, file_path


def get_import_file_path(stored_filename: str) -> Path:
    if stored_filename != Path(stored_filename).name:
        raise ImportFileStorageError("Invalid stored filename")

    _ensure_csv_filename(stored_filename)

    storage_dir = _get_storage_dir()
    file_path = storage_dir / stored_filename
    resolved_storage_dir = storage_dir.resolve()
    resolved_file_path = file_path.resolve()

    if resolved_storage_dir not in resolved_file_path.parents:
        raise ImportFileStorageError("Invalid stored filename")

    return file_path
