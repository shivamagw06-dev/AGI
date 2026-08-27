from knowledge_factory.industry_intelligence.playbooks.catalog import get_playbook


def valuation_for(industry_id: str):
    pb = get_playbook(industry_id) or {}
    return pb.get("valuation") or {}
