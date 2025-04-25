import os
import json
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# Leer el JSON desde la variable de entorno GOOGLE_CREDS
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
