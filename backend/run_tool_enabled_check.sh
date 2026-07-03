#!/usr/bin/env bash
set -euo pipefail

: "${OCI_GENAI_API_KEY:?set OCI_GENAI_API_KEY first}"
: "${OCI_GENAI_ENDPOINT:=https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1}"
: "${OCI_GENAI_MODEL:=xai.grok-4.20-multi-agent-0309}"

export OCI_GENAI_ENDPOINT OCI_GENAI_MODEL
export PYTHONPATH="$(pwd)"

python3 - <<'PY2'
import asyncio
import sys
from app.services.genai_client import GenAIClient

async def main():
    c = GenAIClient()
    print('python=', sys.executable)
    print('api_key_present=', bool(c.api_key))
    print('api_key_prefix=', (c.api_key[:4] + '...' if c.api_key else ''))
    print('base_url=', c.base_url)
    print('default_model=', c.default_model)
    try:
        print('client_class=', type(c.client).__name__)
    except Exception as e:
        print('client_init_error=', type(e).__name__, e)
    try:
        out = await c.analyze_with_tools(
            '请用搜索工具查找最近关于比亚迪闪充发布会的公开舆情，并给出简短结论。',
            model=c.default_model,
            tools=[{'type': 'x_search'}, {'type': 'web_search'}],
            max_tokens=512,
        )
        print('---RESULT START---')
        print(out[:4000])
        print('---RESULT END---')
    except Exception as e:
        print('ERROR:', type(e).__name__, e)

asyncio.run(main())
PY2
