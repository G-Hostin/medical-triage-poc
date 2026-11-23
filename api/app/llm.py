import os

import httpx

# Dans docker compose, le service vllm n'est joignable que depuis le réseau interne
VLLM_URL = os.getenv("VLLM_URL") or "http://vllm:8000"
MODEL_NAME = os.getenv("MODEL_NAME") or "triage"
MODEL_VERSION = os.getenv("MODEL_VERSION") or "sft-v1"

TIMEOUT = 60  # secondes
MAX_TOKENS = 450
# <|endoftext|> et <|im_end|> : le modèle a appris à finir sa réponse par <|endoftext|>
STOP_TOKEN_IDS = [151643, 151645]

QUESTION = "Quel est le niveau de priorité de ce patient à l'accueil des urgences ?"


def build_prompt(case: str) -> str:
    # Même texte qu'à l'entraînement (gabarit ChatML du tokenizer de Qwen3), sinon le modèle répond moins bien
    return (
        "<|im_start|>user\nCas clinique : " + case + "\n\n" + QUESTION + "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


async def generate(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "stop_token_ids": STOP_TOKEN_IDS,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(f"{VLLM_URL}/v1/completions", json=payload)
        response.raise_for_status()
    return response.json()["choices"][0]["text"]


async def model_is_up() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{VLLM_URL}/health")
        return response.status_code == 200
    except httpx.HTTPError:
        return False
