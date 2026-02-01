"""
S3 storage client for Oros.

Handles document storage and retrieval from S3 with LocalStack support.
"""

from datetime import timedelta
from io import BytesIO
from typing import Any, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from services.shared.config import Settings, get_settings
from services.shared.logging import get_logger

logger = get_logger(__name__)


class S3Client:
    """
    S3 client wrapper with support for LocalStack in development.

    Provides methods for uploading, downloading, and managing documents in S3.
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize S3 client.

        Args:
            settings: Optional settings override
        """
        self.settings = settings or get_settings()
        self._client = self._create_client()

    def _create_client(self) -> Any:
        """Create boto3 S3 client with appropriate configuration."""
        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )

        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": self.settings.aws_region,
            "config": config,
        }

        # Use LocalStack endpoint in development
        if self.settings.aws_endpoint_url:
            kwargs["endpoint_url"] = self.settings.aws_endpoint_url
            kwargs["aws_access_key_id"] = self.settings.aws_access_key_id or "test"
            kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key or "test"

        return boto3.client(**kwargs)

    async def upload_document(
        self,
        content: bytes | BinaryIO,
        key: str,
        bucket: str | None = None,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload a document to S3.

        Args:
            content: Document content as bytes or file-like object
            key: S3 object key
            bucket: Bucket name (defaults to raw documents bucket)
            content_type: MIME type of the content
            metadata: Optional metadata to attach to the object

        Returns:
            S3 URI of the uploaded object

        Raises:
            ClientError: If upload fails
        """
        bucket = bucket or self.settings.s3_bucket_raw_documents

        try:
            if isinstance(content, bytes):
                content = BytesIO(content)

            extra_args: dict[str, Any] = {"ContentType": content_type}
            if metadata:
                extra_args["Metadata"] = metadata

            self._client.upload_fileobj(
                content,
                bucket,
                key,
                ExtraArgs=extra_args,
            )

            s3_uri = f"s3://{bucket}/{key}"
            logger.info(
                "document_uploaded",
                bucket=bucket,
                key=key,
                content_type=content_type,
            )
            return s3_uri

        except ClientError as e:
            logger.error(
                "document_upload_failed",
                bucket=bucket,
                key=key,
                error=str(e),
            )
            raise

    async def download_document(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bytes:
        """
        Download a document from S3.

        Args:
            key: S3 object key
            bucket: Bucket name (defaults to raw documents bucket)

        Returns:
            Document content as bytes

        Raises:
            ClientError: If download fails
        """
        bucket = bucket or self.settings.s3_bucket_raw_documents

        try:
            buffer = BytesIO()
            self._client.download_fileobj(bucket, key, buffer)
            buffer.seek(0)

            logger.info("document_downloaded", bucket=bucket, key=key)
            return buffer.read()

        except ClientError as e:
            logger.error(
                "document_download_failed",
                bucket=bucket,
                key=key,
                error=str(e),
            )
            raise

    async def get_presigned_url(
        self,
        key: str,
        bucket: str | None = None,
        expiration: timedelta = timedelta(hours=1),
        method: str = "get_object",
    ) -> str:
        """
        Generate a presigned URL for temporary access to an object.

        Args:
            key: S3 object key
            bucket: Bucket name (defaults to raw documents bucket)
            expiration: URL expiration time
            method: S3 method ('get_object' or 'put_object')

        Returns:
            Presigned URL
        """
        bucket = bucket or self.settings.s3_bucket_raw_documents

        url = self._client.generate_presigned_url(
            method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=int(expiration.total_seconds()),
        )

        logger.debug(
            "presigned_url_generated",
            bucket=bucket,
            key=key,
            expiration_seconds=expiration.total_seconds(),
        )
        return url

    async def delete_document(
        self,
        key: str,
        bucket: str | None = None,
    ) -> None:
        """
        Delete a document from S3.

        Args:
            key: S3 object key
            bucket: Bucket name (defaults to raw documents bucket)

        Raises:
            ClientError: If deletion fails
        """
        bucket = bucket or self.settings.s3_bucket_raw_documents

        try:
            self._client.delete_object(Bucket=bucket, Key=key)
            logger.info("document_deleted", bucket=bucket, key=key)

        except ClientError as e:
            logger.error(
                "document_delete_failed",
                bucket=bucket,
                key=key,
                error=str(e),
            )
            raise

    async def document_exists(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bool:
        """
        Check if a document exists in S3.

        Args:
            key: S3 object key
            bucket: Bucket name (defaults to raw documents bucket)

        Returns:
            True if document exists, False otherwise
        """
        bucket = bucket or self.settings.s3_bucket_raw_documents

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    async def list_documents(
        self,
        prefix: str = "",
        bucket: str | None = None,
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        List documents in S3 with optional prefix filter.

        Args:
            prefix: Key prefix to filter by
            bucket: Bucket name (defaults to raw documents bucket)
            max_keys: Maximum number of keys to return

        Returns:
            List of object metadata dictionaries
        """
        bucket = bucket or self.settings.s3_bucket_raw_documents

        try:
            response = self._client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            objects = []
            for obj in response.get("Contents", []):
                objects.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                        "etag": obj["ETag"],
                    }
                )

            return objects

        except ClientError as e:
            logger.error(
                "document_list_failed",
                bucket=bucket,
                prefix=prefix,
                error=str(e),
            )
            raise

    async def get_object_metadata(
        self,
        key: str,
        bucket: str | None = None,
    ) -> dict[str, Any]:
        """
        Get metadata for an S3 object.

        Args:
            key: S3 object key
            bucket: Bucket name (defaults to raw documents bucket)

        Returns:
            Object metadata dictionary
        """
        bucket = bucket or self.settings.s3_bucket_raw_documents

        try:
            response = self._client.head_object(Bucket=bucket, Key=key)

            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
                "metadata": response.get("Metadata", {}),
            }

        except ClientError as e:
            logger.error(
                "object_metadata_failed",
                bucket=bucket,
                key=key,
                error=str(e),
            )
            raise


# Singleton instance
_s3_client: S3Client | None = None


def get_s3_client(settings: Settings | None = None) -> S3Client:
    """Get or create S3 client singleton."""
    global _s3_client

    if _s3_client is None:
        _s3_client = S3Client(settings)

    return _s3_client
