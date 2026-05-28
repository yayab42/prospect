from fastapi import UploadFile


MAX_CSV_SIZE_BYTES = 1024 * 1024


class UnsupportedCSVFile(ValueError):
    pass


class CSVFileTooLarge(ValueError):
    pass


async def read_csv_upload_file(file: UploadFile) -> bytes:
    if file.filename is None or not file.filename.lower().endswith(".csv"):
        raise UnsupportedCSVFile("Only CSV files are supported")

    file_content = await file.read(MAX_CSV_SIZE_BYTES + 1)

    if len(file_content) > MAX_CSV_SIZE_BYTES:
        raise CSVFileTooLarge("CSV file is too large")

    return file_content
