from minio import Minio
from minio.error import S3Error
from datetime import timedelta
from urllib.parse import urlparse
import logging
import io
import os

# --- THIS IS YOUR MINIO CONFIG ---
MINIO_ENDPOINT = "127.0.0.1:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET = "lms-uploads"


logger = logging.getLogger(__name__)
# Initialize MinIO client
try:
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False # Set to True if using HTTPS
    )

except S3Error as exc:
    print("Error connecting to MinIO:", exc)
    minio_client = None

def check_minio_bucket():
    """
    Checks if the MinIO bucket exists and creates it if not.
    This should be called during app startup, not on import.
    """
    if minio_client is None:
        print("MinIO client not initialized. Cannot check bucket.")
        return
        
    try:
        found = minio_client.bucket_exists(MINIO_BUCKET)
        if not found:
            minio_client.make_bucket(MINIO_BUCKET)
            print(f"Bucket '{MINIO_BUCKET}' created.")
        else:
            print(f"Bucket '{MINIO_BUCKET}' already exists.")
    except Exception as e:
        print(f"Error connecting to MinIO during bucket check: {e}")

def upload_file_to_storage(file_obj, file_name: str, content_type: str) -> str:
    """
    Uploads a file-like object to MinIO and returns the OBJECT KEY (file_name).
    """
    if minio_client is None:
        raise Exception("MinIO client not initialized.")
    
    try:
        file_data = file_obj.read()
        minio_client.put_object(
            MINIO_BUCKET,
            file_name,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
        # --- CHANGED ---
        # Do NOT return a presigned URL. Return the permanent key.
        return file_name 
    except Exception as e:
        logger.error(f"MinIO upload failed: {e}", exc_info=True)
        raise

def get_presigned_url_for_key(file_name: str, expires_in=timedelta(hours=1)) -> str:
    """
    Generates a new presigned URL for a given object key.
    Handles cases where the input is a full URL from old data.
    """
    if minio_client is None:
        raise Exception("MinIO client not initialized.")
    
    key_to_use = file_name
    
    # --- UPDATED FIX ---
    # Check if the file_name is a full URL (from old DB data)
    if file_name and file_name.startswith("http"):
        try:
            # We expect a URL like: http://.../BUCKET_NAME/OBJECT_KEY?query...
            # The error shows the path includes the bucket name.
            bucket_search_string = f"/{MINIO_BUCKET}/"
            
            if bucket_search_string in file_name:
                # Get everything *after* the bucket name
                key_with_query = file_name.split(bucket_search_string, 1)[1]
                
                # Strip off any query parameters (like ?X-Amz-Algorithm=...)
                key_to_use = key_with_query.split("?", 1)[0]
                
                logger.info(f"Converted full URL to object key: {key_to_use}")
            else:
                # Fallback logic if the bucket name isn't in the path
                parsed_url = urlparse(file_name)
                key_to_use = parsed_url.path.lstrip("/")
                logger.warning(f"Converted URL (no bucket in path) to key: {key_to_use}")
                
        except Exception as e:
            logger.error(f"Failed to parse old URL {file_name}: {e}", exc_info=True)
            # Fallback to original name, which will fail but log the error
            key_to_use = file_name
    # --- END OF FIX ---
    
    try:
        # Generate presigned URL using the (potentially cleaned) key
        presigned_url = minio_client.presigned_get_object(
            MINIO_BUCKET,
            key_to_use, 
            expires=expires_in
        )
        return presigned_url
    except S3Error as e:
        logger.error(
            f"MinIO S3Error generating URL for key '{key_to_use}'. Original input was '{file_name}'. Error: {e}", 
            exc_info=True
        )
        # Add a clearer exception if parsing failed
        if key_to_use.startswith("http"):
             raise Exception(f"CRITICAL: Failed to parse object key from old URL. Key was: {key_to_use}")
        raise
    except Exception as e:
        logger.error(f"MinIO URL generation failed for key '{key_to_use}': {e}", exc_info=True)
        raise