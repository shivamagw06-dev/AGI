"""Company / sector / portfolio macro links."""

__all__ = [
    "compile_company_links",
    "compile_sector_links",
    "company_macro_link",
    "portfolio_macro_exposure",
    "sector_macro_link",
]


def __getattr__(name: str):
    if name in {"compile_company_links", "company_macro_link"}:
        from knowledge_factory.macro_intelligence.links.company import (
            compile_company_links,
            company_macro_link,
        )

        return compile_company_links if name == "compile_company_links" else company_macro_link
    if name in {"compile_sector_links", "sector_macro_link"}:
        from knowledge_factory.macro_intelligence.links.sector import compile_sector_links, sector_macro_link

        return compile_sector_links if name == "compile_sector_links" else sector_macro_link
    if name == "portfolio_macro_exposure":
        from knowledge_factory.macro_intelligence.links.portfolio import portfolio_macro_exposure

        return portfolio_macro_exposure
    raise AttributeError(name)
