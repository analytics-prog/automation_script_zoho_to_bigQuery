import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from importlib import import_module

# ====== config ======
RUN_EVERY_MINUTES = 60 # change if you want 30, 15, etc.
ALIGN_TO_HOUR = True  # True = run at :00, :00+1h...  False = run every N minutes from start time
REPO_DIR = os.path.abspath(os.path.dirname(__file__))           # folder containing main.py
LOG_DIR = os.path.join(REPO_DIR, "logs")
LOCKFILE_PATH = os.path.join(REPO_DIR, ".hourly_runner.lock")

# ====== logging ======
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("hourly_runner")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "runner.log"),
    maxBytes=10_000_000, backupCount=5, encoding="utf-8"
)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
handler.setFormatter(fmt)
logger.addHandler(handler)
# also echo to console
console = logging.StreamHandler(sys.stdout)
console.setFormatter(fmt)
logger.addHandler(console)

# ====== single-instance process lock (stdlib only) ======
_lock_fp = None
def acquire_process_lock():
    """
    Prevent running two copies of this runner at the same time.
    Works on Windows (msvcrt) and Linux/Mac (fcntl) using a lock file.
    """
    global _lock_fp
    _lock_fp = open(LOCKFILE_PATH, "w")
    try:
        try:
            import msvcrt  # Windows
            try:
                msvcrt.locking(_lock_fp.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise RuntimeError("another runner instance is already running (Windows lock).")
        except ImportError:
            import fcntl  # POSIX
            try:
                fcntl.flock(_lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise RuntimeError("another runner instance is already running (POSIX lock).")
    except Exception as e:
        logger.error(str(e))
        sys.exit(0)

def release_process_lock():
    global _lock_fp
    if not _lock_fp:
        return
    try:
        try:
            import msvcrt
            msvcrt.locking(_lock_fp.fileno(), msvcrt.LK_UNLCK, 1)
        except ImportError:
            import fcntl
            fcntl.flock(_lock_fp.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        _lock_fp.close()
    except Exception:
        pass
    # keep the lock file on disk; it’s fine

# ====== scheduling helpers ======
def seconds_until_next_tick(now: datetime) -> float:
    """sleep time until next run, aligned to hour or to fixed interval."""
    if not ALIGN_TO_HOUR:
        return RUN_EVERY_MINUTES * 60.0
    # align to :00, :00+N, :00+2N ...
    slot = (now.minute // RUN_EVERY_MINUTES + 1) * RUN_EVERY_MINUTES
    add_hours, next_minute = divmod(slot, 60)
    next_time = now.replace(second=0, microsecond=0)
    next_time = next_time.replace(minute=0) + timedelta(hours=add_hours, minutes=next_minute)
    return max(1.0, (next_time - now).total_seconds())

def run_pipeline_once() -> bool:
    """
    Import and run your repo's main() one time.
    main.py should orchestrate Zoho Deals, Zoho Leads, Stripe.
    Returns True on success, False on exception.
    """
    t0 = time.time()
    try:
        sys.path.insert(0, REPO_DIR)  # ensure local imports
        mod = import_module("main")
        fn = getattr(mod, "main")
        logger.info("===== RUN START =====")
        fn()
        dt = time.time() - t0
        logger.info(f"✅ RUN OK in {dt:.1f}s")
        return True
    except SystemExit as e:
        # allow your main() to signal non-zero exit (we still keep the loop alive)
        logger.exception(f"❌ RUN failed with exit {e.code}")
        return False
    except Exception:
        logger.exception("❌ RUN crashed with exception")
        return False
    finally:
        # remove our injected path to be clean between runs
        try:
            sys.path.remove(REPO_DIR)
        except ValueError:
            pass

def main_loop():
    acquire_process_lock()
    try:
        # initial wait: if aligning, sleep to the next boundary; otherwise run immediately
        if ALIGN_TO_HOUR:
            now = datetime.now(timezone.utc).astimezone()
            sleep_s = seconds_until_next_tick(now)
            logger.info(f"aligning to schedule; sleeping {sleep_s:.0f}s until next tick")
            time.sleep(sleep_s)

        while True:
            start = datetime.now(timezone.utc).astimezone()
            ok = run_pipeline_once()

            # compute next sleep
            # if run took longer than interval, run ASAP (1s)
            elapsed = (datetime.now(timezone.utc).astimezone() - start).total_seconds()
            interval = RUN_EVERY_MINUTES * 60.0
            if ALIGN_TO_HOUR:
                # recalc from current time to the next aligned tick
                sleep_s = seconds_until_next_tick(datetime.now(timezone.utc).astimezone())
            else:
                sleep_s = max(1.0, interval - elapsed)

            if not ok:
                logger.info(f"next run in {sleep_s:.0f}s (previous run failed)")

            time.sleep(sleep_s)
    except KeyboardInterrupt:
        logger.info("shutting down (Ctrl+C).")
    finally:
        release_process_lock()

if __name__ == "__main__":
    main_loop()
