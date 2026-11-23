import re

# Première ligne attendue : « Niveau : urgence maximale (tri 2 de l'échelle FRENCH). »
LEVEL_LINE = re.compile(
    r"^Niveau : (urgence maximale|urgence modérée|urgence différée) "
    r"\(tri (1|2|3A|3B|4|5) de l'échelle FRENCH\)\.?$"
)


def parse_answer(text: str) -> dict | None:
    """Renvoie niveau, tri, explication et conduite, ou None si la première ligne n'a pas le bon format."""
    lines = text.strip().splitlines()
    if not lines:
        return None
    match = LEVEL_LINE.match(lines[0].strip())
    if match is None:
        return None

    explanation = None
    conduct = None
    for line in lines[1:]:
        if line.startswith("Explication :"):
            explanation = line.split(":", 1)[1].strip()
        elif line.startswith("Conduite :"):
            conduct = line.split(":", 1)[1].strip()

    return {
        "niveau": match.group(1),
        "tri": match.group(2),
        "explication": explanation,
        "conduite": conduct,
    }
