from gstuff.gdrv import Drive
from gstuff.gsht import GSManager
import googlesheetssettings as gss


def main():
    """make sure all of the data variables in the Statements sheet are defined first in the Data Variables sheet"""

    # define some variables
    issues = []
    dv_header_rows = 3
    stmt_header_rows = 3

    # create a Google Drive wrapper object
    drive = Drive()

    # create a Google Sheet Manager object
    gsm = GSManager(drive.credentials)

    # get a "workbook", aka a full spreadsheet, not just one tab
    wb = gsm.get_workbook(gss.STATEMENT_SHEET_ID)

    # get a "sheet", aka a tab in a workbook
    statement_sheet = wb.sheets.get('Statements')

    # get another "sheet"
    data_variable_sheet = wb.sheets.get('Data Variables')


    # make a list of all of the data variables that have been defined in the Data Variables sheet
    dv_handles = []
    if data_variable_sheet.rows > dv_header_rows:
        for i in range(dv_header_rows, data_variable_sheet.rows):
            if data_variable_sheet.values[i][0] == 'ready':
                # get data variable handle
                dv_handle = data_variable_sheet.values[i][1]
                # add data variable handle to 'dv_handles' if it's not already there
                if dv_handle not in dv_handles:
                    dv_handles.append(dv_handle)
    
    # check to see if the data variables in the Statements sheet are in 'dv_handles'
    if statement_sheet.rows > stmt_header_rows:
        for i in range(stmt_header_rows, statement_sheet.rows):
            if statement_sheet.values[i][0] == 'ready':
                # get the data variable handle
                stmt_dv_handle = statement_sheet.values[i][6]
                # look for the handle
                if stmt_dv_handle not in dv_handles:
                    # the handle in the Statements sheet may be missing the 'nvdnc-ns::' prefix, so check for that
                    if 'nvdnc-ns::' + stmt_dv_handle not in dv_handles:
                        issues.append(f'Data variable not found.\nStatement handle: {statement_sheet.values[i][3]}\nData variable: {stmt_dv_handle}')

    # display the results
    if issues:
        for issue in issues:
            print(issue)
    else:
        print('No issues found.')



if __name__ == '__main__':
    main()

