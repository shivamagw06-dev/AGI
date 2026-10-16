"""Keep simulated provider failures isolated between test cases."""
import pytest


@pytest.fixture(autouse=True)
def isolated_market_data_allowance(tmp_path, monkeypatch):
    # Production intentionally shares cooldowns across workers. A mocked 429 in
    # one test must not poison the following test or touch a developer's store.
    monkeypatch.setenv('MARKET_DATA_BUDGET_DB', str(tmp_path / 'market-budget.sqlite3'))
