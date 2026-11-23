import pytest
from fastapi.testclient import TestClient

from app import llm
from app.main import app

API_KEY = "cle-de-test"


@pytest.fixture
def log_path(tmp_path, monkeypatch):
    path = tmp_path / "interactions.jsonl"
    monkeypatch.setenv("LOG_PATH", str(path))
    return path


@pytest.fixture
def client(log_path, monkeypatch):
    monkeypatch.setenv("API_KEY", API_KEY)
    return TestClient(app)


@pytest.fixture
def fake_model(monkeypatch):
    # remplace l'appel à vLLM : on choisit la réponse (ou l'erreur) renvoyée par le « modèle »
    def install(answer=None, error=None):
        async def fake_generate(prompt):
            if error is not None:
                raise error
            return answer

        monkeypatch.setattr(llm, "generate", fake_generate)

    return install
