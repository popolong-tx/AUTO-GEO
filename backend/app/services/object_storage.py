"""OCI Object Storage service for reading data and storing reports."""

import os
import json
import csv
import io
import base64
from typing import Optional
from datetime import datetime, timedelta, timezone

import oci

try:
    from PIL import Image
except Exception:
    Image = None
try:
    import pandas as pd
except Exception:
    pd = None
from oci.object_storage import ObjectStorageClient


class ObjectStorageService:
    """OCI Object Storage operations."""

    def __init__(
        self,
        namespace: Optional[str] = None,
        config_profile: Optional[str] = None,
    ):
        self.namespace = namespace or os.getenv("OCI_OBJECT_STORAGE_NAMESPACE", "")
        config_profile = config_profile or os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
        try:
            self.config = oci.config.from_file(profile_name=config_profile)
            self.client = ObjectStorageClient(self.config)
        except Exception:
            self.client = None

    async def read_data_file(
        self, bucket: str, object_name: str
    ) -> dict:
        """Read a data file from Object Storage (JSON or CSV)."""
        if not self.client:
            return {"error": "Object Storage client not configured", "source": "disabled"}

        try:
            resp = self.client.get_object(self.namespace, bucket, object_name)
            raw_bytes = resp.data.content if hasattr(resp.data, 'content') else resp.data.read()
            content = raw_bytes.decode('utf-8', errors='ignore')

            if object_name.endswith(".json"):
                return {"format": "json", "data": json.loads(content)}
            elif object_name.endswith(".csv"):
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
                return {"format": "csv", "data": rows, "columns": list(rows[0].keys()) if rows else []}
            elif object_name.endswith(('.xlsx', '.xls')):
                if pd is None:
                    return {"format": "excel", "error": "pandas/openpyxl not installed", "preview": content[:500]}
                df = pd.read_excel(io.BytesIO(raw_bytes))
                rows = df.fillna('').to_dict(orient='records')
                return {"format": "excel", "data": rows, "columns": list(df.columns), "sheet_rows": len(rows), "sheet_name": getattr(df, 'name', None) or 'Sheet1'}
            else:
                return {"format": "text", "data": content}
        except Exception as e:
            return {"error": str(e), "source": "object_storage.read_data_file"}


    async def extract_reference_text(
        self,
        bucket: str,
        object_name: str,
        max_chars: int = 12000,
    ) -> dict:
        """Extract a text preview from a stored reference file when possible."""
        if not self.client:
            return {"error": "Object Storage client not configured", "source": "disabled"}

        try:
            resp = self.client.get_object(self.namespace, bucket, object_name)
            raw_bytes = resp.data.content if hasattr(resp.data, 'content') else resp.data.read()
            content = raw_bytes.decode('utf-8', errors='ignore')
            lower = object_name.lower()
            if lower.endswith('.pdf'):
                return {"format": "pdf", "data": '', "note": "PDF text extraction is not enabled in object storage service"}
            if lower.endswith('.json'):
                return {"format": "json", "data": json.loads(content), "preview": content[:max_chars]}
            if lower.endswith('.csv'):
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
                return {"format": "csv", "data": rows, "preview": content[:max_chars]}
            return {"format": 'text', "data": content[:max_chars], "preview": content[:max_chars]}
        except Exception as e:
            return {"error": str(e), "source": "object_storage.extract_reference_text"}


    async def extract_image_reference(
        self,
        bucket: str,
        object_name: str,
        max_chars: int = 2000,
    ) -> dict:
        """Return a lightweight image reference summary for JPEG/PNG assets."""
        if not self.client:
            return {"error": "Object Storage client not configured", "source": "disabled"}
        lower = object_name.lower()
        if not (lower.endswith('.jpg') or lower.endswith('.jpeg') or lower.endswith('.png')):
            return {"error": "not_an_image"}
        try:
            return {
                "format": "image",
                "data": {
                    "type": "image_reference",
                    "object_name": object_name,
                    "bucket": bucket,
                    "hint": "JPEG/PNG image file uploaded as reference material. Use OCR/vision if available; otherwise treat as auxiliary evidence.",
                },
                "preview": f"Image reference: {object_name}",
            }
        except Exception as e:
            return {"error": str(e), "source": "object_storage.extract_image_reference"}



    def resize_image_bytes(self, raw: bytes, max_side: int = 512, quality: int = 85) -> tuple[bytes, str, dict]:
        """Resize an image to stay close to the 512x512 target before base64 encoding."""
        if Image is None:
            return raw, 'image/jpeg', {'resized': False, 'reason': 'Pillow not installed'}
        try:
            img = Image.open(io.BytesIO(raw))
            img = img.convert('RGB')
            w, h = img.size
            scale = min(max_side / max(w, h), 1.0)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            if new_size != img.size:
                img = img.resize(new_size, Image.LANCZOS)
            out = io.BytesIO()
            img.save(out, format='JPEG', quality=quality, optimize=True)
            meta = {'resized': True, 'width': img.size[0], 'height': img.size[1], 'quality': quality}
            return out.getvalue(), 'image/jpeg', meta
        except Exception as e:
            return raw, 'image/jpeg', {'resized': False, 'reason': str(e)}

    async def read_reference_base64(
        self,
        bucket: str,
        object_name: str,
        max_bytes: int = 1024 * 1024,
        max_pixels_hint: int = 1792,
    ) -> dict:
        """Read an image file and return a base64 payload for direct multimodal input."""
        if not self.client:
            return {"error": "Object Storage client not configured", "source": "disabled"}
        lower = object_name.lower()
        if not (lower.endswith('.jpg') or lower.endswith('.jpeg') or lower.endswith('.png')):
            return {"error": "not_an_image"}
        try:
            resp = self.client.get_object(self.namespace, bucket, object_name)
            raw = resp.data.content if hasattr(resp.data, 'content') else resp.data.read()
            if len(raw) > max_bytes:
                raw = raw[:max_bytes]
            raw, mime, resize_meta = self.resize_image_bytes(raw)
            b64 = base64.b64encode(raw).decode('ascii')
            return {
                'format': 'image',
                'mime_type': mime,
                'base64': b64,
                'byte_length': len(raw),
                'token_hint': 'target 256-1792 tokens per image; keep source image around 512x512 when possible',
                'max_pixels_hint': max_pixels_hint,
                'resize_meta': resize_meta,
                'object_name': object_name,
            }
        except Exception as e:
            return {'error': str(e), 'source': 'object_storage.read_reference_base64'}

    async def upload_reference_file(
        self,
        bucket: str,
        object_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict:
        """Upload a user reference file to Object Storage."""
        if not self.client:
            return {"error": "Object Storage client not configured", "source": "disabled"}

        try:
            self.client.put_object(
                self.namespace,
                bucket,
                object_name,
                content,
                content_type=content_type,
            )
            return {"status": "success", "object_name": object_name}
        except Exception as e:
            return {"error": str(e), "source": "object_storage.upload_reference_file"}

    async def get_object_url(self, bucket: str, object_name: str) -> str:
        if not self.client:
            return ""
        try:
            endpoint = self.client.base_client.endpoint.rstrip('/')
            return f"{endpoint}/n/{self.namespace}/b/{bucket}/o/{object_name.replace('/', '%2F')}"
        except Exception:
            return ""

    async def upload_report(
        self,
        bucket: str,
        object_name: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> dict:
        """Upload a PDF report to Object Storage."""
        if not self.client:
            return {"error": "Object Storage client not configured", "source": "disabled"}

        try:
            self.client.put_object(
                self.namespace,
                bucket,
                object_name,
                content,
                content_type=content_type,
            )
            return {"status": "success", "object_name": object_name}
        except Exception as e:
            return {"error": str(e), "source": "object_storage.upload_report"}

    async def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expiry_hours: int = 24,
    ) -> str:
        """Generate a pre-signed URL for downloading a report.

        Note: This uses Object Storage pre-authenticated request support.
        """
        if not self.client:
            return ""

        try:
            par_manager = oci.object_storage.ObjectStorageClientCompositeOperations(self.client)
            par_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
                name=f"report-{object_name}",
                access_type="ObjectRead",
                time_expires=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
                bucket_listing_action="Deny",
            )
            par = par_manager.create_preauthenticated_request_and_wait_for_state(
                self.namespace, bucket, par_details
            )
            endpoint = self.client.base_client.endpoint.rstrip('/')
            return f"{endpoint}{par.data.access_uri}"
        except Exception as e:
            return ""

    async def list_reports(
        self, bucket: str, topic_id: str
    ) -> list[dict]:
        """List all reports for a given topic."""
        if not self.client:
            return []

        try:
            prefix = f"reports/{topic_id}/"
            resp = self.client.list_objects(
                self.namespace, bucket, prefix=prefix
            )
            reports = []
            for obj in resp.data.objects:
                reports.append({
                    "name": obj.name,
                    "size": obj.size,
                    "time_created": obj.time_created.isoformat() if obj.time_created else None,
                })
            return sorted(reports, key=lambda x: x["time_created"] or "", reverse=True)
        except Exception as e:
            return []

    async def delete_report(
        self, bucket: str, object_name: str
    ) -> bool:
        """Delete a report from Object Storage."""
        if not self.client:
            return False

        try:
            self.client.delete_object(self.namespace, bucket, object_name)
            return True
        except Exception:
            return False
