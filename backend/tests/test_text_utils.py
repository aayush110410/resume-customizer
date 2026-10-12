from app.text_utils import contains_term, estimate_pages, normalize


def test_normalize_pdf_artifacts():
    assert normalize("Eﬃcient • “API” design – scaled") == 'efficient "api" design - scaled'


def test_normalize_removes_soft_hyphen_and_collapses_space():
    assert normalize("Micro­services   \n deployed") == "microservices deployed"


def test_contains_term_symbols():
    text = "Built services in C++ and Node.js on .NET"
    assert contains_term(text, "c++")
    assert contains_term(text, "node.js")
    assert contains_term(text, ".net")
    assert not contains_term("Used Golang daily", "go")
    assert not contains_term("Expert in C# and Java", "c")


def test_contains_term_is_boundary_aware_for_words():
    assert contains_term("Deployed on AWS Lambda", "aws")
    assert not contains_term("Drew sketches", "aws")


def test_estimate_pages():
    assert estimate_pages(0) == 1
    assert estimate_pages(550) == 1
    assert estimate_pages(551) == 2
