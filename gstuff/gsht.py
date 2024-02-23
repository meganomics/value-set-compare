from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging


logger = logging.getLogger(__name__)


class GSManager:

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)
        logger.info(f'GSManager initialized with credentials: {self.credentials}')

    def get_workbook(self, file_id):
        logger.info(f'Getting workbook with id: {file_id}')
        return Workbook(file_id, self.service)

    def create_vs_workbook(self, name, vs_kind, desc_vals, cont_vals):
        """Create a workbook with two sheets and return it.
            The first sheet is called "Description" and it contains the general desription of the value set in the form
            of name (column A) and value (column B) pairs.
            The second sheet is named based on the type of ValueSet being created and contains the values (concepts) of
            the ValueSet.
            Parameters
                "name": The name that will be given to this Workbook (Google Sheet).
                "vs_kind": The type of ValueSet being created. Valid values are "concepts" "drugs" and "subsets".
                "desc_vals": A list of lists containing the name and value pairs for the first sheet.
                "cont_vals": A list of lists containing the values (concepts) for the second sheet. The contents vary
                based on the type of ValueSet being created.
        """
        try:
            spreadsheet = {
                'properties': {
                    'title': name
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'Description'
                        }
                    },
                    {
                        'properties': {
                            'title': vs_kind.capitalize()
                        }
                    }
                ]
            }
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')

            data = [
                {
                    'range': 'Description',
                    'values': desc_vals
                },
                {
                    'range': vs_kind.capitalize(),
                    'values': cont_vals
                }
            ]
            body = {
                'valueInputOption': 'RAW',
                'data': data
            }
            result = self.service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

            return self.get_workbook(spreadsheet_id)

        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return None


class Workbook:

    def __init__(self, file_id, sheets_service):
        self.service = sheets_service
        self.file_id = file_id
        self.name = ''
        self.sheets = {}
        try:
            metadata = self.service.spreadsheets().get(spreadsheetId=self.file_id).execute()
            self.name = metadata.get('properties', '').get('title', '')
            sheets = metadata.get('sheets', [])
            for sheet in sheets:
                sheet_properties = sheet.get('properties', {})
                sheet_title = sheet_properties.get('title')
                self.sheets[sheet_title] = Sheet(self, sheet_title)
        except HttpError as error:
            logger.error(f'An error occurred while initializing Workbook: {error}')
        logger.debug(f'Workbook ({self.name}) initialized. Workbook id: {self.file_id}')

    def sheet_names(self):
        return [sheet for sheet in self.sheets]

    def add_sheet(self, name):
        if name in self.sheet_names():
            logger.warning(f"Sheet '{name}' already exists in workbook '{self.name}'")
            return
        try:
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': name,
                        'gridProperties': {
                            'rowCount': 100,
                            'columnCount': 4
                        }
                    }
                }
            }]
            body = {
                'requests': requests
            }
            response = self.service.spreadsheets().batchUpdate(spreadsheetId=self.file_id, body=body).execute()
            self._refresh_sheets()

        except HttpError as error:
            logger.error(f'An error occurred when adding a sheet: {error}')

    def get_or_create_sheet(self, name):
        logger.debug(f'get_or_create_sheet: {name} for workbook {self.name}')
        if name not in self.sheet_names():
            self.add_sheet(name)
        return self.sheets[name]

    def get_sheet(self, name, header_row=-1, data_name_row=-1):
        sheet = self.sheets.get(name)
        if header_row >= 0:
            sheet.set_header_row(header_row)
        if data_name_row >= 0:
            sheet.set_data_name_row(data_name_row)
        return self.sheets.get(name)

    def _refresh_sheets(self):
        self.sheets = {}
        try:
            metadata = self.service.spreadsheets().get(spreadsheetId=self.file_id).execute()
            sheets = metadata.get('sheets', [])
            for sheet in sheets:
                sheet_properties = sheet.get('properties', {})
                sheet_title = sheet_properties.get('title')
                self.sheets[sheet_title] = Sheet(self, sheet_title)
        except HttpError as error:
            logger.error(f'An error occurred while refreshing sheets: {error}')

    def get_sheet_names(self):
        self.sheet_names = []
        metadata = self.service.spreadsheets().get(spreadsheetId=self.file_id).execute()
        sheets = metadata.get('sheets', [])
        for sheet in sheets:
            sheet_properties = sheet.get('properties', {})
            sheet_title = sheet_properties.get('title')
            self.sheet_names.append(sheet_title)
        return self.sheet_names

    def append_row_to_sheet(self, sheet_name, values):
        sheet = self.get_or_create_sheet(sheet_name)
        sheet.append_row(values)
        sheet.save()


class Sheet:

    def __init__(self, wb, name, missing_default=''):
        """header_row and data_name_row are 0-based indexes. -1 means no header or data names"""
        self.wb = wb
        self.name = name
        self.rows = 0
        self.cols = 0
        self._raw_sheet = self.wb.service.spreadsheets().values().get(spreadsheetId=wb.file_id, range=self.name).execute()
        self.values = self._raw_sheet.get('values', [])
        self.rows = len(self.values)
        self.header = []
        self.data_names = []
        self.col_names = {}
        for r in self.values:
            self.cols = max(self.cols, len(r))
        for r in self.values:
            while len(r) < self.cols:
                r.append(missing_default)

    def set_header_row(self, row):
        if -1 < row < self.rows:
            self.header = self.values[row]

    def set_data_name_row(self, row):
        if -1 < row < self.rows:
            self.data_names = self.values[row]
        for i in range(len(self.data_names)):
            if self.data_names[i]:
                self.col_names[self.data_names[i]] = i

    def get_cell(self, row, col):
        if isinstance(col, int):
            return self.values[row][col]
        elif isinstance(col, str) and col in self.col_names:
            return self.values[row][self.col_names[col]]
        else:
            logger.error(f'Column {col} not found in sheet {self.name}')
            return None
        
    def get_row(self, row):
        return self.values[row]

    def get_col(self,col):
        column = []
        if isinstance(col,int):
            for i in range(self.rows):
                column.append(self.values[i][col])
            return column
        elif isinstance(col, str) and col in self.col_names:
            for i in range(self.rows):
                column.append(self.values[i][col])
            return column
        else:
            logger.error(f'Column {col} not found in sheet {self.name}')
            return None
            
    def write_cell(self, row, col, value):
        if row > self.rows:
            self.rows = row
        if col > self.cols:
            self.cols = col
        while len(self.values) < row:
            self.values.append([])
        while len(self.values[row-1]) < col:
            self.values[row-1].append('')
        self.values[row-1][col-1] = value

    def write_row(self, row, values):
        if row > self.rows:
            self.rows = row
        while len(self.values) < row:
            self.values.append([])
        self.values[row-1] = values
        self.cols = max(self.cols, len(values))

    def append_row(self, values):
        self.rows += 1
        self.values.append(values)
        self.cols = max(self.cols, len(values))

    def trim_empty_rows(self):
        while len(self.values) > self.rows:
            self.values.pop()

    def save(self):
        body = {
            'values': self.values
        }
        self.wb.service.spreadsheets().values().update(
            spreadsheetId=self.wb.file_id,
            range=self.name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
