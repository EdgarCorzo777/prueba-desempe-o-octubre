import os
import json
import io
import logging
from datetime import datetime, timezone
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger("sismowatch.lake")

DEFAULT_BUCKET = os.getenv("MINIO_BUCKET", "sismowatch-bronze")

def get_minio_client() -> Minio:
    """
    Returns configured Minio S3 client with automatic host fallback.
    """
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ROOT_USER", "sismowatch_minio_admin")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD", "sismowatch_minio_pass_2026")

    # If running on host and minio:9000 is unreachable, fallback to localhost:9000
    host, port = endpoint.split(":") if ":" in endpoint else (endpoint, "9000")
    if host == "minio" and not os.path.exists("/.dockerenv"):
        endpoint = f"localhost:{port}"

    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False
    )

def ensure_bronze_bucket(bucket_name: str = DEFAULT_BUCKET) -> bool:
    """
    Guarantees that the Bronze lakehouse bucket exists in MinIO.
    """
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"Created MinIO Lakehouse bucket: '{bucket_name}'")
        return True
    except Exception as e:
        logger.warning(f"Could not verify/create MinIO bucket '{bucket_name}': {e}")
        return False

def persist_raw_feed_to_lake(
    feed_data: dict,
    execution_id: str,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Persists raw, unmodified GeoJSON response from USGS into MinIO Bronze Layer.
    Partitioned by UTC date: raw/year=YYYY/month=MM/day=DD/feed_{execution_id}.json
    Returns the s3:// URI.
    """
    ensure_bronze_bucket(bucket_name)
    client = get_minio_client()

    now_utc = datetime.now(timezone.utc)
    object_name = f"raw/year={now_utc.year}/month={now_utc.month:02d}/day={now_utc.day:02d}/feed_{execution_id}.json"
    
    payload_bytes = json.dumps(feed_data, ensure_ascii=False, indent=2).encode("utf-8")
    stream = io.BytesIO(payload_bytes)

    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=stream,
        length=len(payload_bytes),
        content_type="application/geo+json"
    )

    s3_uri = f"s3://{bucket_name}/{object_name}"
    logger.info(f"Persisted raw feed to MinIO Bronze Lake: {s3_uri} ({len(payload_bytes)} bytes)")
    return s3_uri

def read_raw_feed_from_lake(s3_uri: str) -> dict:
    """
    Retrieves raw GeoJSON object from MinIO Bronze layer.
    """
    client = get_minio_client()
    clean_uri = s3_uri.replace("s3://", "")
    parts = clean_uri.split("/", 1)
    bucket = parts[0]
    object_name = parts[1]

    response = client.get_object(bucket, object_name)
    data = json.loads(response.read().decode("utf-8"))
    response.close()
    response.release_conn()
    return data
