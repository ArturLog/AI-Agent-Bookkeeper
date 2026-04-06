import datetime
import functions_framework
from dateutil.relativedelta import relativedelta
from config import validate_config, SHIFT_HOURS, SHIFT_REPORT, SPREADSHEET_ID
from services import DriveService, VisionService, LLMService, StorageService, EmailService, SheetsService
from utils.parser import convert_heic_to_jpeg

class PipelineProcessor:
    """
    Orchestrates ingestion, classification, and analysis.
    - Uses Vision API for categorization
    - Uses Gemini LLM for detailed analysis
    """
    def __init__(self):
        self.drive = DriveService()
        self.vision = VisionService()
        self.llm = LLMService()
        self.storage = StorageService()
        self.email = EmailService()

    def run(self) -> list:
        """
        Main execution pipeline.
        """
        print("Starting ingestion from Google Drive...")
        files = self.drive.list_images()

        if not files:
            print("No image files found.")
            return []

        all_results = []
        last_month = datetime.datetime.now() - relativedelta(months=1)
        month_year = last_month.strftime("%B%Y").lower()

        for file in files:
            file_id, file_name, mime_type = file['id'], file['name'], file['mimeType']
            print(f"Processing: {file_name}")

            existing_path = self.storage.find_file_in_month(file_name, month_year)
            
            content = None
            category = None

            try:
                if existing_path:
                    print(f"File {file_name} already exists in GCS at: {existing_path}. Skipping classification/upload.")
                    category = existing_path.split('/')[1]
                    
                    if category in [SHIFT_HOURS, SHIFT_REPORT]:
                        content = self.drive.download_file(file_id)
                        content = convert_heic_to_jpeg(content)
                else:
                    content = self.drive.download_file(file_id)
                    content_for_vision = convert_heic_to_jpeg(content)
                    category = self.vision.categorize_image(content_for_vision)
                    print(f"Category: {category}")
                    # Upload converted JPEG content, not original HEIC
                    upload_filename = file_name.lower().replace('.heic', '.jpeg')
                    self.storage.upload_image(content_for_vision, upload_filename, category, month_year, 'image/jpeg')
                    content = content_for_vision

                if category == SHIFT_HOURS and content:
                    result = self.llm.analyze_shift_hours(content)
                    all_results.append(result)
                    print(f"Analysis for {file_name} completed. Found {len(result['data'])} records.")
                elif category == SHIFT_REPORT and content:
                    result = self.llm.analyze_shift_report(content)
                    all_results.append(result)
                    print(f"Analysis for report {file_name} completed. Date: {result['date_str']}")
            
            except ValueError as e:
                print(f"Skipping {file_name}: {e}")
                continue

        return all_results

@functions_framework.http
def main_handler(request):
    """
    Entry point for GCF HTTP trigger.
    """
    email_notifier = EmailService()
    try:
        print("Pipeline triggered.")
        validate_config()

        email_notifier.send_email(
            subject="Monthly Financial Report - Ingestion Started",
            message_body="The <b>Automated Financial Agent</b> has started the monthly process."
        )

        processor = PipelineProcessor()
        results = processor.run()

        if results:
            hours_data = [r for r in results if r['type'] == SHIFT_HOURS]
            reports = [r for r in results if r['type'] == SHIFT_REPORT]
            
            reports.sort(key=lambda x: x['date'] if x['date'] else datetime.datetime.min)

            last_month = datetime.datetime.now() - relativedelta(months=1)
            sheet_name = last_month.strftime("%B%Y").lower()

            print(f"Processed {len(hours_data)} shift-hours files and {len(reports)} shift-reports.")

            sheets = SheetsService(SPREADSHEET_ID)
            sheets.update_monthly_sheet(sheet_name, reports, hours_data)
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
            email_notifier.send_email(
                subject=f"Monthly Report Completed - {sheet_name}",
                message_body=f"""
                Ingestion and analysis finished successfully.<br><br>
                <b>Summary:</b><br>
                - Reports found: {len(reports)}<br>
                - Employee records: {len(hours_data)}<br><br>
                View results here: <a href="{sheet_url}">Google Sheet</a>
                """
            )

        return "Process completed successfully", 200

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        print(f"ERROR: {error_msg}")
        email_notifier.send_email(
            subject="ALERT: Monthly Financial Report Failed",
            message_body=f"Failed with error: <b>{str(e)}</b><br><br>Please check Google Cloud console logs."
        )
        return f"Error: {e}", 500

# Local execution
if __name__ == "__main__":
    try:
        validate_config()
        proc = PipelineProcessor()
        results = proc.run()

        if results:
            hours_data = [r for r in results if r['type'] == SHIFT_HOURS]
            reports = [r for r in results if r['type'] == SHIFT_REPORT]
            reports.sort(key=lambda x: x['date'] if x['date'] else datetime.datetime.min)

            last_month = datetime.datetime.now() - relativedelta(months=1)
            sheet_name = last_month.strftime("%B%Y").lower()

            sheets = SheetsService(SPREADSHEET_ID)
            sheets.update_monthly_sheet(sheet_name, reports, hours_data)
            print(f"DONE locally. Sheet '{sheet_name}' updated.")
        
    except Exception as e:
        print(f"LOCAL ERROR: {e}")

