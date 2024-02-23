from gstuff.gdrv import Drive
from gstuff.gsht import GSManager
from gstuff.gsht import Sheet
import googlesheetssettings as gss

# defining constants
dv_header_rows = 2
dv_metadata_cols = 2

# get metadata out of the sheet, assuming a particular structure; add vs type (Treatment,
# Diagnosis, or Procedure) depending on whether the filename ends in _Tx, _Dx, or _Px.

def get_metadata(sheet):
    metadata_labels = []
    metadata_values = []
    for i in range(dv_header_rows, sheet.rows):
        if sheet.values[i][0] != '':
            metadata_labels.append(sheet.values[i][0])
            metadata_values.append(sheet.values[i][1])
    metadata = dict(zip(metadata_labels, metadata_values))
    metadata_with_vs_type = metadata_add_vs_type(metadata)
    return metadata_with_vs_type

def metadata_add_vs_type(metadata):
    type_dict = {
        'Px':'Procedure',
        'Dx':'Diagnosis',
        'Tx':'Treatment'}
    for type in type_dict.keys():
        if metadata['Filename'][-2:] == type:
            metadata['Value Set Type'] = type_dict[type]
    return metadata


# pull out last row of headers & strip white space

def get_sheet_headers(sheet):
    sheet_headers = [header.strip() for header in sheet.values[dv_header_rows-1]]
    #sheet_headers = list(filter(None, sheet_headers)) #removes empty entries from the header list
    return sheet_headers


# given a particular value, return a list of the indices of all columns whose headers contain that value

def get_col_numbers(dict, sheet, system):
    sheet_headers = get_sheet_headers(sheet)
    col_numbers = find_indices(sheet_headers, dict[system][0])
    return col_numbers

def find_indices(list, item):
    indices = []
    for idx, value in enumerate(list):
        if item in value:
            indices.append(idx)
    return indices

def get_codelists(code_cols, sheet, code_dict):
    """ pull out paired code-description lists, each matched with a coding system type (icd, snomed, etc.)
    """
    first_row = sheet.get_row(dv_header_rows)
    system_code_pair_dict = {}
    for col in code_cols:
        if first_row[col] != '':
            for key in code_dict.keys():
                #if key != 'name':
                column_pairs = code_dict[key][3]
                if col in column_pairs:
                    codes = list(list(x) for x in zip(sheet.get_col(column_pairs[1]),sheet.get_col(column_pairs[0])))[2:]
                    system_code_pair_dict[key] = codes
    return system_code_pair_dict
    

# create a subset value set

def create_subset_vs(sheet, cont_vals):
    metadata = get_metadata(sheet) #a  dictionary
    filename = metadata['Filename']
    metadata.update({'Content Type':'subsets'})
    desc_vals = list(map(list, metadata.items()))[1:]
    drive = Drive()
    gsm = GSManager(drive.credentials) 
    value_set = gsm.create_vs_workbook(filename, 'subsets', desc_vals, cont_vals)
    drive.move(value_set.file_id, None, gss.STAGING_FOLDER_ID)


# create filename labels appropriate for concept value sets (i.e. "Covid-19_Dx (ICD-10-CM)")

def update_filename_label(dict, metadata, system):
    oldname = metadata['Filename']
    oldlabel = metadata['Label']
    newtext = dict[system][1]
    metadata.update({'Filename':oldname+newtext})
    metadata.update({'Label':oldlabel+newtext})
    return metadata


# create concept value set for any system besides generic drug

def create_concept_vs(sheet, system_dict, system, code_pairs):
    metadata = get_metadata(sheet) #a dictionary
    updated_metadata = update_filename_label(system_dict, metadata, system)

    filename = updated_metadata['Filename']
    label = updated_metadata['Label']
    updated_metadata.update({'Content Type':system_dict[system][4]})
    desc_vals = list(map(list, updated_metadata.items()))[1:]
    cont_vals = [['Label', 'Code', 'System', 'Note']]
    for i in range(len(code_pairs)-1):
        code_pair = code_pairs[i]
        if code_pair[0] != '' or code_pair[1] != '':
            code_pair.append(system_dict[system][2])
            cont_vals.append(code_pair)

    drive = Drive()
    gsm = GSManager(drive.credentials)
    value_set = gsm.create_vs_workbook(filename, 'concepts', desc_vals, cont_vals)
    drive.move(value_set.file_id, None, gss.STAGING_FOLDER_ID)
    return filename,label


