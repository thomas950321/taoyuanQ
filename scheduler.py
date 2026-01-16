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

from advanced_rag import fetch_and_process_website

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
    """Background job to fetch content and update Vector Database"""
    logger.info("Starting scheduled scrape job (Advanced RAG)...")
    try:
        fetch_and_process_website()
        logger.info("Advanced RAG index updated successfully.")
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
    
    # Run once immediately on start to ensure RAG data is loaded
    # (Since DocStore is in-memory, we need to populate it on every restart)
    scheduler.add_job(update_cache_job)

if __name__ == "__main__":
    # If run directly, keep alive
    start_scheduler()
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        pass
