from app.data.factory_data import default_date
from app.tools.factory_tools import build_registry, query_factory_db


def test_line_a_yesterday_has_sensor_fault_pattern():
    registry = build_registry()
    kpis, _ = registry.execute("get_production_kpis", line="Line A", day=default_date())
    downtime, _ = registry.execute("get_downtime_events", line="Line A", day=default_date())

    assert kpis.actual_units < kpis.target_units
    assert kpis.downtime_minutes == 94
    assert sum(1 for event in downtime if event.category == "sensor_fault") == 3


def test_query_factory_db_allows_select_only():
    assert query_factory_db("SELECT * FROM production_kpis")


def test_query_factory_db_rejects_writes():
    for sql in ["DROP TABLE runs", "UPDATE kpis SET actual=1", "PRAGMA table_info(runs)"]:
        try:
            query_factory_db(sql)
        except ValueError as exc:
            assert "SELECT" in str(exc)
        else:
            raise AssertionError(f"Expected rejection for {sql}")
