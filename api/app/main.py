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

STATIC_DIR = Path(__file__).parent / "static"

WARNING = (
    "Aide au tri destinée à l'infirmier organisateur de l'accueil (IOA). "
    "Elle ne remplace pas son évaluation. "
    "Les niveaux proposés n'ont pas été validés cliniquement. "
    "Prototype (POC) entraîné sur des données publiques."
)
WARNING_INVALID = "Réponse du modèle hors format : faire un tri manuel. " + WARNING

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
        "statut": "erreur_modele",
        "latence_ms": 0,
    }

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

    entry.update(
        reponse_brute=raw_answer,
        niveau=parsed["niveau"],
        tri=parsed["tri"],
        statut=status,
        latence_ms=elapsed_ms(start),
    )
    write_entry(entry)

    return TriageResponse(
        id=entry["id"],
        **parsed,
        reponse_brute=raw_answer,
        statut=status,
        version_modele=llm.MODEL_VERSION,
        latence_ms=entry["latence_ms"],
        avertissement=WARNING if status == "ok" else WARNING_INVALID,
    )
