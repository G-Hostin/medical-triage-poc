import asyncio
import json

import httpx

from app import llm


def test_prompt_is_the_training_prompt():
    expected = (
        "<|im_start|>user\nCas clinique : Femme de 30 ans, rhume depuis deux jours."
        "\n\nQuel est le niveau de priorité de ce patient à l'accueil des urgences ?<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    assert llm.build_prompt("Femme de 30 ans, rhume depuis deux jours.") == expected


def test_request_sent_to_vllm(monkeypatch):
    sent = {}

    def handler(request):
        sent["url"] = str(request.url)
        sent["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"text": "Niveau : ..."}]})

    # faux serveur vLLM : httpx.MockTransport répond à la place du réseau
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs)
    )

    assert asyncio.run(llm.generate("un prompt")) == "Niveau : ..."
    assert sent["url"] == llm.VLLM_URL + "/v1/completions"
    assert sent["payload"] == {
        "model": llm.MODEL_NAME,
        "prompt": "un prompt",
        "max_tokens": 450,
        "temperature": 0,
        "stop_token_ids": [151643, 151645],
    }
