from cid.dossier_spec import DOSSIER_SPEC_VERSION, SECTIONS, audit_research


def test_dossier_spec_has_twenty_evidence_sections():
    assert DOSSIER_SPEC_VERSION == "institutional-dossier-v2"
    assert len(SECTIONS) == 20
    assert len(set(SECTIONS)) == len(SECTIONS)


def test_audit_requires_text_and_evidence_for_support():
    research = {
        "sections": {
            SECTIONS[0]: {"summary": "Known", "claims": [], "evidence_ids": ["W1"]},
            SECTIONS[1]: {"summary": "Uncited", "claims": [], "evidence_ids": []},
        }
    }
    audit = audit_research(research)
    assert audit["supported_sections"] == [SECTIONS[0]]
    assert audit["partial_sections"] == [SECTIONS[1]]
    assert len(audit["missing_sections"]) == 18
    assert audit["status"] == "PARTIAL"
