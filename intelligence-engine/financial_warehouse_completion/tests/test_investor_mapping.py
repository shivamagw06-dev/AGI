import pytest
from financial_warehouse_completion.investor_mapping import registry,save,seeds

@pytest.fixture
def isolated_db(tmp_path,monkeypatch):
 from institutional_warehouse import db
 monkeypatch.setenv('INSTITUTIONAL_WAREHOUSE_ROOT',str(tmp_path))
 for key in ['WAREHOUSE_DATABASE_URL','INSTITUTIONAL_WAREHOUSE_DATABASE_URL']:monkeypatch.delenv(key,raising=False)
 monkeypatch.setattr(db,'_BACKEND',None);monkeypatch.setattr(db,'_INITIALISED',False)
 yield db
 if db._BACKEND:db._BACKEND.close()

def test_seed_revocation_persists_without_changing_other_mappings(isolated_db):
 original=registry();seed=seeds()[0]
 result=save({**seed,'status':'revoked'},'test-admin')
 assert result['ok']
 current=registry();assert len(current['mappings'])==len(original['mappings'])
 changed=next(m for m in current['mappings'] if m['id']==seed['id'])
 assert changed['status']=='revoked' and changed['reviewedBy']=='test-admin'
 assert len(isolated_db.query('SELECT * FROM wh_investor_entity_mappings'))==1

def test_invalid_review_cannot_overwrite(isolated_db):
 seed=seeds()[0]
 for field,value in [('profileId','in-unknown'),('bucket','wealth'),('validFrom','bad'),('evidenceUrl','javascript:bad'),('evidenceNote','')]:
  with pytest.raises(ValueError):save({**seed,field:value},'test-admin')
 assert not isolated_db.query('SELECT * FROM wh_investor_entity_mappings')
