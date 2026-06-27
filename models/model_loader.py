#model_loader.py를 vLLM 버전으로 덮어쓰기 (← 이게 핵심. 안 하면 또 Qwen3-4B 로딩하다 죽음)
import os
from openai import OpenAI

from config import MODEL_ID, TEMPERATURE, MAX_NEW_TOKENS, ENABLE_THINKING

try:
    from config import VLLM_BASE_URL
except ImportError:
    VLLM_BASE_URL = "http://localhost:8000/v1"

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", VLLM_BASE_URL)
MODEL_ID = os.getenv("MODEL_ID", MODEL_ID)


class ModelLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = OpenAI(
                base_url=VLLM_BASE_URL,
                api_key="dummy",
                timeout=120.0,
            )
            print(f"[ModelLoader] vLLM 연결 {VLLM_BASE_URL} | model={MODEL_ID}")
        return cls._instance

    def generate(self, system_prompt: str, user_prompt: str, json_schema: dict | None = None) -> str:
        extra_body = {"chat_template_kwargs": {"enable_thinking": ENABLE_THINKING}}
        if json_schema is not None:
            extra_body["structured_outputs"] = {"json": json_schema}
        resp = self._client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_NEW_TOKENS,
            extra_body=extra_body,
        )
        return resp.choices[0].message.content


llm = ModelLoader()
