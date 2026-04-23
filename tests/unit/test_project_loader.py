from __future__ import annotations

from papertrail.projects.loader import ProjectLoader


def test_project_loader_reads_indian_financial_project() -> None:
    loader = ProjectLoader()
    project = loader.load("indian_financial")

    assert project.slug == "indian_financial"
    assert project.name == "Indian Financial Documents"
    assert project.classification_labels() == {
        "indian_cheque",
        "indian_bank_statement",
        "indian_salary_slip",
        "indian_itr_form",
    }
    assert project.engine_defaults.ocr == "paddleocr"
    assert project.shared_tools == ["ifsc_lookup"]
