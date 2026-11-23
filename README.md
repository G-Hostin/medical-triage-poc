# medical-triage-poc

Prototype d'agent de triage médical pour le Centre Hospitalier Saint-Aurélien (projet de formation OpenClassrooms, parcours AI Engineer). Le modèle Qwen3-1.7B-Base est affiné par fine-tuning supervisé (SFT) avec LoRA, puis aligné par préférences (DPO).

Ce prototype ne pose pas de diagnostic et ne doit pas servir à conseiller des patients.

## Étape 1 : les données

- `notebooks/01_preparation_donnees.ipynb` : chargement des quatre corpus, nettoyage, mise au format conversationnel, métadonnées, jeux d'entraînement et d'évaluation
- `notebooks/02_anonymisation.ipynb` : anonymisation avec Presidio, contrôle manuel, publication
- `notebooks/02b_comparaison_anonymisation.ipynb` : comparaison avec le reconnaisseur médical de Presidio (`MedicalNERRecognizer`)
- `notebooks/03_triage.ipynb` : cas cliniques classés avec l'échelle de tri FRENCH (SFMU) par l'API Anthropic, version 1.1 du jeu
- `dataset/README.md` : fiche du jeu de données (sources, licences, schéma des métadonnées, limites)
- `livrables/etape1_donnees_rgpd.pdf` : schéma des métadonnées et démarche RGPD

Le jeu de données est publié en privé sur Hugging Face (version 1.0, puis 1.1 avec les cas de triage). Le dossier `data/` n'est pas versionné : il est recréé par les notebooks.

## Installation

Python 3.12 et [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Lancement

Les notebooks se lancent dans l'ordre, depuis le dossier `notebooks/` :

```bash
uv run jupyter lab
```

Le notebook 01 télécharge les corpus depuis Hugging Face (environ 1 Go pour UltraMedical-Preference). Le notebook 02 met environ six minutes à anonymiser l'ensemble des fichiers. Sa dernière cellule publie le jeu de données : il faut être connecté avec `uv run hf auth login`.

Le notebook 03 appelle l'API Anthropic : copier `.env.example` en `.env` et y mettre une clé (`ANTHROPIC_API_KEY`). Les réponses sont gardées dans `data/interim/triage_reponses.jsonl`, une relance ne rappelle pas l'API.

## Démo locale

Il faut une carte graphique NVIDIA et Docker Desktop. Le modèle fusionné (adaptateurs LoRA du SFT et du DPO intégrés aux poids, avec le tokenizer) doit se trouver dans `models/serve/dpo-v1/` (`sft-v1` pour le modèle après le SFT seul). Le nom du dossier est celui de `MODEL_VERSION` dans `.env`.

Deux services dans `docker-compose.yml` :

- `vllm` sert le modèle. Son port n'est pas publié, seule l'API peut l'appeler
- `api` (FastAPI, dossier `api/`) vérifie la clé, construit le prompt, découpe la réponse du modèle et écrit le journal

```bash
docker compose up -d
```

vLLM met plusieurs minutes à charger le modèle, l'API ne démarre qu'une fois qu'il est prêt. Après une modification du code de l'API, ajouter `--build`.

La page de démo est sur http://localhost:8090. La clé à saisir est la valeur de `API_KEY` dans `.env` (voir `.env.example`). `GET /health` indique si le modèle répond.

```bash
docker compose logs -f api
docker compose logs -f vllm
```

Chaque appel à `POST /triage` ajoute une ligne JSON dans `logs/interactions.jsonl` (identifiant, horodatage, version du modèle, cas, réponse brute, niveau, tri, statut, latence), y compris quand le modèle ne répond pas.

Les tests de l'API simulent le modèle et tournent sans carte graphique :

```bash
cd api
uv sync
uv run pytest
```

GitHub Actions lance ces tests à chaque push sur `main` et à chaque pull request. Sur `main`, il publie ensuite l'image de l'API sur `ghcr.io/g-hostin/medical-triage-poc-api` (étiquettes `latest` et SHA du commit).
