from ask_pipeline.dag import execute_research_dag


def test_dag_exposes_governed_tool_plan_without_claiming_execution():
    result = execute_research_dag(
        policy={"run_dag": True},
        planner={
            "status": "executed",
            "tool_plan": {
                "registry_version": "agi-tools-v1",
                "tools": [{"name": "SEARCH_RESEARCH"}, {"name": "GET_THESIS"}],
                "budgets": {"max_searches": 5, "max_documents": 20, "max_runtime_seconds": 30},
            },
        },
        knowledge={"status": "executed"},
        evidence={"status": "executed", "coverage": 1, "packs_found": 1},
    )
    task = next(item for item in result["tasks"] if item["task_id"] == "governed_tool_plan")
    assert task["status"] == "planned"
    assert task["tools"] == ["SEARCH_RESEARCH", "GET_THESIS"]
    assert task["controlled_writes_allowed"] is False
    assert task["execution_mode"] == "explicit_bindings_only"
    assert ["governed_tool_plan"] in result["levels"]
