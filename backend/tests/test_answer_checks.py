from app.evaluation.answer_checks import (
    check_citations,
    parse_judge_response,
    split_claims,
)

A = "german-laws::stgb::sec-211-mord"
B = "german-laws::stgb::sec-212-totschlag"


def test_split_keeps_legal_abbreviations_inside_one_claim() -> None:
    claims = split_claims(
        "Nach § 438 Abs. 1 Nr. 3 BGB gilt eine Frist von zwei Jahren. Das ist kurz."
    )
    assert claims == [
        "Nach § 438 Abs. 1 Nr. 3 BGB gilt eine Frist von zwei Jahren.",
        "Das ist kurz.",
    ]


def test_citation_after_full_stop_belongs_to_previous_claim() -> None:
    answer = f"Mord wird lebenslang bestraft. [{A}] Totschlag mindestens fünf Jahre. [{B}]"
    check = check_citations(answer, {A, B})

    assert len(check.claims) == 2
    assert check.all_claims_cited
    assert check.citation_coverage == 1.0


def test_list_items_are_claims_and_list_intro_is_not() -> None:
    answer = f"Die Unterschiede sind:\n- Mord braucht ein Mordmerkmal [{A}]\n- Totschlag nicht"
    check = check_citations(answer, {A, B})

    assert check.claims == [f"Mord braucht ein Mordmerkmal [{A}]", "Totschlag nicht"]
    assert check.uncited_claims == ["Totschlag nicht"]
    assert check.citation_coverage == 0.5


def test_unknown_citations_are_reported() -> None:
    check = check_citations(f"Mord ist strafbar [{A}, german-laws::stgb::sec-999].", {A})
    assert check.invalid_citations == ["german-laws::stgb::sec-999"]


def test_empty_answer_is_not_fully_cited() -> None:
    assert not check_citations("", {A}).all_claims_cited


def test_parse_judge_response() -> None:
    assert parse_judge_response('Sure: {"score": 4, "reason": "ok"}') == {
        "score": 4,
        "reason": "ok",
    }
    assert parse_judge_response('{"score": 9}')["score"] is None
    assert parse_judge_response("no json")["score"] is None
