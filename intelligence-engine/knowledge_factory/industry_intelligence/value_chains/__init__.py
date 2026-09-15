from knowledge_factory.industry_intelligence.playbooks.catalog import get_playbook


def value_chain_for(industry_id: str):
    pb = get_playbook(industry_id) or {}
    return pb.get("value_chain") or []
