import pytest

from codify.clauses import parse_text, read_policy


def test_numbered_clauses_sections_and_wrapped_lines():
    p = parse_text("Password Policy\n\n1. Passwords\n1.1 Passwords shall be changed\nevery 90 days.\n"
                   "1.2 Users shall lock screens.\n\n## 2. Email\n2.1 Email shall be filtered.\n")
    assert p.title == "Password Policy"
    assert [(c.id, c.section, c.heading, c.text) for c in p.clauses] == [
        ("1.1", "1", "Passwords", "Passwords shall be changed every 90 days."),
        ("1.2", "1", "Passwords", "Users shall lock screens."),
        ("2.1", "2", "Email", "Email shall be filtered."),
    ]


def test_lettered_items_carry_their_lead_in():
    p = parse_text("1.2 Users shall:\n(a) not share passwords;\nb) lock their screens.")
    assert [(c.id, c.text) for c in p.clauses] == [
        ("1.2(a)", "Users shall not share passwords;"), ("1.2(b)", "Users shall lock their screens.")]


def test_unnumbered_paragraphs_and_bullets_get_ids():
    p = parse_text("# Remote Work\n\n## Devices\nStaff shall use managed laptops.\n\n- Laptops shall be encrypted.\n"
                   "- Screens shall lock after 5 minutes.")
    assert [c.id for c in p.clauses] == ["p-p1", "p-1", "p-2"]
    assert p.title == "Remote Work" and p.clauses[1].heading == "Devices"


def test_markdown_tables_and_notes_are_skipped():
    p = parse_text("# Policy\n| Version | 3 |\n| --- | --- |\n*Fictional.*\n## 1. Scope\n1.1 It applies to all staff.")
    assert [c.id for c in p.clauses] == ["1.1"]


def test_word_documents(examples):
    p = read_policy("acme.docx", (examples / "acme-information-security-policy-2016.docx").read_bytes())
    assert p.title == "Acme Agency Information Security Policy" and len(p.clauses) == 43
    assert (p.clauses[11].id, p.clauses[11].heading) == ("5.1", "Access Control")


def test_csv_and_excel_tables():
    p = read_policy("clauses.csv", "Clause ID;Clause Text;Section\n4.1;Users shall lock screens.;Devices\n4.2;;\n")
    assert [(c.id, c.text, c.heading) for c in p.clauses] == [("4.1", "Users shall lock screens.", "Devices")]
    from codify.xlsx import write_rows

    data = write_rows([["text"], ["Backups shall be taken daily."]])
    assert [(c.id, c.text) for c in read_policy("c.xlsx", data).clauses] == [("row-1", "Backups shall be taken daily.")]


@pytest.mark.parametrize("name, content, message", [
    ("p.docx", b"not a zip", "not a Word"),
    ("p.doc", b"\xd0\xcf\x11\xe0" + b"\0" * 20, "old-style .doc"),
    ("p.csv", "name,value\na,b\n", "clause text column"),
    ("p.txt", "   \n\n", "no clauses found"),
    ("p.docx", "text", "must be read as bytes"),
])
def test_bad_input_says_what_is_wrong(name, content, message):
    with pytest.raises(ValueError, match=message):
        read_policy(name, content)


def test_demo_files_match_the_examples(examples):
    static = examples.parent / "src" / "codify" / "static"
    for ext in ("md", "docx"):
        assert (static / f"acme-policy.{ext}").read_bytes() == \
            (examples / f"acme-information-security-policy-2016.{ext}").read_bytes()
