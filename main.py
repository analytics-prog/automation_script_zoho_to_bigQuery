# main.py
import os
import time
import logging
from importlib import import_module

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Toggle any pipeline via env (1=run, 0=skip)
RUN_ZOHO_DEALS = os.getenv("RUN_ZOHO_DEALS", "1") == "1"
RUN_ZOHO_LEADS = os.getenv("RUN_ZOHO_LEADS", "1") == "1"
RUN_STRIPE     = os.getenv("RUN_STRIPE", "1") == "1"
RUN_KLAVIYO    = os.getenv("RUN_KLAVIYO", "1") == "1"

TASKS = [
    ("Zoho → Deals", "fetch_zoho_deals_to_bq", "main", RUN_ZOHO_DEALS),
    ("Zoho → Leads", "fetch_zoho_leads_to_bq", "main", RUN_ZOHO_LEADS),
    ("Stripe → BigQuery (multi)", "fetch_stripe_to_bq_multi", "main", RUN_STRIPE),
    ("Klaviyo → BigQuery", "fetch_klaviyo_to_bq", "main", RUN_KLAVIYO),
]

def run_task(label: str, module_name: str, func_name: str = "main") -> bool:
    logging.info(f"===== START {label} =====")
    t0 = time.time()
    try:
        mod = import_module(module_name)
        fn = getattr(mod, func_name)
        fn()
        logging.info(f"✅ {label} completed in {time.time() - t0:.1f}s")
        return True
    except SystemExit as e:
        logging.exception(f"❌ {label} failed (exit {e.code}) after {time.time() - t0:.1f}s")
        return False
    except Exception as e:
        logging.exception(f"❌ {label} crashed after {time.time() - t0:.1f}s: {e}")
        return False

def main():
    logging.info("Mode: RAW tables append snapshots; FINAL tables MERGE by key (update existing, insert new).")
    overall_ok = True
    for label, module_name, func_name, enabled in TASKS:
        if not enabled:
            logging.info(f"⏭️ Skipping {label}")
            continue
        ok = run_task(label, module_name, func_name)
        overall_ok = overall_ok and ok
    if not overall_ok:
        raise SystemExit(1)

if __name__ == "__main__":
    INTERVAL = 3 * 60 * 60       # 3 hours = 10800s
    REFRESH  = 5 * 60            # log refresh = 5 minutes = 300s

    while True:
        main()
        logging.info(f"⏳ Sleeping for {INTERVAL//3600} hours before next run...")

        remaining = INTERVAL
        while remaining > 0:
            mins_left = remaining // 60
            hrs = mins_left // 60
            mins = mins_left % 60
            logging.info(f"➡️ Next run in {hrs}h {mins}m...")
            time.sleep(min(REFRESH, remaining))
            remaining -= REFRESH
