"""
Live smoke test for the OpenCode Go provider.

Run with:
  pytest test_opencode_go_smoke.py -q -s

Or directly:
  python test_opencode_go_smoke.py
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def _build_client() -> tuple[OpenAI, str, float]:
    api_key = os.getenv("OPENCODE_GO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENCODE_GO_API_KEY is empty")

    base_url = os.getenv("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1").strip()
    model_name = os.getenv("OPENCODE_GO_MODEL_NAME", "qwen3.5-plus").strip()
    timeout = float(os.getenv("OPENCODE_GO_API_TIMEOUT", "60"))

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )
    return client, model_name, timeout


def run_opencode_go_smoke_test() -> str:
    client, model_name, timeout = _build_client()

    start = time.time()
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "Reply with a single short sentence."},
            {"role": "user", "content": "Say 'OpenCode Go is working.'"},
        ],
        temperature=0,
        top_p=1,
        max_tokens=32,
    )
    elapsed = time.time() - start

    message = response.choices[0].message
    content = (message.content or getattr(message, "reasoning_content", "") or "").strip()
    if not content:
        raise AssertionError("OpenCode Go returned an empty response")

    print(f"provider=OpenCode Go model={model_name} timeout={timeout:.0f}s elapsed={elapsed:.2f}s")
    print(content)
    return content


def test_opencode_go_chat_completion():
    run_opencode_go_smoke_test()


if __name__ == "__main__":
    run_opencode_go_smoke_test()
