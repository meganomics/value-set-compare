import json


class Term:

    def __init__(self):
        self.label: str = ''
        self.context: str = ''


class Concept:

    def __init__(self):
        self.handle: str = ''
        self.label: str = ''
        self.code: str = ''
        self.system: str = ''
        self.note: str = ''
        self.terms: list[Term] = []

    def __str__(self):
        return f'{self.system}::{self.code}::{self.label}'


class VSReference:

    def __init__(self, label, short_name, note):
        self.label = label
        self.short_name = short_name
        self.note = note


class ValueSet:

    def __init__(self):
        self.label: str = ''
        self.handle: str = ''
        self.kind: str = ''
        self.concept: str = ''
        self.description: str = ''
        self.oid: str = ''
        self.uri: str = ''
        self.namespaces: list[str] = []
        self.intent: str = ''
        self.members: list[Concept] = []
        self.subsets: list[VSReference] = []
        self.documentation: dict = {
            'references': [],
            'notes': [],
        }
        self.info: dict = {
            'short_name': '',
            'details': [],
            'flags': [],
        }
        self.errors: list = []

        self.gs_kind: str = ''

    @property
    def desc_vals(self):
        rv = []
        if self.label:
            rv.append(['Label', self.label])
        if self.handle:
            rv.append(['Handle', self.handle])
        if self.kind:
            if self.kind == 'grouping':
                self.gs_kind = 'subsets'
                rv.append(['Content Type', 'subsets'])
            else:
                self.gs_kind = 'concepts'
                rv.append(['Content Type', 'concepts'])
        # Consider adding Concept
        if self.description:
            rv.append(['Description', self.description])
        if self.oid:
            rv.append(['OID', self.oid])
        if self.uri:
            rv.append(['URL', self.uri])
        if self.intent:
            rv.append(['Intent', self.intent])
        if self.documentation:
            refs = self.documentation.get('references', [])
            for ref in refs:
                rv.append(['Reference', ref])
            notes = self.documentation.get('notes', [])
            for note in notes:
                rv.append(['Note', note])
        return rv

    @property
    def cont_vals(self):
        rv = []
        if self.kind == 'grouping':
            rv.append(['Filename', 'Value Set Label', 'Note'])
            for subset in self.subsets:
                rv.append([subset.short_name, subset.label, subset.note])
            return rv
        else:
            # TODO: Add support for generic and trade names for drugs.
            rv.append(['Label', 'Code', 'System', 'Note'])
            for concept in self.members:
                rv.append([concept.label, concept.code, concept.system, concept.note])
            return rv


def values_to_dicts(values):
    if len(values) > 1:
        rv = []
        header = values[0]
        for row in values[1:]:
            row_dict = {}
            for col in range(len(header)):
                row_dict[header[col]] = row[col]
            rv.append(row_dict)
        return rv
    return []


def value_set_from_gs(gs_wb):
    vs = ValueSet()
    vs.info['short_name'] = gs_wb.name
    desc_sheet = gs_wb.sheets.get('Description')
    vs_content_type = ''
    if desc_sheet:
        for row in desc_sheet.values:
            if row[0] == 'Handle':
                vs.handle = row[1]
            elif row[0] == 'Label':
                vs.label = row[1]
            elif row[0] == 'Value Set Type':
                vs.kind = row[1]
            elif row[0] == 'Content Type':
                vs_content_type = row[1]
            elif row[0] == 'Description':
                vs.description = row[1]
            elif row[0] == 'OID':
                vs.oid = row[1]
            elif row[0] == 'URL':
                vs.uri = row[1]
            elif row[0] == 'Concept':
                vs.concept = row[1]
            elif row[0] == 'Intent':
                vs.intent = row[1]
            elif row[0] == 'Reference':
                vs.documentation['references'].append(row[1])
            elif row[0] == 'Note':
                vs.documentation['notes'].append(row[1])
            elif row[0] == 'Info-details-json':
                jv = json.loads(row[1])
                vs.info['details'].append(jv)
            elif row[0] == 'Info-details-text':
                vs.info['details'].append(row[1])
        # Infer value set type if not explicitly set.
        if not vs.kind:
            if vs_content_type == 'subsets':
                vs.kind = 'grouping'
            elif vs.intent:
                vs.kind = 'intensional'
            else:
                vs.kind = 'extensional'
        # Load content sheet.
        if vs_content_type == 'concepts':
            cont_sheet = gs_wb.sheets.get('Concepts')
            records = values_to_dicts(cont_sheet.values)
            for record in records:
                concept = Concept()
                concept.label = record.get('Label', '')
                concept.code = record.get('Code', '')
                concept.system = record.get('System', '')
                concept.note = record.get('Note', '')
                vs.members.append(concept)
        elif vs_content_type == 'drugs':
            vs.info['flags'].append('drug-list')
            cont_sheet = gs_wb.sheets.get('Drugs')
            records = values_to_dicts(cont_sheet.values)
            for record in records:
                concept = Concept()
                concept.label = record.get('Label', '')
                concept.code = record.get('Code', '')
                concept.system = record.get('System', '')
                concept.note = record.get('Note', '')
                generic_name = record.get('Generic Name', '')
                if generic_name:
                    gn_term = Term()
                    gn_term.label = generic_name
                    gn_term.context = 'drug-generic-name'
                    concept.terms.append(gn_term)
                trade_names = record.get('Trade Name(s)', '')
                if trade_names:
                    for tn in trade_names.split(','):
                        tn_term = Term()
                        tn_term.label = tn.strip()
                        tn_term.context = 'drug-trade-name'
                        concept.terms.append(tn_term)
                vs.members.append(concept)
        elif vs_content_type == 'subsets':
            cont_sheet = gs_wb.sheets.get('Subsets')
            records = values_to_dicts(cont_sheet.values)
            for record in records:
                ref_fn = record.get('Filename', '')
                ref_vs_label = record.get('Value Set Label', '')
                ref_note = record.get('Note', '')
                vsref = VSReference(ref_vs_label, ref_fn, ref_note)
                if ref_fn or ref_vs_label:
                    vs.subsets.append(vsref)
        else:
            vs.errors.append(f'No content type in file: {gs_wb.name}')
    else:
        vs.errors.append(f'No description sheet in file: {gs_wb.name}')
    return vs


class VocabEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, ValueSet) or isinstance(o, Concept) or isinstance(o, Term):
            return o.__dict__
        return json.JSONEncoder.default(self, o)
