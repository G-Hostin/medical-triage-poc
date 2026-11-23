from app.parsing import parse_answer


def test_three_lines():
    answer = (
        "Niveau : urgence modérée (tri 3B de l'échelle FRENCH).\n"
        "Explication : Fièvre isolée, constantes normales.\n"
        "Conduite : Réévaluer dans l'heure."
    )
    assert parse_answer(answer) == {
        "niveau": "urgence modérée",
        "tri": "3B",
        "explication": "Fièvre isolée, constantes normales.",
        "conduite": "Réévaluer dans l'heure.",
    }


def test_missing_lines_give_none():
    parsed = parse_answer("Niveau : urgence différée (tri 5 de l'échelle FRENCH).")
    assert parsed["niveau"] == "urgence différée"
    assert parsed["tri"] == "5"
    assert parsed["explication"] is None
    assert parsed["conduite"] is None


def test_wrong_first_line():
    assert parse_answer("") is None
    assert parse_answer("Réponse : C, cathéter sus pubien") is None
    assert parse_answer("Niveau : urgence absolue (tri 2 de l'échelle FRENCH).") is None
    assert parse_answer("Niveau : urgence maximale (tri 7 de l'échelle FRENCH).") is None
