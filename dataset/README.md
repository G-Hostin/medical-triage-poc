---
language:
- fr
- en
license: other
pretty_name: Corpus médical bilingue pour le POC de triage du CHSA
task_categories:
- question-answering
- text-generation
tags:
- medical
- sft
- dpo
size_categories:
- 1K<n<10K
configs:
- config_name: sft
  data_files:
  - split: train
    path: sft_train.jsonl
  - split: validation
    path: sft_val.jsonl
  - split: test
    path: sft_test.jsonl
- config_name: dpo
  data_files:
  - split: train
    path: dpo_train.jsonl
  - split: validation
    path: dpo_val.jsonl
- config_name: eval_mediqal_qcu
  data_files:
  - split: test
    path: eval_mediqal_qcu.jsonl
- config_name: eval_mediqal_qcm
  data_files:
  - split: test
    path: eval_mediqal_qcm.jsonl
- config_name: eval_frenchmedmcqa
  data_files:
  - split: test
    path: eval_frenchmedmcqa.jsonl
- config_name: eval_ultramedical
  data_files:
  - split: test
    path: eval_ultramedical.jsonl
---

# Corpus médical bilingue pour le POC de triage du CHSA

Version 1.0. Jeu de données préparé pour un projet de formation : le fine-tuning supervisé (SFT) puis l'alignement par préférences (DPO) du modèle Qwen3-1.7B-Base, dans le cadre d'un prototype d'assistant de triage aux urgences. Il ne contient aucune donnée de patient du CHSA, uniquement des corpus publics retravaillés.

Ce jeu de données ne doit pas servir à poser un diagnostic ni à conseiller un patient.

## Contenu

- `sft` : 5 000 paires instruction-réponse, moitié en français et moitié en anglais (4 500 en entraînement, 250 en validation, 250 en test). Format conversationnel : une colonne `messages` avec un message `user` et un message `assistant`.
- `dpo` : 3 300 paires de préférences en anglais (3 000 en entraînement, 300 en validation). Colonnes `prompt`, `chosen` et `rejected`, au format attendu par le `DPOTrainer` de TRL.
- Quatre jeux d'évaluation, jamais utilisés pour l'entraînement : 500 QCM à réponse unique et 300 QCM à réponses multiples tirés du test officiel de MediQAl, les 321 questions de test de FrenchMedMCQA, et les 777 paires de test d'UltraMedical-Preference.

Composition du jeu SFT (entraînement, validation et test réunis) :
- 1 300 QCM à réponse unique et 600 QCM à réponses multiples de MediQAl
- 300 questions ouvertes de MediQAl, dont toutes celles de médecine d'urgence et de réanimation (254)
- 300 QCM de FrenchMedMCQA
- 2 500 questions de MedQuAD, types de questions cliniques seulement

Pour les QCM, la réponse attendue donne la lettre puis le texte de la proposition : « Réponse : A, le vaccin contre la fièvre jaune est obligatoire ».

## Sources et licences

- MediQAl, `ANR-MALADES/MediQAl` : questions d'examens médicaux français, CC BY 4.0.
- FrenchMedMCQA, copie `nthngdy/frenchmedmcqa` de l'original `qanastek/frenchmedmcqa` (Labrak et al.), Apache 2.0. La copie ne garde que les questions à réponse unique.
- MedQuAD, copie `keivalya/MedQuad-MedicalQnADataset` de l'original `abachaa/MedQuAD` (Ben Abacha et Demner-Fushman, BMC Bioinformatics, 2019), CC BY 4.0.
- UltraMedical-Preference, `TsinghuaC3I/UltraMedical-Preference` (Zhang et al., 2024), MIT.

Chaque exemple garde sa source, son identifiant d'origine et sa licence. Une réutilisation doit citer les sources ci-dessus.

## Schéma des métadonnées

Chaque exemple porte les champs suivants, en plus du texte :
- `id` : identifiant stable, construit avec la source et l'identifiant d'origine
- `source`, `sous_source`, `id_origine`, `licence`
- `langue` : `fr` ou `en`
- `tache` : `qcm_reponse_unique`, `qcm_reponses_multiples`, `question_ouverte`, `question_patient` ou `preference`
- `specialite` : spécialité médicale donnée par la source (MediQAl, FrenchMedMCQA), sinon vide
- `type_question` : « Understanding » ou « Reasoning » pour MediQAl, type de question pour MedQuAD, catégorie de la paire pour UltraMedical
- `origine_annotation` et `niveau_confiance` : `eleve` pour une correction officielle d'examen, `moyen` pour un site de santé public ou un classement revu par des experts, `faible` pour une préférence choisie par GPT-4
- `symptomes` et `antecedents` : listes de termes repérés automatiquement dans le cas clinique ou la question
- `constantes` : fréquence cardiaque (`fc`), pression artérielle (`pa`), fréquence respiratoire (`fr`), saturation (`spo2`) et température, quand le texte les donne
- `nb_elements_masques` : nombre d'éléments remplacés à l'anonymisation
- `version`
- Jeu DPO seulement : `note_choisie`, `note_rejetee` (notes de GPT-4 sur 5), `modele_choisi`, `modele_rejete`

Symptômes, antécédents et constantes sont repérés par des listes de mots et des expressions régulières. Le repérage est approximatif et ne couvre qu'une partie des exemples : au moins un symptôme pour 29,7 % des exemples de MediQAl du jeu d'entraînement, au moins une constante pour 16,1 %. Les valeurs sont recopiées telles qu'elles sont écrites, sans contrôle de vraisemblance.

## Préparation

Notebooks du dépôt : `01_preparation_donnees.ipynb` (chargement, nettoyage, format, découpage) et `02_anonymisation.ipynb`. Un journal des transformations (`journal_transformations.json`) donne le nombre de lignes avant et après chaque filtre.

Principaux filtres :
- doublons retirés dans chaque source
- toute question présente dans un jeu de test officiel retirée de l'entraînement (MediQAl partage des questions entre ses parties)
- 1 024 tokens Qwen3 au plus par exemple
- jeu DPO : questions issues de MedQuAD retirées (recoupement avec le SFT), écart d'au moins 1 point sur 5 entre la réponse préférée et l'autre, une paire par question, et autant de paires où la réponse préférée est la plus longue que de paires où elle est la plus courte

## Anonymisation

Les noms et prénoms, les adresses e-mail et les numéros de téléphone sont remplacés par `<PERSONNE>` / `<PERSON>`, `<EMAIL>` et `<TELEPHONE>` / `<PHONE>`, avec Presidio et des règles adaptées au texte médical (920 éléments masqués). L'âge, le sexe, les lieux et les dates sont gardés.

Contrôle manuel sur la version finale : 56 des 60 éléments masqués tirés au hasard étaient de vrais identifiants, et sur 100 détections laissées en place, une seule était un nom de personne (un auteur cité en référence). Le détail est dans le notebook 02.

Limite importante : les jeux d'origine sont publics. Une personne qui dispose de l'original pourrait retrouver un texte et le nom qui y figurait. Au sens du RGPD, ce jeu est désidentifié plutôt qu'anonyme.

## Limites

- Aucun des corpus ne porte sur le triage aux urgences : ce sont des QCM d'examens, des questions de patients et des préférences entre réponses.
- Le jeu DPO est entièrement en anglais.
- Les préférences d'UltraMedical ont été choisies par GPT-4, pas par des médecins (sauf le jeu de test, revu par des experts d'après ses auteurs).
- Les questions de FrenchMedMCQA viennent d'examens de pharmacie.
