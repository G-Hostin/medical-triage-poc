---
language:
- fr
- en
license: apache-2.0
base_model: Qwen/Qwen3-1.7B-Base
library_name: transformers
pipeline_tag: text-generation
datasets:
- g-hostin/medical-triage-poc-data
tags:
- medical
- triage
- lora
- dpo
---

# medical-triage-poc-model

Qwen3-1.7B-Base affiné pour proposer un niveau de priorité à l'accueil des urgences. Projet de formation OpenClassrooms (parcours AI Engineer) : prototype (POC) d'aide au triage pour un hôpital fictif, le Centre Hospitalier Saint-Aurélien.

Ce modèle ne doit pas servir à trier de vrais patients. Les niveaux qu'il a appris ont été attribués par un grand modèle selon l'échelle FRENCH, sans validation par des urgentistes.

Code du projet : https://github.com/G-Hostin/medical-triage-poc

## Contenu du dépôt

- à la racine : le modèle `dpo-v1`, c'est-à-dire Qwen3-1.7B-Base avec l'adaptateur LoRA du SFT puis celui du DPO fusionnés dans ses poids (bf16, 3,4 Go). C'est le modèle servi par vLLM dans le projet
- `adapters/sft` et `adapters/dpo` : les deux adaptateurs LoRA, avec leurs réglages dans `run_info.json`. L'adaptateur du DPO a été entraîné sur le modèle SFT déjà fusionné
- l'étiquette `dpo-v1` fixe cette version

## Entraînement

Données : [g-hostin/medical-triage-poc-data](https://huggingface.co/datasets/g-hostin/medical-triage-poc-data), version v1.1.

- SFT avec LoRA (rang 16, alpha 32, dropout 0,05, toutes les couches linéaires) sur 4 860 exemples : QCM et questions ouvertes de médecine en français, questions de patients en anglais et 360 cas de triage. 2 époques, learning rate 2e-4, meilleur checkpoint au pas 1200 (perte de validation 0,706)
- DPO avec le même réglage LoRA sur 3 000 paires d'UltraMedical-Preference, en anglais. 1 époque, learning rate 5e-5, β 0,1, meilleur checkpoint au pas 250 (perte de validation 0,532)
- graine 42, une carte NVIDIA RTX 4070 SUPER de 12 Go, avec TRL 1.18 et PEFT 0.21

## Utilisation

Le modèle a appris un format précis. La question est mise au gabarit ChatML et la réponse se termine par `<|endoftext|>` :

```
<|im_start|>user
Cas clinique : Homme de 55 ans, douleur thoracique en étau depuis 40 minutes, qui irradie dans le bras gauche, avec des sueurs.

Quel est le niveau de priorité de ce patient à l'accueil des urgences ?<|im_end|>
<|im_start|>assistant
```

La réponse tient en trois lignes : « Niveau : urgence ... (tri ... de l'échelle FRENCH). », « Explication : ... » et « Conduite : ... ». Dans le projet, la génération se fait sans hasard (température 0), avec 450 tokens au plus et un arrêt sur les tokens 151643 et 151645.

Pour récupérer le modèle fusionné sans les adaptateurs :

```
hf download g-hostin/medical-triage-poc-model --revision dpo-v1 --exclude "adapters/*" --local-dir models/serve/dpo-v1
```

Le dépôt GitHub le sert avec vLLM (image `vllm/vllm-openai:v0.34.0`) derrière une API FastAPI, avec docker compose.

## Résultats

Mesurés sur des jeux de test jamais vus à l'entraînement, génération sans hasard :
- niveau de priorité juste sur 97 cas de triage : 68,0 %
- urgences maximales reconnues : 90,7 % (39 sur 43) avec Transformers, 88,4 % (38 sur 43) servi par vLLM
- aucune urgence maximale classée en urgence différée
- format respecté et arrêt seul : 94,8 %
- réponses qui citent une constante absente du cas : 2,1 %
- 30 cas pièges écrits à partir des critères graves de FRENCH : 29 en urgence maximale, aucun en différée
- 1 121 QCM médicaux en français : 32,1 % de bonnes réponses, contre 22,2 % pour le modèle de base
- 777 paires de préférences revues par des experts : réponse préférée jugée plus probable dans 43,2 % des paires, contre 30,0 % pour le modèle de base

## Limites

- une aide au tri, pas un diagnostic : le niveau proposé doit être validé par un soignant
- les cas de triage ont été étiquetés par un grand modèle via l'API d'Anthropic, selon l'échelle FRENCH, puis relus pour leur cohérence seulement
- le modèle est trop prudent : il classe souvent un cas bénin au-dessus de son niveau
- les explications peuvent contenir des erreurs même quand le niveau est bon
- il a appris sur des cas d'examens rédigés en français médical, et les seuils de FRENCH sont pensés pour l'adulte
- seul, il donne un niveau même à une question sans rapport avec la médecine et peut suivre une consigne glissée dans le cas. Dans le projet, l'API ajoute un filtre à l'entrée et une règle de sécurité à la sortie

## Licence

Apache 2.0, comme Qwen3-1.7B-Base. Les données d'entraînement gardent leurs propres licences, décrites sur la fiche du jeu de données.
