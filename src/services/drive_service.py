import io
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from config import GOOGLE_DRIVE_FOLDER_ID

class DriveService:
    def __init__(self):
        self._service = self._get_drive_service()

    def _get_drive_service(self):
        """
        Initializes Google Drive service.
        """
        credentials, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        return build('drive', 'v3', credentials=credentials)

    def list_images(self, folder_id: str = None) -> list:
        """
        Lists image files in a Google Drive folder, including standard formats and HEIC.
        """
        folder_id = folder_id or GOOGLE_DRIVE_FOLDER_ID
        if not folder_id:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID")

        results = self._service.files().list(
            q=f"'{folder_id}' in parents and (mimeType contains 'image/' or mimeType='image/heic' or name contains '.heic')",
            fields="files(id, name, mimeType)"
        ).execute()
        return results.get('files', [])

    def download_file(self, file_id: str) -> bytes:
        """
        Downloads a file from Google Drive.
        """
        request = self._service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return file_content.getvalue()
