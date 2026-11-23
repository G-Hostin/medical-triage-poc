import json
import uuid

import httpx

from app import llm
from tests.conftest import API_KEY

CASE = "Homme de 55 ans, douleur thoracique en étau depuis 40 minutes, qui irradie dans le bras gauche, avec des sueurs."
MODEL_ANSWER = (
    "Niveau : urgence maximale (tri 2 de l'échelle FRENCH).\n"
    "Explication : Douleur thoracique typique d'un syndrome coronarien aigu.\n"
    "Conduite : ECG dans les 10 minutes et avis médical immédiat."
)
LOG_FIELDS = {"id", "horodatage", "version_modele", "cas", "reponse_brute", "niveau", "tri", "statut", "latence_ms"}


def post_case(client, case=CASE, key=API_KEY):
    headers = {"X-API-Key": key} if key is not None else {}
    return client.post("/triage", json={"cas": case}, headers=headers)


def read_log(log_path):
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_missing_key_is_refused(client, fake_model, log_path):
    fake_model(answer=MODEL_ANSWER)
    assert post_case(client, key=None).status_code == 401
    assert not log_path.exists()


def test_wrong_key_is_refused(client, fake_model, log_path):
    fake_model(answer=MODEL_ANSWER)
    assert post_case(client, key="mauvaise-cle").status_code == 401
    assert not log_path.exists()


def test_empty_case_is_refused(client, fake_model, log_path):
    fake_model(answer=MODEL_ANSWER)
    assert post_case(client, case="   ").status_code == 422
    # 19 caractères une fois les espaces retirés
    assert post_case(client, case="     " + "a" * 19 + "     ").status_code == 422
    assert not log_path.exists()


def test_too_long_case_is_refused(client, fake_model):
    fake_model(answer=MODEL_ANSWER)
    assert post_case(client, case="a" * 4001).status_code == 422


def test_triage_ok(client, fake_model, log_path):
    fake_model(answer=MODEL_ANSWER)
    response = post_case(client, case="  " + CASE + "  ")
    assert response.status_code == 200

    data = response.json()
    assert uuid.UUID(data["id"]).version == 4
    assert data["niveau"] == "urgence maximale"
    assert data["tri"] == "2"
    assert data["explication"] == "Douleur thoracique typique d'un syndrome coronarien aigu."
    assert data["conduite"] == "ECG dans les 10 minutes et avis médical immédiat."
    assert data["reponse_brute"] == MODEL_ANSWER
    assert data["statut"] == "ok"
    assert data["version_modele"] == llm.MODEL_VERSION
    assert isinstance(data["latence_ms"], int)
    assert "IOA" in data["avertissement"]

    entries = read_log(log_path)
    assert len(entries) == 1
    entry = entries[0]
    assert set(entry) == LOG_FIELDS
    assert entry["id"] == data["id"]
    assert entry["cas"] == CASE
    assert entry["reponse_brute"] == MODEL_ANSWER
    assert entry["niveau"] == "urgence maximale"
    assert entry["tri"] == "2"
    assert entry["statut"] == "ok"
    assert entry["version_modele"] == llm.MODEL_VERSION
    assert entry["latence_ms"] == data["latence_ms"]
    assert entry["horodatage"].endswith("+00:00")


def test_invalid_format(client, fake_model, log_path):
    fake_model(answer="Je pense que ce patient doit être vu rapidement.")
    response = post_case(client)
    assert response.status_code == 200

    data = response.json()
    assert data["statut"] == "format_invalide"
    assert data["niveau"] is None
    assert data["tri"] is None
    assert "tri manuel" in data["avertissement"]
    assert read_log(log_path)[0]["statut"] == "format_invalide"


def test_model_unreachable(client, fake_model, log_path):
    fake_model(error=httpx.ConnectError("connexion refusée"))
    assert post_case(client).status_code == 503

    entry = read_log(log_path)[0]
    assert set(entry) == LOG_FIELDS
    assert entry["statut"] == "erreur_modele"
    assert entry["niveau"] is None


def test_model_timeout(client, fake_model, log_path):
    fake_model(error=httpx.ReadTimeout("délai dépassé"))
    assert post_case(client).status_code == 504
    assert read_log(log_path)[0]["statut"] == "erreur_modele"


def test_health(client, monkeypatch):
    async def model_up():
        return True

    async def model_down():
        return False

    monkeypatch.setattr(llm, "model_is_up", model_up)
    assert client.get("/health").json() == {"api": "ok", "modele": "ok", "version_modele": llm.MODEL_VERSION}

    monkeypatch.setattr(llm, "model_is_up", model_down)
    assert client.get("/health").json()["modele"] == "indisponible"


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Clé API" in response.text