# create concept value set for generic drug

def create_generic_vs(sheet, system_dict, system, code_pairs):
    metadata = get_metadata(sheet) #a dictionary
    updated_metadata = update_filename_label(system_dict, metadata, system)

    filename = updated_metadata['Filename']
    label = updated_metadata['Label']
    updated_metadata.update({'Content Type':system_dict[system][4]})
    desc_vals = list(map(list, updated_metadata.items()))[1:]
    cont_vals = [['Label', 'Code', 'System', 'Note', 'Generic Name', 'Trade Name', 'Category']]
    for i in range(len(code_pairs)-1):
        code_pair = code_pairs[i]
        row = ['','','','','','','']
        if code_pair[0] != '' or code_pair[1] != '':
            row[0] = code_pair[1]
            row[4] = code_pair[1]
            row[6] = code_pair[0]
            cont_vals.append(row)

    drive = Drive()
    gsm = GSManager(drive.credentials)
    value_set = gsm.create_vs_workbook(filename, 'concepts', desc_vals, cont_vals)
    drive.move(value_set.file_id, None, gss.STAGING_FOLDER_ID)
    return filename,label


def create_value_sets(sheet, code_cols, system_dict):
    """ create concept vs's for each of the codelist systems represented in the given sheet;
        store their filenames and labels for use in the subset value set, create one 
        subset vs based on that """
    
    code_pair_dict = get_codelists(code_cols, sheet, system_dict)
    subset_cont_vals = [['Filename', 'Value Set Label', 'Note']]
    for system in code_pair_dict:
        if system == 'name':
            name, label = create_generic_vs(sheet, system_dict, system, code_pair_dict[system])
        else:
            name, label = create_concept_vs(sheet, system_dict, system, code_pair_dict[system])
        subset_cont_val_row = [name, label, '']
        subset_cont_vals.append(subset_cont_val_row)
    create_subset_vs(sheet, subset_cont_vals)


def main():
    code_cols = [2, 4, 5, 8, 10, 11, 12, 13]
    system_dict = {
        #'system_type':['header','filename_label','system','columns','concepts or drugs'],
        'icd':['ICD10',' (ICD-10-CM)','ICD-10-CM',[2,3],'concepts'],
        'medcode':['Medcode',' (MEDCODE)','MEDCODE',[4,7],'concepts'],
        'snomed':['SNOMED',' (SNOMED)','SNOMED',[5,6],'concepts'],
        'opcs':['OPCS',' (OPCS)','OPCS',[8,9],'concepts'],
        'dmd_pid':['Prod', ' (DMD_PID)','DMDPID',[10,12],'drugs'],
        'dmd':['zyxw', ' (DMD)','DMD',[11,12],'drugs'],
        'name':['Generic', ' (Name)','',[13, 14],'drugs']
        }

    # create a Google Drive wrapper object
    drive = Drive()

    # create a Google Sheet Manager object
    gsm = GSManager(drive.credentials)

    source_wb = gsm.get_workbook(gss.SOURCE_SHEET_ID)

    tabs = source_wb.get_sheet_names()

    print(len(tabs))

    #for tab in map(lambda s: f"'{s}'", tabs):   #wraps function names in single quotes -- tab names ending in integer causing problems
    #    working_sheet = source_wb.sheets.get(tab)
    #    working_sheet.write_cell(2,15,'category')
    #    working_sheet.save()
    #    create_value_sets(working_sheet, code_cols, system_dict)

    #working_sheet = source_wb.sheets.get('covid-19_tx')
    #create_value_sets(working_sheet,code_cols,system_dict)

    print('Done.')


if __name__ == '__main__':
    main()