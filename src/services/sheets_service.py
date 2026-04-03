import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class SheetsService:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self._service = build('sheets', 'v4')

    def update_monthly_sheet(self, sheet_name, reports, hours_data):
        """
        Creates/updates a sheet with report and hours data combined.
        Columns: Day, Tips, 23%, 8%, Netto Sum, [Employee Names...]
        """
        try:
            spreadsheet = self._service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_id = None
            for s in sheets:
                if s['properties']['title'] == sheet_name:
                    sheet_id = s['properties']['sheetId']
                    break

            if sheet_id is not None:
                self._service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=sheet_name
                ).execute()
            else:
                body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {'title': sheet_name}
                        }
                    }]
                }
                res = self._service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=body
                ).execute()
                sheet_id = res['replies'][0]['addSheet']['properties']['sheetId']

            employees = sorted(list(set(h['name'] for h in hours_data)))
            
            header = ["Day", "Tips", "Netto 23%", "Netto 8%", "Total Netto"] + employees
            
            rows = [header]
            for day in range(1, 32):
                row = [day, 0.0, 0.0, 0.0, 0.0] + [0.0] * len(employees)
                
                day_reports = [r for r in reports if r['date'] and r['date'].day == day]
                if day_reports:
                    unique_reports = []
                    seen_sigs = set()
                    for r in day_reports:
                        sig = (r['date_str'], r['netto_sum'], r['tips'])
                        if sig not in seen_sigs:
                            unique_reports.append(r)
                            seen_sigs.add(sig)
                    
                    row[1] = sum(r['tips'] for r in unique_reports)
                    row[2] = sum(r['netto_23'] for r in unique_reports)
                    row[3] = sum(r['netto_8'] for r in unique_reports)
                    row[4] = sum(r['netto_sum'] for r in unique_reports)
                
                for i, emp_name in enumerate(employees):
                    emp_hours = [h for h in hours_data if h['name'] == emp_name]
                    for entry in emp_hours:
                        for shift in entry['data']:
                            if shift['day'] == day:
                                row[5 + i] += shift['hours_decimal']
                
                if any(v > 0 for v in row[1:]):
                    rows.append(row)

            body = {'values': rows}
            self._service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body=body
            ).execute()
            
            format_body = {
                'requests': [{
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {'bold': True},
                                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                }]
            }
            self._service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=format_body
            ).execute()

            print(f"Successfully updated sheet: {sheet_name}")

        except HttpError as err:
            print(f"Sheets API Error: {err}")
            raise
