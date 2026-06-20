import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from config import MODEL_ID, LOAD_IN_4BIT, DEVICE_MAP, MAX_NEW_TOKENS, TEMPERATURE, ENABLE_THINKING


class ModelLoader:
    """Qwen3-4B 싱글톤 로더 — 모든 Agent가 같은 인스턴스 사용"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        print(f"[ModelLoader] {MODEL_ID} 로딩 중...")
        self.tokenizer, self.model = self._load()
        self._initialized = True
        print("[ModelLoader] 로딩 완료")

    def _load(self):
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=LOAD_IN_4BIT,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        ) if LOAD_IN_4BIT else None

        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            quantization_config=bnb_config,
            device_map=DEVICE_MAP,
            torch_dtype=torch.float16,
        )
        model.eval()
        return tokenizer, model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=ENABLE_THINKING,
        )
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=TEMPERATURE,
                do_sample=TEMPERATURE > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = outputs[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()


llm = ModelLoader()
