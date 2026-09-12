"""Knowledge Retrieval & Intelligence Gateway (Sprint 6.4)."""

# Keep package import light to avoid circular imports with KFE/KCE.
__all__ = ["KnowledgeRetrievalGateway", "KnowledgeBundle"]


def __getattr__(name: str):
    if name == "KnowledgeRetrievalGateway":
        from app.krig.gateway import KnowledgeRetrievalGateway

        return KnowledgeRetrievalGateway
    if name == "KnowledgeBundle":
        from app.krig.bundle import KnowledgeBundle

        return KnowledgeBundle
    raise AttributeError(name)
