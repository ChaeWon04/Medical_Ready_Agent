from openai import OpenAI
from config import VLLM_BASE_URL, MODEL_ID, ENABLE_THINKING


class ModelLoader:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            base_url = VLLM_BASE_URL if VLLM_BASE_URL.endswith("/v1") else VLLM_BASE_URL + "/v1"
            cls._instance._client = OpenAI(base_url=base_url, api_key="dummy")
        return cls._instance

    def generate(self, system_prompt: str, user_prompt: str, json_schema=None) -> str:
        extra = {"chat_template_kwargs": {"enable_thinking": ENABLE_THINKING}}
        if json_schema:
            extra["guided_json"] = json_schema

        response = self._client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            extra_body=extra,
        )
        return response.choices[0].message.content


llm = ModelLoader()
