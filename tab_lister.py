from gstuff.gdrv import Drive
from gstuff.gsht import GSManager
from gstuff.gsht import Sheet
import googlesheetssettings as gss
import time

def main():

    # create a Google Drive wrapper object
    drive = Drive()

    # create a Google Sheet Manager object
    gsm = GSManager(drive.credentials)

    source_wb = gsm.get_workbook(gss.SOURCE_SHEET_ID)
    target_wb = gsm.get_workbook(gss.TARGET_SHEET_ID)

    target_sheet = target_wb.sheets.get('Sheet1')

    tabs = source_wb.get_sheet_names()

    n = 1
    for tab in tabs:
        source_sheet = source_wb.sheets.get(tab)
        filename = source_sheet.get_cell(2,1)
        target_sheet.write_cell(n,3,filename)
        target_sheet.save()
        n = n+1
        if n == 60:
            print('Processed 59 tabs, waiting a minute.')
            time.sleep(60) 

    print('Done.')


if __name__ == '__main__':
    main()