from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from config import LOCAL_MODEL_NAME

_model = None
_tokenizer = None


def get_model():
    global _model, _tokenizer
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_NAME)
        _model = AutoModelForCausalLM.from_pretrained(
            LOCAL_MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
        )
    return _model, _tokenizer


def generate(prompt: str, max_new_tokens: int = 512) -> str:
    model, tokenizer = get_model()
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
    )
