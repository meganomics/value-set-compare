import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


SCOPES = ['https://www.googleapis.com/auth/drive']


def authorize():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


class Drive:

    def __init__(self):
        self.credentials = authorize()
        self.service = build('drive', 'v3', credentials=self.credentials, cache_discovery=False)

    def id_to_name(self, file_id):
        try:
            results = self.service.files().get(fileId=file_id, fields="name").execute()
            return results.get('name', '')

        except HttpError as error:
            print(f'An error occurred: {error}')
            return ''

    def list_from_query(self, query):
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields="nextPageToken, files(id, name)"
            ).execute()

            items = results.get('files', [])

            if not items:
                print('No files found.')
                return []
            else:
                return items

        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def move(self, file_id, source, target):
        try:
            if source:
                file = self.service.files().update(
                    fileId=file_id,
                    addParents=target,
                    removeParents=source,
                    fields='name, id, parents'
                ).execute()
            else:
                file = self.service.files().update(
                    fileId=file_id,
                    addParents=target,
                    fields='name, id, parents'
                ).execute()
            return file['id']

        except HttpError as error:
            print(f'Unable to move file, {file_id} from {source} to {target}: {error}')
            return None


