"""MinIO / S3-compatible client for reading and writing Parquet files."""

import io
import os
from typing import Optional

import boto3
import pandas as pd
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Default bucket names – overridable via environment variables
BRONZE_BUCKET = os.getenv("MINIO_BRONZE_BUCKET", "bronze")
SILVER_BUCKET = os.getenv("MINIO_SILVER_BUCKET", "silver")


def get_minio_client():
    """Return a boto3 S3 client configured for MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("MINIO_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY"),
        config=Config(signature_version="s3v4"),
        region_name=os.getenv("MINIO_REGION", "us-east-1"),
    )


def read_parquet(object_key: str, bucket: Optional[str] = None) -> pd.DataFrame:
    """
    Read a Parquet file from MinIO into a DataFrame.

    Parameters
    ----------
    object_key : str
        The S3 object key (path) inside the bucket.
    bucket : str, optional
        Bucket name.  Defaults to BRONZE_BUCKET.

    Returns
    -------
    pd.DataFrame
        Loaded data, or an empty DataFrame on error.
    """
    bucket = bucket or BRONZE_BUCKET
    client = get_minio_client()
    try:
        response = client.get_object(Bucket=bucket, Key=object_key)
        return pd.read_parquet(io.BytesIO(response["Body"].read()))
    except ClientError as exc:
        print(f"[minio_client] Error reading s3://{bucket}/{object_key}: {exc}")
        return pd.DataFrame()


def write_parquet(
    df: pd.DataFrame,
    object_key: str,
    bucket: Optional[str] = None,
) -> bool:
    """
    Write a DataFrame as a Parquet file to MinIO.

    Parameters
    ----------
    df : pd.DataFrame
        Data to write.
    object_key : str
        The S3 object key (path) inside the bucket.
    bucket : str, optional
        Bucket name.  Defaults to SILVER_BUCKET.

    Returns
    -------
    bool
        True on success, False on error.
    """
    bucket = bucket or SILVER_BUCKET
    client = get_minio_client()
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)
    try:
        client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=buffer,
            ContentType="application/octet-stream",
        )
        return True
    except ClientError as exc:
        print(f"[minio_client] Error writing s3://{bucket}/{object_key}: {exc}")
        return False


def write_json(payload: dict, object_key: str, bucket: Optional[str] = None) -> bool:
    """
    Write a JSON-serialisable dict to MinIO.

    Used for storing pipeline metadata (source code versions, run timestamps, etc.).
    """
    import json

    bucket = bucket or SILVER_BUCKET
    client = get_minio_client()
    body = json.dumps(payload, default=str, indent=2).encode("utf-8")
    try:
        client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=body,
            ContentType="application/json",
        )
        return True
    except ClientError as exc:
        print(f"[minio_client] Error writing JSON s3://{bucket}/{object_key}: {exc}")
        return False


def list_objects(prefix: str = "", bucket: Optional[str] = None) -> list[str]:
    """Return a list of object keys in *bucket* matching *prefix*."""
    bucket = bucket or SILVER_BUCKET
    client = get_minio_client()
    try:
        paginator = client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys
    except ClientError as exc:
        print(f"[minio_client] Error listing s3://{bucket}/{prefix}: {exc}")
        return []


def ensure_bucket(bucket: str) -> bool:
    """Create *bucket* if it does not exist yet."""
    client = get_minio_client()
    try:
        client.head_bucket(Bucket=bucket)
        return True
    except ClientError:
        try:
            client.create_bucket(Bucket=bucket)
            return True
        except ClientError as exc:
            print(f"[minio_client] Could not create bucket '{bucket}': {exc}")
            return False
