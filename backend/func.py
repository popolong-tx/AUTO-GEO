"""OCI Functions entry point."""

import json
import io
import asyncio
from fdk import response

from app.main import app


async def handle_async(data):
    """Handle async function invocation."""
    try:
        body = {}
        if data:
            body = json.loads(data.getvalue())

        method = body.get("method", "GET")
        path = body.get("path", "/health")
        query = body.get("query", {})
        headers = body.get("headers", {})

        # Use TestClient for internal routing
        from starlette.testclient import TestClient
        client = TestClient(app)

        if method == "GET":
            resp = client.get(path, params=query, headers=headers)
        elif method == "POST":
            resp = client.post(path, json=body.get("body", {}), headers=headers)
        elif method == "PUT":
            resp = client.put(path, json=body.get("body", {}), headers=headers)
        elif method == "DELETE":
            resp = client.delete(path, headers=headers)
        else:
            return {"statusCode": 405, "body": {"error": "Method not allowed"}}

        return {
            "statusCode": resp.status_code,
            "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
        }
    except Exception as e:
        return {"statusCode": 500, "body": {"error": str(e)}}


def handler(ctx, data: io.BytesIO = None):
    """OCI Functions handler."""
    try:
        result = asyncio.run(handle_async(data))
        return response.Response(
            ctx,
            response_data=json.dumps(result.get("body", {})),
            status_code=result.get("statusCode", 200),
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        return response.Response(
            ctx,
            response_data=json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"},
        )
