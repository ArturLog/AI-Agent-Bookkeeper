import datetime
import functions_framework
from dateutil.relativedelta import relativedelta
from config import validate_config, SHIFT_HOURS
from services import DriveService, VisionService, StorageService, EmailService

class PipelineProcessor:
    """
    Orchestrates ingestion, classification, and analysis.
    """
    def __init__(self):
        self.drive = DriveService()
        self.vision = VisionService()
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

            # Check if file already exists in GCS (within this month)
            existing_path = self.storage.find_file_in_month(file_name, month_year)
            
            content = None
            category = None

            if existing_path:
                print(f"File {file_name} already exists in GCS at: {existing_path}. Skipping classification/upload.")
                # Format: {monthyear}/{category}/{filename}
                category = existing_path.split('/')[1]
                
                # We only need content if we are going to analyze it
                if category == SHIFT_HOURS:
                    content = self.drive.download_file(file_id)
            else:
                content = self.drive.download_file(file_id)
                
                category = self.vision.categorize_image(content)
                print(f"Category: {category}")
                
                self.storage.upload_image(content, file_name, category, month_year, mime_type)

            if category == SHIFT_HOURS and content:
                result = self.vision.analyze_shift_hours(content)
                all_results.append(result)
                print(f"Analysis for {file_name} completed. Found {len(result['data'])} records.")

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
            print(f"Processed {len(results)} shift-hour images.")
            for res in results:
                summary = f"Summary for {res['name']} ({res['month']} {res['year']}):\n"
                for entry in res['data']:
                    summary += f" - Day {entry['day']}: {entry['hours_decimal']}h\n"
                print(summary)

        return "Process completed successfully", 200

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        print(f"ERROR: {error_msg}")
        email_notifier.send_email(
            subject="ALERT: Monthly Financial Report Failed",
            message_body=f"Failed with error: <b>{str(e)}</b><br><br>Please check GC logs."
        )
        return f"Error: {e}", 500


# Uncomment to run locally
if __name__ == "__main__":
    try:
        validate_config()
        proc = PipelineProcessor()
        
        results = proc.run()

        if results:
            print(f"Processed {len(results)} shift-hour images.")
            for res in results:
                summary = f"Summary for {res['name']} ({res['month']} {res['year']}):\n"
                for entry in res['data']:
                    summary += f" - Day {entry['day']}: {entry['hours_decimal']}h\n"
                print(summary)
        
        print(f"Processed {len(res)} results.")
        
    except Exception as e:
        print(f"LOCAL ERROR: {e}")

