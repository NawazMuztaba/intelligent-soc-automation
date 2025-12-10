#!/usr/bin/env python3
"""
Hybrid Log Adapter - multi-threaded tailer that publishes log lines to Redis `raw_logs`.

Usage examples:
  # single run for specific files:
  python adapters/log_adapter.py --watch /tmp/test_auth.log:auth --watch /tmp/test_web.log:web

  # from controller or background:
  nohup python adapters/log_adapter.py --watch /var/log/auth.log:auth --watch /var/log/nginx/access.log:web > logs/adapter.log 2>&1 &

Behavior:
 - Each --watch takes argument PATH:SOURCE_LABEL
 - Adapter is rotation-safe: it reopens file when inode changes
 - Publishes JSON to Redis channel 'raw_logs'
 - Prints colorized console output and writes minimal health to stdout
"""

import argparse
import threading
import time
import os
import json
import redis
import sys
from datetime import datetime

# CONFIG
REDIS_URL = "redis://localhost:6379/0"
POLL_INTERVAL = 0.2           # how often to check for new lines (seconds)
HEALTH_INTERVAL = 60         # how often to print health (seconds)

# ANSI colors
CLR_RESET = "\033[0m"
CLR_CYAN = "\033[0;36m"
CLR_GREEN = "\033[0;32m"
CLR_YELLOW = "\033[0;33m"
CLR_RED = "\033[0;31m"
CLR_MAGENTA = "\033[0;35m"

r = redis.Redis.from_url(REDIS_URL)

class TailWorker(threading.Thread):
    def __init__(self, path, source, stats):
        super().__init__(daemon=True)
        self.path = path
        self.source = source
        self.stats = stats  # shared dict for counts
        self._stopped = threading.Event()

    def stop(self):
        self._stopped.set()

    def open_file(self):
        try:
            f = open(self.path, "r", errors="ignore")
            inode = os.fstat(f.fileno()).st_ino
            # go to file end
            f.seek(0, os.SEEK_END)
            return f, inode
        except Exception as e:
            return None, None

    def run(self):
        last_inode = None
        f = None
        while not self._stopped.is_set():
            if f is None:
                f, last_inode = self.open_file()
                if f is None:
                    print(f"{CLR_YELLOW}[ADAPTER][{self.source}] waiting for file: {self.path}{CLR_RESET}")
                    time.sleep(2.0)
                    continue
                else:
                    print(f"{CLR_GREEN}[ADAPTER][{self.source}] opened {self.path}{CLR_RESET}")

            line = f.readline()
            if not line:
                # check rotation by inode
                try:
                    cur_inode = os.stat(self.path).st_ino
                    if cur_inode != last_inode:
                        # file rotated: reopen
                        print(f"{CLR_MAGENTA}[ADAPTER][{self.source}] rotation detected; reopening{CLR_RESET}")
                        try:
                            f.close()
                        except:
                            pass
                        f, last_inode = self.open_file()
                        continue
                except FileNotFoundError:
                    # file disappeared (rotated or removed)
                    try:
                        f.close()
                    except:
                        pass
                    f = None
                    time.sleep(1.0)
                    continue
                time.sleep(POLL_INTERVAL)
                continue

            line = line.rstrip("\n")
            payload = {
                "source": self.source,
                "line": line,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "file": self.path
            }
            try:
                r.publish("raw_logs", json.dumps(payload))
                self.stats_increment()
                print(f"{CLR_CYAN}[{self.source}] PUBLISHED → {line[:150]}{CLR_RESET}")
            except Exception as e:
                print(f"{CLR_RED}[ADAPTER][{self.source}] Redis publish error: {e}{CLR_RESET}")
                time.sleep(1.0)

    def stats_increment(self):
        with self.stats["lock"]:
            self.stats["count"] += 1
            self.stats["per_source"].setdefault(self.source, 0)
            self.stats["per_source"][self.source] += 1

def health_thread(stats, workers):
    last_print = time.time()
    while True:
        time.sleep(1.0)
        if time.time() - last_print >= HEALTH_INTERVAL:
            with stats["lock"]:
                total = stats.get("count", 0)
                per = stats.get("per_source", {})
            stamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"{CLR_YELLOW}[HEALTH] {stamp} total_published={total} sources={list(per.keys())}{CLR_RESET}")
            for s, c in per.items():
                print(f"   - {s}: {c}")
            # also print worker status
            for w in workers:
                print(f"   * worker: {w.source} (path={w.path}) alive={w.is_alive()}")
            last_print = time.time()

def parse_args():
    p = argparse.ArgumentParser(description="Hybrid multi-threaded log adapter -> Redis raw_logs")
    p.add_argument("--watch", "-w", action="append", help="Add watch in format /path/to/file:label (can repeat)", required=True)
    p.add_argument("--health", type=int, default=HEALTH_INTERVAL, help="Health interval seconds")
    p.add_argument("--redis", type=str, default=REDIS_URL, help="Redis URL")
    return p.parse_args()

def main():
    args = parse_args()
    global r, HEALTH_INTERVAL
    r = redis.Redis.from_url(args.redis)
    HEALTH_INTERVAL = args.health

    watches = []
    for w in args.watch:
        if ":" not in w:
            print(f"{CLR_RED}Invalid --watch value (must be path:label): {w}{CLR_RESET}")
            sys.exit(1)
        path, label = w.split(":", 1)
        watches.append((path, label))

    print(f"{CLR_GREEN}Starting Hybrid Log Adapter{CLR_RESET}")
    print(f"  watches: {watches}")
    stats = {"count": 0, "per_source": {}, "lock": threading.Lock()}

    workers = []
    for path, label in watches:
        tw = TailWorker(path, label, stats)
        tw.start()
        workers.append(tw)

    # start health thread
    ht = threading.Thread(target=health_thread, args=(stats, workers), daemon=True)
    ht.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"{CLR_YELLOW}\nShutting down adapter...{CLR_RESET}")
        for w in workers:
            w.stop()
        # allow threads to finish
        time.sleep(1.0)

if __name__ == "__main__":
    main()
