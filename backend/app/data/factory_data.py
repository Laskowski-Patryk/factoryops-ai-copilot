from datetime import date, timedelta
from random import Random

from app.models.schemas import DowntimeEvent, KpiSnapshot

LINES = ["Line A", "Line B", "Line C"]

SOP_DOCS = [
    {
        "id": "SOP-QA-014",
        "title": "Sensor Fault Escalation",
        "body": (
            "Repeated photoeye or proximity sensor faults require inspection, cleaning, "
            "bracket alignment, calibration check, and maintenance escalation after the "
            "third stop in one shift."
        ),
    },
    {
        "id": "SOP-MAINT-022",
        "title": "Conveyor Cell Recovery",
        "body": (
            "For recurring conveyor cell downtime, verify sensor cabling, validate PLC "
            "event timestamps, inspect guarding vibration, then run a controlled restart "
            "with QA sign-off."
        ),
    },
    {
        "id": "SOP-OPS-008",
        "title": "Shift Handover Report",
        "body": (
            "Shift reports must include target versus actual output, top loss categories, "
            "open actions, ticket references, and owner commitments for the next shift."
        ),
    },
]


def default_date() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _seed(line: str, day: str) -> int:
    return sum(ord(ch) for ch in f"{line}:{day}:factoryops")


def get_kpis(line: str, day: str) -> KpiSnapshot:
    rng = Random(_seed(line, day))
    target = {"Line A": 5000, "Line B": 4600, "Line C": 4300}.get(line, 4500)
    actual = int(target * rng.uniform(0.91, 1.03))
    downtime = rng.randint(18, 46)
    oee = round(rng.uniform(0.78, 0.89), 3)
    scrap = round(rng.uniform(0.011, 0.026), 3)
    if line == "Line A" and day == default_date():
        actual = 4210
        downtime = 94
        oee = 0.681
        scrap = 0.034
    return KpiSnapshot(
        line=line,
        date=day,
        target_units=target,
        actual_units=actual,
        oee=oee,
        scrap_rate=scrap,
        downtime_minutes=downtime,
    )


def get_downtime(line: str, day: str) -> list[DowntimeEvent]:
    if line == "Line A" and day == default_date():
        return [
            DowntimeEvent(
                line=line,
                date=day,
                start_time="06:42",
                duration_minutes=21,
                category="sensor_fault",
                reason="Repeated photoeye misread at infeed station",
                station="A-INFEED-02",
                evidence="PLC tag PE_A2 toggled 31 times in 4 minutes",
            ),
            DowntimeEvent(
                line=line,
                date=day,
                start_time="10:18",
                duration_minutes=34,
                category="sensor_fault",
                reason="Proximity sensor alignment drift after changeover",
                station="A-CELL-04",
                evidence="Three stops cleared by manual sensor reset",
            ),
            DowntimeEvent(
                line=line,
                date=day,
                start_time="13:57",
                duration_minutes=24,
                category="sensor_fault",
                reason="Intermittent cable signal on conveyor guard sensor",
                station="A-CELL-04",
                evidence="Fault returned within 12 minutes after restart",
            ),
            DowntimeEvent(
                line=line,
                date=day,
                start_time="15:31",
                duration_minutes=15,
                category="minor_stop",
                reason="Starved station after upstream recovery",
                station="A-PACK-01",
                evidence="Buffer ran below 20 percent for final hour",
            ),
        ]
    rng = Random(_seed(line, day) + 7)
    categories = ["changeover", "micro_stop", "material_wait", "quality_hold"]
    return [
        DowntimeEvent(
            line=line,
            date=day,
            start_time=f"{8 + idx * 3:02d}:{rng.randint(0, 59):02d}",
            duration_minutes=rng.randint(6, 18),
            category=categories[idx % len(categories)],
            reason=f"Planned recovery item {idx + 1}",
            station=f"{line[-1]}-CELL-{idx + 1:02d}",
            evidence="Synthetic event generated for portfolio demo",
        )
        for idx in range(2)
    ]


def compare_performance(line: str, day: str, days_back: int = 7) -> dict:
    base = date.fromisoformat(day)
    history = [
        get_kpis(line, (base - timedelta(days=offset)).isoformat())
        for offset in range(1, days_back + 1)
    ]
    current = get_kpis(line, day)
    avg_actual = round(sum(item.actual_units for item in history) / len(history), 1)
    avg_oee = round(sum(item.oee for item in history) / len(history), 3)
    avg_downtime = round(sum(item.downtime_minutes for item in history) / len(history), 1)
    return {
        "days_back": days_back,
        "avg_actual_units": avg_actual,
        "avg_oee": avg_oee,
        "avg_downtime_minutes": avg_downtime,
        "actual_delta_units": round(current.actual_units - avg_actual, 1),
        "oee_delta": round(current.oee - avg_oee, 3),
        "downtime_delta_minutes": round(current.downtime_minutes - avg_downtime, 1),
        "history": [item.model_dump() for item in history],
    }


def search_sops(query: str) -> list[dict[str, str]]:
    terms = {part.lower() for part in query.replace("-", " ").split() if len(part) > 2}
    scored = []
    for doc in SOP_DOCS:
        haystack = f"{doc['title']} {doc['body']}".lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append((score, doc))
    return [doc for _, doc in sorted(scored, reverse=True)[:3]] or SOP_DOCS[:2]
