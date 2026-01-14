import time
import os
import sys
import logging
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import redis

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import fetch_taoyuanq_content

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Redis Connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

def get_redis_client():
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        # Keep silent/warn only if critical
        return None

def update_cache_job():
    """Background job to fetch content and update Redis"""
    logger.info("Starting scheduled scrape job...")
    try:
        content = fetch_taoyuanq_content()
        if content:
            r = get_redis_client()
            if r:
                try:
                    # Save as JSON string
                    json_content = json.dumps(content)
                    r.set("taoyuanq_pages", json_content)
                    r.set("last_update", time.time())
                    # Cleanup old key
                    r.delete("taoyuanq_content")
                    logger.info(f"Cache updated successfully. Pages: {len(content)}")
                except Exception:
                    pass
            else:
                logger.warning("Redis not available. Scraped content not saved.")
        else:
            logger.warning("Scraper returned empty content.")
    except Exception as e:
        logger.error(f"Job failed: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule 'update_cache_job' to run every 30 minutes
    scheduler.add_job(
        update_cache_job,
        trigger=IntervalTrigger(minutes=30),
        id='scraper_job',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started. Job will run every 30 minutes.")
    
    # Run once immediately on start if cache is empty
    r = get_redis_client()
    if r:
        try:
            if not r.get("taoyuanq_pages"):
                 logger.info("Cache empty, running immediate initial scrape...")
                 scheduler.add_job(update_cache_job)
        except Exception:
            pass

if __name__ == "__main__":
    # If run directly, keep alive
    start_scheduler()
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        pass
