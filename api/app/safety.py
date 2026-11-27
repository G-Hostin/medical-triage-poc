import re

# Deux garde-fous autour du modèle :
# - à l'entrée, refuser un texte qui ne décrit pas un patient, ou qui contient une consigne adressée au modèle
# - à la sortie, relever le niveau à « urgence maximale » si le cas contient un critère de tri 1 ou 2 de FRENCH

# Filtre à l'entrée, volontairement permissif : un vrai cas ne doit jamais être bloqué.
# Un âge, une personne, un verbe de consultation, un symptôme ou une constante suffit.
PATIENT_MARKERS = re.compile(
    r"\d+\s*(?:ans|mois|semaines|jours)\b"
    r"|\b(?:homme|femme|enfant|nourrisson|bébé|nouveau-né|garçon|fille|fillette|adolescent\w*|patient\w*"
    r"|monsieur|madame|mademoiselle|mme|mlle|melle|malade\w*|sujet|individu|personne)\b"
    r"|\b(?:présente|consulte|amenée?|adressée?|hospitalisée?|admise?|opérée?|traitée?|souffre|se plaint|reçoit)\b"
    r"|\b(?:douleur|fièvre|fébri\w*|toux|dyspnée|essoufflé\w*|malaise|vomi\w*|saign\w*|chute|plaie|brûl\w*"
    r"|céphalée|vertige\w*|diarrhée|éruption|fracture|infection|cancer\w*|diabét\w*|tabagi\w*|glycémie)\b"
    r"|\b(?:FC|PA|TA|FR|SpO2|pouls|tension|température)\b"
    # le modèle a aussi appris en anglais : un cas écrit en anglais ne doit pas être bloqué
    r"|\d+[- ]year[- ]old|\b(?:man|woman|boy|girl|child|infant|baby|patient|male|female)\b"
    r"|\b(?:pain|fever|cough|dyspnea|vomiting|bleeding|headache|seizure|rash|BP|HR|RR)\b",
    re.IGNORECASE,
)
INSTRUCTION = re.compile(
    r"\b(?:ignore|oublie)\w*\s+(?:\w+\s+){0,3}(?:consignes?|instructions?|règles?)\b|\b(?:réponds|répondez)\b",
    re.IGNORECASE,
)


def check_input(case: str) -> str | None:
    """Renvoie la raison du refus (« consigne » ou « hors_sujet »), ou None si le texte peut partir au modèle."""
    if INSTRUCTION.search(case):
        return "consigne"
    if not PATIENT_MARKERS.search(case):
        return "hors_sujet"
    return None


# Règle de sécurité : critères de tri 1 ou 2 du référentiel FRENCH.
# Constantes repérées avec les mêmes motifs qu'au notebook 01.
VALUE = r"\s*(?:=|:|est à|est de|à|de)?\s*"
PAS = re.compile(r"\b(?:PA|TA|PAS|pression artérielle|tension artérielle)" + VALUE + r"(\d{2,3})\s*/\s*\d{2,3}", re.I)
FC = re.compile(r"\b(?:FC|fréquence cardiaque|pouls)" + VALUE + r"(\d{2,3})", re.I)
FR = re.compile(r"\b(?:FR|fréquence respiratoire)" + VALUE + r"(\d{1,2})\b", re.I)
SPO2 = re.compile(r"\b(?:SpO2|SaO2|saturation(?: en oxygène)?)" + VALUE + r"(\d{2,3})\s*%", re.I)
TEMPERATURE = re.compile(r"(?:\bT°?|\btempérature|\bfièvre)" + VALUE + r"(\d{2}(?:[.,]\d)?)\s*°", re.I)
GLASGOW = re.compile(r"\b(?:GCS|Glasgow)" + VALUE + r"(\d{1,2})\b", re.I)
AGE = re.compile(r"(\d+)\s*(ans|mois)\b")
CHILD = re.compile(r"\b(?:enfant|nourrisson|bébé|nouveau-né|fillette)\b", re.I)
FEVER = re.compile(r"\bfièvre\b|\bfébrile\b", re.I)

