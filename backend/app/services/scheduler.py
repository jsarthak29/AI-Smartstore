import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import AsyncSessionLocal
from app.services.automation import expiry, low_stock, weekly_summary

log = logging.getLogger(__name__)

_JOBS = {
    low_stock.JOB_NAME: (low_stock.run, CronTrigger(hour=8, minute=0)),
    weekly_summary.JOB_NAME: (weekly_summary.run, CronTrigger(day_of_week="mon", hour=9, minute=0)),
    expiry.JOB_NAME: (expiry.run, CronTrigger(hour=7, minute=0)),
}


async def _wrapped(fn):
    async with AsyncSessionLocal() as db:
        try:
            await fn(db)
        except Exception:
            log.exception("scheduled job %s crashed", fn.__module__)


def build_scheduler() -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="UTC")
    for name, (fn, trig) in _JOBS.items():
        sched.add_job(_wrapped, trigger=trig, args=[fn], id=name, replace_existing=True)
        log.info("registered job %s", name)
    return sched


async def run_job_now(name: str) -> None:
    if name not in _JOBS:
        raise ValueError(f"unknown job {name}")
    fn, _ = _JOBS[name]
    await _wrapped(fn)
