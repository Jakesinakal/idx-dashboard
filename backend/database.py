import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv(Path(__file__).parent.parent / ".env")

_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if _creds and not Path(_creds).is_absolute():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(Path(__file__).parent.parent / _creds)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ["BQ_DATASET"]
TABLE_PREFIX = f"`{PROJECT_ID}.{DATASET}`"


def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)