# signes graves écrits en mots
RED_FLAGS = [
    ("arrêt cardiaque", r"arrêt cardi"),
    # FRENCH range le purpura dans les critères du motif « Fièvre » : il ne compte qu'avec de la fièvre
    ("fièvre avec purpura", r"purpura|taches?\b[^.]{0,60}ne s'effacen?t pas"),
    ("coma", r"\bcoma\b|inconscient|ne répond (?:pas|plus)"),
    ("convulsions en cours", r"(?:convulsi\w*|crise)[^.]{0,40}\ben cours\b"),
    ("déficit neurologique", r"hémiplégi\w*|paralys\w*|déficit moteur|aphasi\w*|bouche déformée"),
    ("détresse respiratoire", r"détresse respiratoire|\btirage\b"),
    ("hémorragie digestive", r"hématémèse|vomi\w* du sang|méléna|rectorragie\w* abondante\w*"),
    ("idées suicidaires", r"suicid\w*|mettre fin à ses jours"),
    ("anaphylaxie", r"anaphyla\w*|œdème de quincke"),
    ("morsure de serpent", r"(?:morsure|mordu\w*)[^.]{0,30}(?:vipère|serpent)"),
    ("traumatisme pénétrant", r"coup de couteau|arme blanche|plaie par balle"),
]
# « pas de purpura », « sans détresse respiratoire » : le signe est absent
NEGATION = re.compile(r"\b(?:pas d[e']|sans|ni|absence d[e']|aucune?)\s*(?:\S+\s+){0,2}$", re.I)
# « un de ses oncles a fait une hémiplégie », « antécédent de paralysie » : ce n'est pas le patient aujourd'hui
HISTORY = re.compile(r"antécédent|atcd|\boncles?\b|\btantes?\b|\bpère\b|\bmère\b|grand-|\bfrères?\b|\bsœurs?\b", re.I)


def numbers(pattern: re.Pattern, case: str) -> list[float]:
    return [float(n.replace(",", ".")) for n in pattern.findall(case)]


def patient_age(case: str) -> float | None:
    # premier âge écrit dans le cas (« homme de 70 ans », « nourrisson de 8 mois »)
    match = AGE.search(case)
    if match is None:
        return None
    value = int(match.group(1))
    return value if match.group(2) == "ans" else value / 12


def vital_flag(case: str) -> str | None:
    age = patient_age(case)
    child = (age is not None and age < 16) or (age is None and CHILD.search(case) is not None)

    temperatures = numbers(TEMPERATURE, case)
    if any(t >= 40 or t <= 35.2 for t in temperatures):
        return "température ≥ 40 °C ou ≤ 35,2 °C"
    if any(s <= 90 for s in numbers(SPO2, case)):
        return "SpO2 ≤ 90 %"
    if any(g <= 13 for g in numbers(GLASGOW, case)):
        return "Glasgow ≤ 13"
    if age is not None and age <= 0.25 and (FEVER.search(case) or any(t >= 38 for t in temperatures)):
        return "fièvre avant 3 mois"

    if child:
        # chez l'enfant, FRENCH donne d'autres seuils de pouls ; on ne regarde pas la tension ni la respiration
        limit = 180 if age is not None and age < 1 else 160
        if any(f >= limit for f in numbers(FC, case)):
            return f"pouls ≥ {limit}/min chez l'enfant"
        return None

    # tension écrite en cmHg (18/10) : on la passe en mmHg
    pas = [p * 10 if p < 30 else p for p in numbers(PAS, case)]
    if any(p <= 90 for p in pas):
        return "PAS ≤ 90 mmHg"
    if any(p >= 220 for p in pas):
        return "PAS ≥ 220 mmHg"
    if any(f >= 130 or f <= 40 for f in numbers(FC, case)):
        return "pouls ≥ 130 ou ≤ 40/min"
    if any(f >= 30 for f in numbers(FR, case)):
        return "fréquence respiratoire ≥ 30/min"
    return None


def sentence_at(case: str, position: int) -> str:
    start = case.rfind(".", 0, position) + 1
    end = case.find(".", position)
    return case[start:end if end != -1 else len(case)]


def word_flag(case: str) -> str | None:
    has_fever = FEVER.search(case) is not None or any(t >= 38 for t in numbers(TEMPERATURE, case))
    for label, pattern in RED_FLAGS:
        if label == "fièvre avec purpura" and not has_fever:
            continue
        for match in re.finditer(pattern, case, re.IGNORECASE):
            negated = NEGATION.search(case[max(0, match.start() - 40):match.start()])
            if not negated and not HISTORY.search(sentence_at(case, match.start())):
                return label
    return None


def red_flag(case: str) -> str | None:
    """Renvoie le critère grave trouvé dans le cas, ou None."""
    return vital_flag(case) or word_flag(case)
