"""
调度模块 — 基于 APScheduler 的定时任务
"""
import logging

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler(config: dict):
    """
    启动后台调度器。
    默认每天 11:00 (北京时间) 执行一次管线。
    """
    global _scheduler

    sched_cfg = config.get("scheduler", {})
    hour = sched_cfg.get("hour", 11)
    minute = sched_cfg.get("minute", 0)
    tz_str = sched_cfg.get("timezone", "Asia/Shanghai")
    tz = pytz.timezone(tz_str)

    _scheduler = BackgroundScheduler(timezone=tz)

    from src.pipeline import run_pipeline

    def job():
        logger.info("定时任务触发")
        run_pipeline(config)

    trigger = CronTrigger(
        hour=hour, minute=minute, timezone=tz
    )
    _scheduler.add_job(
        job, trigger, id="aiagent_daily", replace_existing=True
    )

    logger.info(
        "调度器已启动: 每天 %02d:%02d (%s)",
        hour, minute, tz_str,
    )
    logger.info("等待定时触发... (按 Ctrl+C 停止)")

    _scheduler.start()

    try:
        from time import sleep
        while True:
            sleep(60)
    except KeyboardInterrupt:
        logger.info("收到中断信号，停止调度器")
        _scheduler.shutdown(wait=False)


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("调度器已停止")
