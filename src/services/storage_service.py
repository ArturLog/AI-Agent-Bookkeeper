from google.cloud import storage
from config import DATA_BUCKET

class StorageService:
    def __init__(self):
        self._client = storage.Client()
        self._bucket = self._client.bucket(DATA_BUCKET)

    def upload_image(self, content: bytes, file_name: str, category: str, month_year: str, mime_type: str) -> str:
        """
        Uploads content (image) to GCS with a structured path.
        """
        gcs_path = f"{month_year}/{category}/{file_name}"
        blob = self._bucket.blob(gcs_path)
        blob.upload_from_string(content, content_type=mime_type)
        print(f"Uploaded to GCS: {gcs_path}")
        return gcs_path

    def find_file_in_month(self, file_name: str, month_year: str) -> str:
        """
        Searches for a specific filename within a month's prefix in GCS.
        Returns the full GCS path if found, otherwise None.
        """
        prefix = f"{month_year}/"
        blobs = self._client.list_blobs(self._bucket, prefix=prefix)
        
        for blob in blobs:
            if blob.name.endswith(f"/{file_name}"):
                return blob.name
        return None

