"""Saved ML results.

Every heavy ML endpoint is calculated once in a background job and saved in ml_result_snapshots.
API requests read the saved copy, so page loads stay fast however big the data is. After each
data import the whole set is recalculated in the background.
"""
import datetime
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.models.models import MLResultSnapshot, ProductForecast
from backend.app.services import jobs

ML_JOB_KIND = "ml_recalculate"


def reset_ml_caches(db: Session) -> None:
    """Drop in-memory and stored per-product caches so engines recompute from current rows."""
    from backend.ml.forecasting import engine as forecasting_engine
    from backend.ml.risk import engine as risk_engine
    from backend.app.services import services, recommendation_engine
    forecasting_engine.FORECAST_CACHE.clear()
    risk_engine.RISK_CACHE.update({"timestamp": 0, "data": []})
    services.SUMMARY_CACHE.update({"timestamp": 0, "data": None})
    recommendation_engine.UNIFIED_REC_CACHE.update({"timestamp": 0, "data": []})
    try:
        db.query(ProductForecast).delete()
        db.commit()
    except Exception:
        db.rollback()


def _sources() -> List[Tuple[str, str, Callable[[Session], Any]]]:
    from backend.app.services.services import SupplyChainService
    from backend.api.routes.insights import compute_home_insights
    from backend.ml.intelligences import snapshot_sources as intelligence_sources

    def svc(db):
        return SupplyChainService(db)

    return [
        ("inventory_risk", "Stockout risk", lambda db: svc(db).risk_engine.get_all_inventory_risks()),
        ("control_tower_summary", "Dashboard KPIs", lambda db: svc(db).get_control_tower_summary()),
        ("recommendations", "Recommendations", lambda db: svc(db).recommendation_engine.get_unified_recommendations()),
        ("module_procurement", "Purchase planning", lambda db: svc(db).procurement_engine.generate_procurement_intelligence()),
        ("module_assortment", "Shelf space", lambda db: svc(db).assortment_engine.generate_assortment_intelligence()),
        ("module_pricing", "Price optimisation", lambda db: svc(db).get_pricing_optimization()),
        ("module_policy", "Restocking rules", lambda db: svc(db).get_policy_simulation()),
        ("module_customer_ltv", "Customer value", lambda db: svc(db).get_customer_ltv()),
        ("module_market_basket", "Bought together", lambda db: svc(db).get_market_basket()),
        ("module_trade_area", "Store catchment", lambda db: svc(db).get_trade_area()),
        ("insights_home", "Home dashboard answers", compute_home_insights),
        *intelligence_sources(),
    ]


def _jsonable(payload: Any) -> Any:
    return json.loads(json.dumps(payload, default=str))


def _save(db: Session, key: str, payload: Any, duration_ms: int) -> MLResultSnapshot:
    snap = db.query(MLResultSnapshot).filter(MLResultSnapshot.key == key).first()
    if not snap:
        snap = MLResultSnapshot(key=key)
        db.add(snap)
    snap.payload = _jsonable(payload)
    snap.computed_at = datetime.datetime.utcnow()
    snap.duration_ms = duration_ms
    db.commit()
    return snap


def get_or_compute(db: Session, key: str) -> Tuple[Any, Optional[datetime.datetime]]:
    """Saved result if there is one; otherwise calculate now (first run / small data) and save it."""
    snap = db.query(MLResultSnapshot).filter(MLResultSnapshot.key == key).first()
    if snap and snap.payload is not None:
        return snap.payload, snap.computed_at
    return recompute(db, key)


def recompute(db: Session, key: str) -> Tuple[Any, Optional[datetime.datetime]]:
    """Calculate one saved result now and store it."""
    fn = dict((k, f) for k, _, f in _sources())[key]
    t0 = time.time()
    payload = fn(db)
    snap = _save(db, key, payload, int((time.time() - t0) * 1000))
    return snap.payload, snap.computed_at


def recalculate_all(ctx: jobs.JobContext) -> Dict[str, Any]:
    db = ctx.db
    reset_ml_caches(db)
    sources = _sources()
    timings = {}
    failed = {}
    ctx.progress(0, len(sources), "Starting ML recalculation")
    for i, (key, label, fn) in enumerate(sources):
        ctx.progress(i, len(sources), f"Calculating: {label}")
        t0 = time.time()
        try:
            payload = fn(db)
            ms = int((time.time() - t0) * 1000)
            _save(db, key, payload, ms)
            timings[key] = ms
        except Exception as e:
            db.rollback()
            failed[key] = str(e)
    ctx.progress(len(sources), len(sources), "Done")
    total_s = round(sum(timings.values()) / 1000, 1)
    return {
        "status": "SUCCESS" if not failed else "ERROR",
        "message": f"Recalculated {len(timings)} of {len(sources)} ML results in {total_s}s"
                   + (f"; failed: {', '.join(failed)}" if failed else ""),
        "timings_ms": timings,
        "failed": failed,
    }


def start_recalculation(db: Session, reason: str = "manual") -> Dict[str, Any]:
    """Queue a full recalculation, unless one is already waiting to start."""
    pending = (db.query(jobs.BackgroundJob)
               .filter(jobs.BackgroundJob.kind == ML_JOB_KIND, jobs.BackgroundJob.status == "QUEUED")
               .order_by(jobs.BackgroundJob.id.desc()).first())
    if pending:
        return jobs.job_to_dict(pending)
    job = jobs.submit(db, ML_JOB_KIND, recalculate_all, params={"reason": reason},
                      message="Waiting to recalculate ML results")
    return jobs.job_to_dict(job)
