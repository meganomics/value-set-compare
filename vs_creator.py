from gstuff.gdrv import Drive
from gstuff.gsht import GSManager
from gstuff.gsht import Sheet
import googlesheetssettings as gss
import time

# defining constants
dv_header_rows = 2
dv_metadata_cols = 2

# get metadata out of the sheet, assuming a particular structure; add vs type (Treatment,
# Diagnosis, or Procedure) depending on whether the filename ends in _Tx, _Dx, or _Px.

def get_metadata(sheet):
    metadata_labels = []
    metadata_values = []
    for i in range(dv_header_rows, min(sheet.rows,10)):
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

#def get_col_numbers(dict, sheet, system):
#    sheet_headers = get_sheet_headers(sheet)
#    col_numbers = find_indices(sheet_headers, dict[system][0])
#    return col_numbers

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
                column_pairs = code_dict[key][3]
                if col in column_pairs:
                    col1 = [sci_to_code(newline_strip(x)) for x in sheet.get_col(column_pairs[1])][2:]
                    col2 = [sci_to_code(newline_strip(x)) for x in sheet.get_col(column_pairs[0])][2:]
                    codes = [list(x) for x in list(set(zip(col1, col2)))] #set is to remove duplicates
                    system_code_pair_dict[key] = codes
    return system_code_pair_dict

def sci_to_code(code):
    """ convert codes in scientific notation in the Google sheet back into codes """
    if 'E+' in code:
        base, exp = code.split("E+")
        newcode = str(int(float(base+'e'+exp)))
        return newcode
    else:
        return code
    
def newline_strip(label):
    label2 = label.replace("\n", " ")
    return label2


# create a grouping value set

def create_grouping_vs(sheet, cont_vals):
    metadata = get_metadata(sheet) #a  dictionary
    filename = metadata['Filename']
    metadata.update({'Content Type':'subsets'})
    desc_vals = list(map(list, metadata.items()))[1:]
    drive = Drive()
    gsm = GSManager(drive.credentials) 
    value_set = gsm.create_vs_workbook(filename, 'subsets', desc_vals, cont_vals)
    drive.move(value_set.file_id, None, gss.STAGING_FOLDER_ID)
    print("Created grouping vs "+filename)
#    time.sleep(1)


# create filename labels appropriate for concept value sets (i.e. "Covid-19_Dx (ICD-10-CM)")

def update_filename_label(dict, metadata, system):
    oldname = metadata['Filename']
    oldlabel = metadata['Label']
    newtext = dict[system][1]
    metadata.update({'Filename':oldname+newtext})
    metadata.update({'Label':oldlabel+newtext})
    return metadata


# create concept value set for any system besides ICD-10 (where intensional
# defs exist), DMD/PID, generic drugs

def create_concept_vs(sheet, system_dict, system, code_pairs):
    metadata = get_metadata(sheet) #a dictionary
    updated_metadata = update_filename_label(system_dict, metadata, system)

    filename = updated_metadata['Filename']
    label = updated_metadata['Label']
    updated_metadata.update({'Content Type':system_dict[system][4]})
    desc_vals = list(map(list, updated_metadata.items()))[1:]
    cont_vals = [['Label', 'Code', 'System', 'Note']]
    for i in range(len(code_pairs)):
        code_pair = code_pairs[i]
        if code_pair[0] != '' or code_pair[1] != '':
            code_pair.append(system_dict[system][2])
            cont_vals.append(code_pair)

    drive = Drive()
    gsm = GSManager(drive.credentials)
    value_set = gsm.create_vs_workbook(filename, 'concepts', desc_vals, cont_vals)
    drive.move(value_set.file_id, None, gss.STAGING_FOLDER_ID)
    print("Created concept vs "+filename)
#    time.sleep(1)
    return filename,label


# create concept value set for ICD-10 (where intensional defs exist)

