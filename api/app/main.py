import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, StringConstraints

from app import llm
from app.journal import write_entry
from app.parsing import parse_answer
from app.safety import check_input, red_flag

STATIC_DIR = Path(__file__).parent / "static"

WARNING = (
    "Aide au tri destinée à l'infirmier organisateur de l'accueil (IOA). "
    "Elle ne remplace pas son évaluation. "
    "Les niveaux proposés n'ont pas été validés cliniquement. "
    "Prototype (POC) entraîné sur des données publiques."
)
WARNING_INVALID = "Réponse du modèle hors format : faire un tri manuel. "
WARNING_RAISED = "Niveau relevé à urgence maximale par la règle de sécurité (critère : {}). "
REFUSALS = {
    "hors_sujet": "Le texte ne décrit pas un patient : indiquer au moins l'âge, le motif ou les symptômes.",
    "consigne": "Le texte contient une consigne adressée au modèle : décrire seulement le patient.",
}

app = FastAPI(title="API de triage aux urgences (POC)")


class TriageRequest(BaseModel):
    # les espaces au début et à la fin sont retirés avant de vérifier la longueur
    cas: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=4000)]


class TriageResponse(BaseModel):
    id: str
    niveau: Literal["urgence maximale", "urgence modérée", "urgence différée"] | None
    tri: str | None
    explication: str | None
    conduite: str | None
    reponse_brute: str
    statut: Literal["ok", "format_invalide"]
    # niveau écrit par le modèle, et critère grave qui l'a fait relever (None si la règle n'a rien changé)
    niveau_modele: str | None
    regle_securite: str | None
    version_modele: str
    latence_ms: int
    avertissement: str


# en-tête X-API-Key (FastAPI remplace le _ par un tiret)
def check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_KEY")
    # sans clé configurée, tout est refusé
    if not expected or x_api_key is None:
        raise HTTPException(status_code=401, detail="Clé API absente ou invalide")
    # compare_digest : comparaison en temps constant
    if not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Clé API absente ou invalide")


def elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    model_ok = await llm.model_is_up()
    return {
        "api": "ok",
        "modele": "ok" if model_ok else "indisponible",
        "version_modele": llm.MODEL_VERSION,
    }


@app.post("/triage", response_model=TriageResponse, dependencies=[Depends(check_api_key)])
async def triage(request: TriageRequest):
    start = time.perf_counter()
    entry = {
        "id": str(uuid.uuid4()),
        "horodatage": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "version_modele": llm.MODEL_VERSION,
        "cas": request.cas,
        "reponse_brute": "",
        "niveau": None,
        "tri": None,
        "niveau_modele": None,
        "regle_securite": None,
        "statut": "erreur_modele",
        "latence_ms": 0,
    }

    # filtre à l'entrée : le texte refusé n'est pas envoyé au modèle, mais il est journalisé
    refusal = check_input(request.cas)
    if refusal is not None:
        entry.update(statut="refus_" + refusal, latence_ms=elapsed_ms(start))
        write_entry(entry)
        raise HTTPException(status_code=422, detail=REFUSALS[refusal])

    try:
        raw_answer = await llm.generate(llm.build_prompt(request.cas))
    except httpx.HTTPError as error:
        # les échecs sont journalisés aussi, avec le statut erreur_modele
        entry["latence_ms"] = elapsed_ms(start)
        write_entry(entry)
        if isinstance(error, httpx.TimeoutException):
            raise HTTPException(status_code=504, detail="Le modèle n'a pas répondu dans les 60 secondes")
        raise HTTPException(status_code=503, detail="Modèle indisponible")

    parsed = parse_answer(raw_answer)
    if parsed is None:
        status = "format_invalide"
        parsed = {"niveau": None, "tri": None, "explication": None, "conduite": None}
    else:
        status = "ok"
    model_level = parsed["niveau"]

    # règle de sécurité : un critère de tri 1 ou 2 de FRENCH dans le cas impose l'urgence maximale
    flag = red_flag(request.cas)
    if flag is not None and model_level != "urgence maximale":
        # le tri FRENCH du modèle ne correspond plus au niveau : on ne le renvoie pas
        parsed.update(niveau="urgence maximale", tri=None)
    else:
        flag = None

    entry.update(
        reponse_brute=raw_answer,
        niveau=parsed["niveau"],
        tri=parsed["tri"],
        niveau_modele=model_level,
        regle_securite=flag,
        statut=status,
        latence_ms=elapsed_ms(start),
    )
    write_entry(entry)

    warning = WARNING
    if status == "format_invalide":
        warning = WARNING_INVALID + warning
    if flag is not None:
        warning = WARNING_RAISED.format(flag) + warning

    return TriageResponse(
        id=entry["id"],
        **parsed,
        reponse_brute=raw_answer,
        statut=status,
        niveau_modele=model_level,
        regle_securite=flag,
        version_modele=llm.MODEL_VERSION,
        latence_ms=entry["latence_ms"],
        avertissement=warning,
    )
