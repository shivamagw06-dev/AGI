"""Management / director graph."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

PEOPLE_NODES = [
    n("person_sashidhar_jagdishan", "Sashidhar Jagdishan", "person", role="ceo"),
    n("person_n_chandrasekaran", "N. Chandrasekaran", "person", role="chairman"),
    n("person_salil_parekh", "Salil Parekh", "person", role="ceo"),
    n("person_suresh_narayanan", "Suresh Narayanan", "person", role="chairman"),
]

PEOPLE_EDGES = [
    e("person_sashidhar_jagdishan", "HDFCBANK", "ceo_of", strength=0.95, confidence=0.97,
      note="CEO of HDFC Bank", evidence_kind="management_disclosure"),
    e("person_n_chandrasekaran", "TCS", "board_of", strength=0.9, confidence=0.95,
      note="Chairman linkage across Tata group companies"),
    e("person_n_chandrasekaran", "TATASTEEL", "board_of", strength=0.7, confidence=0.88),
    e("person_n_chandrasekaran", "TATAMOTORS", "board_of", strength=0.7, confidence=0.88),
    e("person_salil_parekh", "INFY", "ceo_of", strength=0.95, confidence=0.97),
    e("person_suresh_narayanan", "NESTLEIND", "board_of", strength=0.85, confidence=0.92),
    e("TCS", "TATASTEEL", "shares_director", strength=0.65, confidence=0.86,
      note="Tata group board interlock via common leadership network"),
    e("TCS", "TATAMOTORS", "shares_director", strength=0.65, confidence=0.86),
]
