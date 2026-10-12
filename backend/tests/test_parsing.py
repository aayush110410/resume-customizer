import pytest

from app.parsing.extract import ParseError, detect_type, parse_resume


def test_simple_pdf(simple_pdf):
    r = parse_resume(simple_pdf, max_pages=5)
    assert "Experience" in r.text and "Reduced p99 latency by 30%" in r.text
    assert r.layout.file_type == "pdf" and r.layout.pages == 1
    assert not r.layout.multi_column and not r.layout.has_tables and r.layout.hidden_chars == 0
    assert r.layout.word_count > 50 and r.layout.char_count == len(r.text)


def test_two_column_detected(two_column_pdf):
    assert parse_resume(two_column_pdf, 5).layout.multi_column


def test_hidden_text_excluded_and_counted(hidden_text_pdf):
    r = parse_resume(hidden_text_pdf, 5)
    assert r.layout.hidden_chars >= len("Kubernetes Terraform") - 1
    assert "Terraform" not in r.text


@pytest.mark.parametrize(
    "fx,code", [("scanned_pdf", "SCANNED_PDF"), ("encrypted_pdf", "ENCRYPTED_PDF"), ("six_page_pdf", "TOO_MANY_PAGES")]
)
def test_rejections(request, fx, code):
    with pytest.raises(ParseError) as e:
        parse_resume(request.getfixturevalue(fx), 5)
    assert e.value.code == code


def test_simple_docx(simple_docx):
    r = parse_resume(simple_docx, 5)
    assert r.layout.file_type == "docx" and "Mentored four engineers" in r.text and not r.layout.has_tables


def test_docx_table_and_header_detected(docx_with_table):
    r = parse_resume(docx_with_table, 5)
    assert r.layout.has_tables and "B.Tech" in r.text and "8.4/10" in r.text
    assert r.layout.header_footer_text


@pytest.mark.parametrize("data,code", [(b"GIF89a" + b"0" * 300, "INVALID_FILE_TYPE"), (b"", "EMPTY_FILE")])
def test_detect_type_rejects(data, code):
    with pytest.raises(ParseError) as e:
        detect_type(data)
    assert e.value.code == code


def test_corrupt_pdf():
    with pytest.raises(ParseError) as e:
        parse_resume(b"%PDF-1.7 garbage" * 20, 5)
    assert e.value.code == "CORRUPT_FILE"
