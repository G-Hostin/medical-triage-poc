# medical-triage-poc

Prototype d'agent de triage médical pour le Centre Hospitalier Saint-Aurélien (projet de formation OpenClassrooms, parcours AI Engineer). Le modèle Qwen3-1.7B-Base est affiné par fine-tuning supervisé (SFT) avec LoRA, puis aligné par préférences (DPO).

Ce prototype ne pose pas de diagnostic et ne doit pas servir à conseiller des patients.

## Étape 1 : les données

- `notebooks/01_preparation_donnees.ipynb` : chargement des quatre corpus, nettoyage, mise au format conversationnel, métadonnées, jeux d'entraînement et d'évaluation
- `notebooks/02_anonymisation.ipynb` : anonymisation avec Presidio, contrôle manuel, publication
- `notebooks/02b_comparaison_anonymisation.ipynb` : comparaison avec le reconnaisseur médical de Presidio (`MedicalNERRecognizer`)
- `dataset/README.md` : fiche du jeu de données (sources, licences, schéma des métadonnées, limites)
- `livrables/etape1_donnees_rgpd.pdf` : schéma des métadonnées et démarche RGPD

Le jeu de données final (version 1.0) est publié en privé sur Hugging Face. Le dossier `data/` n'est pas versionné : il est recréé par les notebooks.

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
