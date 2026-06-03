"""
load/gcs_loader.py
------------------
Uploads a pandas DataFrame to Google Cloud Storage as a Parquet file.

Destination path pattern:
    raw/{folder}/{folder}_{YYYYMMDD}.parquet

Credentials are loaded from the GOOGLE_APPLICATION_CREDENTIALS path
defined in .env (pointing at credentials/gcp-credentials.json).
"""

import io
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

# Set GCP credentials path from .env before instantiating any GCP client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/gcp-credentials.json"
)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCP_BUCKET_NAME = os.environ.get("GCP_BUCKET_NAME", "")


def upload_to_gcs(df: pd.DataFrame, folder: str, filename: str = None) -> str:
    """
    Uploads a DataFrame as a Parquet file to GCS.

    Args:
        df:       DataFrame to upload.
        folder:   Subfolder under raw/ (e.g. "ihsg", "fred", "currency").
        filename: Base name for the file. Defaults to the folder name.

    Returns:
        Full GCS URI of the uploaded file (gs://bucket/path).

    Raises:
        Exception: Propagates any GCS client error after logging it.
    """
    if filename is None:
        filename = folder

    date_str = datetime.today().strftime("%Y%m%d")
    blob_path = f"raw/{folder}/{filename}_{date_str}.parquet"
    gcs_uri = f"gs://{GCP_BUCKET_NAME}/{blob_path}"

    print(f"[GCS] Uploading {len(df)} rows → {gcs_uri}")

    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCP_BUCKET_NAME)
        blob = bucket.blob(blob_path)

        # Serialise DataFrame to an in-memory Parquet buffer
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow")
        buffer.seek(0)

        blob.upload_from_file(buffer, content_type="application/octet-stream")

        print(f"[GCS] Upload successful: {gcs_uri}")
        return gcs_uri

    except Exception as e:
        print(f"[GCS] ERROR uploading to GCS: {e}")
        raise