def create_icd_intensional_vs(sheet, system_dict, system, code_pairs):
    metadata = get_metadata(sheet) #a dictionary
    updated_metadata = update_filename_label(system_dict, metadata, system)

    filename = updated_metadata['Filename']
    label = updated_metadata['Label']
    updated_metadata.update({'Content Type':system_dict[system][4]})
    intents = system_dict[system][2]+': '
    for i in range(len(code_pairs)):
        code_pair = code_pairs[i]
        if code_pair[1] != '':
            intents += code_pair[1]+', '
    intents_stripped = intents.strip(', ')
    updated_metadata['Intent'] = intents_stripped
    desc_vals = list(map(list, updated_metadata.items()))[1:]
    cont_vals = [['Label', 'Code', 'System', 'Note']]

    drive = Drive()
    gsm = GSManager(drive.credentials)
    value_set = gsm.create_vs_workbook(filename, 'concepts', desc_vals, cont_vals)
    drive.move(value_set.file_id, None, gss.INTENSIONAL_FOLDER_ID)
    print("Created concept vs "+filename+" (INTENSIONAL)")
#    time.sleep(1)
    return filename,label

# create concept value set for DMD/DMD PID codelists

def create_dmd_vs(sheet, system_dict, system, code_pairs):
    metadata = get_metadata(sheet) #a dictionary
    updated_metadata = update_filename_label(system_dict, metadata, system)

    filename = updated_metadata['Filename']
    label = updated_metadata['Label']
    updated_metadata.update({'Content Type':system_dict[system][4]})
    desc_vals = list(map(list, updated_metadata.items()))[1:]
    cont_vals = [['Label', 'Code', 'System', 'Note']]
    for i in range(len(code_pairs)):
        code_pair = code_pairs[i]
        if code_pair[1] != '':
            code_pair.append(system_dict[system][2])
            cont_vals.append(code_pair)

    drive = Drive()
    gsm = GSManager(drive.credentials)
    value_set = gsm.create_vs_workbook(filename, 'concepts', desc_vals, cont_vals)
    drive.move(value_set.file_id, None, gss.STAGING_FOLDER_ID)
    print("Created concept vs "+filename)
#    time.sleep(1)
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
    for i in range(len(code_pairs)):
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
    print("Created concept vs "+filename)
#    time.sleep(1)
    return filename,label


def create_value_sets(sheet, code_cols, system_dict):
    """ create concept vs's for each of the codelist systems represented in the given sheet;
        store their filenames and labels for use in the grouping value set, create one 
        grouping vs based on that """
    
    code_pair_dict = get_codelists(code_cols, sheet, system_dict)
    grouping_cont_vals = [['Filename', 'Value Set Label', 'Note']]
    for system in code_pair_dict:
        if system == 'name':
            name, label = create_generic_vs(sheet, system_dict, system, code_pair_dict[system])
        elif system == 'dmd_pid':
            codes = sheet.get_col(10)[2:]
            if any(code != '' for code in codes):
                name, label = create_dmd_vs(sheet, system_dict, system, code_pair_dict[system])
        elif system == 'dmd':
            codes = sheet.get_col(11)[2:]
            if any(code != '' for code in codes):
                name, label = create_dmd_vs(sheet, system_dict, system, code_pair_dict[system])
        elif system == 'icd':
            codes = sheet.get_col(2)[2:]
            if any('.x' in code or '.X' in code for code in codes):
                name, label = create_icd_intensional_vs(sheet, system_dict, system, code_pair_dict[system])
            else:
                name, label = create_concept_vs(sheet, system_dict, system, code_pair_dict[system])
        else:
            name, label = create_concept_vs(sheet, system_dict, system, code_pair_dict[system])
        grouping_cont_val_row = [name, label, '']
        grouping_cont_vals.append(grouping_cont_val_row)
    create_grouping_vs(sheet, grouping_cont_vals)


def main():
    code_cols = [2, 4, 5, 8, 10, 11, 12, 13]
    system_dict = {
        #'system_type':['header','filename_label','system','columns','concepts or drugs'],
        'icd':['ICD10',' (ICD-10)','ICD-10',[2,3],'concepts'],
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

    source_wb = gsm.get_workbook(gss.VALUE_SET_11)
    workbook_name = source_wb.name
    print(workbook_name+' started.')

    tabs = source_wb.get_sheet_names()

    for tab in tabs: 
        working_sheet = source_wb.sheets.get(tab)
        if working_sheet.cols < 16:
            working_sheet.write_cell(2,15,'category')
            working_sheet.save()
        create_value_sets(working_sheet, code_cols, system_dict)

    print(workbook_name+' done.')

if __name__ == '__main__':
    main()