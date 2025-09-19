#!/usr/bin/env python3
"""
system_health_monitor.py

Continuous Linux system health monitor:
  - CPU (system)
  - memory
  - Disk (for given paths)
  - Running processes (count + high-CPU processes )

Improvements over original:
    - Uses psutil's cpu_percent / Process.cpu_percent correctly(two-sample method)
    - Robust exception handling (NoSuchProcess / AccessDenied / ZombieProcess)
    - Rotating file logger (prevents huge logs)
    - Configurable sampling interval for process CPU measurement
    - CLear, formatted logging and exit behavior (non-blocking)
"""

import argparse
import logging
import time
from logging.handlers import RotatingFileHandler

import psutil

#-------------------------------
# Loggining setup (rotating)
#-------------------------------

def setup_logging(log_file, level=logging.INFO,max_bytes= 5 * 1024 * 1024, backup_count=3):
    logger = logging.getLogger("sysmon_v1")
    logger.setLevel(level)

    if not logger.handlers:
        fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


#-------------------------------
# Checks
#-------------------------------

def check_cpu_usage(threshold, sample_interval, logger):
    """
    Uses psutil.cpu_percent with a sampling interval to get a realistic reading.
    """

    try:
        cpu_percent = psutil.cpu_percent(interval=sample_interval)
    except Exception as e:
        logger.error(f"Failed to read CPU percent: {e}")
        return None, False
    
    if cpu_percent > threshold:
        logger.warning(f"High CPU usage: {cpu_percent:.1f}% (Threshold: {threshold}%)")
        return cpu_percent, True
    else:
        logger.info(f"CPU usage: {cpu_percent:.1f}%")
        return cpu_percent, False
    
def check_memory_usage(threshold, logger):
    try:
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
    except Exception as e:
        logger.error(f"Failed to read  memory usage: {e}")
        return None, False
    
    if mem_percent > threshold:
        logger.warning(f"High memory usage: {mem_percent:.1f}% (Threshold: {threshold}%)")
        return mem_percent, True
    else:
        logger.info(f"Memory usage: {mem_percent:.1f}%")
        return mem_percent, False
    
def check_disk_usage(paths, threshold, logger):
    alerts=[]
    for path in paths:
        try:
            du = psutil.disk_usage(path)
            pct = du.percent
            if pct > threshold:
                logger.warning(f"High disk usage on {path}: {pct:.1f}% (Threshold: {threshold}%)")
                alerts.append((path, pct))
            else:
                logger.info(f"Disk usage on {path}: {pct:.1f}%")
        except Exception as e:
            logger.info(f"Error checking disk {path}: {e}")
    return alerts

def check_running_processes(process_cpu_threshold, process_count_threshold,sample_interval, logger):
    """
    Finds processess whose CPU% over sample interval exceeds process_cpu_threshold.
    Process.cpu_percent works by returning percentage since last call, so:
       - call cpu_percent(None) for each process to initialize
       - sleep sample_interval
       - call cpu-percent(None) again to get usage over sample_interval
    This method is non-blocking and relaible
    """

    alerts=[]
    try:
        process_count = len(psutil.pids())
    except Exception as e:
        logger.error(f"Failed to get process count: {e}")
        process_count = None

    if process_count is not None:
        if process_count > process_count_threshold:
            logger.warning(f"High number of processes: {process_count} (Threshold: {process_count_threshold})")
            alerts.append(("Process Count", process_count))
        else:
            logger.info(f"Total processes: {process_count}")

            
    # First pass: initialize cpu_percent counters (non-blocking)

    procs={}
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            pid = proc.info["pid"]
            name = proc.info.get("name") or ""

            # initialize measurement
            try:
                proc.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            procs[pid]=name
        except(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sleep short interval to sample per-process CPU usage
    time.sleep(sample_interval)

    high_cpu_processes=[]
    for pid, name in procs.items():
        try:
            p= psutil.Process(pid)
            cpu_pct = p.cpu_percent(None)  # percent since the last call
            mem_pct = p.memory_percent()
            if cpu_pct is None:
                continue
            if cpu_pct > process_cpu_threshold:
                high_cpu_processes.append({"pid": pid, "name": name, "cpu": cpu_pct, "mem": mem_pct})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue    
        except Exception as e:
            logger.debug(f"process check error for pid={pid}: {e}")
            continue


    if high_cpu_processes:
        logger.warning("High CPU processess detected:")
        for p in sorted(high_cpu_processes, key=lambda x: x["cpu_percent"], reverse=True):
            logger.warning(f" -PID: {p['pid']}, Name: {p['name']}, CPU%: {p['cpu']:.1f}%, MEM: {p['mem_percent']:.1f}%")
    else:
        logger.info("No high CPU processed detected")
    return process_count, high_cpu_processes, alerts

#-------------------------------
# Main loop
#-------------------------------

def main():
    parser = argparse.ArgumentParser(description="Linux System Health Monitor (v1)")
    parser.add_argument("--interval", type=int, default=60, help="Main monitoring interval in seconds (default 60)")
    parser.add_argument("--sample-interval", type=float, default=0.5, help="Sampling interval for process CPU measurement (seconds, default 0.5)")
    parser.add_argument("--cpu-threshold", type=float, default=80.0, help="CPU usage threshold percent (default 80)")
    parser.add_argument("--memory-threshold", type=float, default=80.0, help="Memory usage threshold percent (default 80)")
    parser.add_argument("--disk-threshold", type=float, default=90.0, help="Disk usage threshold percent (default 90)")
    parser.add_argument("--process-cpu-threshold", type=float, default=20.0, help="Per-process CPU threshold percent (default 20)")
    parser.add_argument("--process-count-threshold", type=int, default=500, help="Total process count threshold (default 500)")
    parser.add_argument("--disk-paths", type=str, default="/", help="Comma-separated disk paths to monitor (default '/')")
    parser.add_argument("--log-file", type=str, default="system_health_v1.log", help="Log file path")
    args = parser.parse_args()

    logger = setup_logging(args.log_file)
    disk_paths = [p.strip() for p in args.disk_paths.split(",") if p.strip()]

    logger.info("Starting system health monitor (v1). press Ctrl+c to stop.")
    try:
        while True:
            cycle_alerts =False
            logger.info("-----New health check cycle-----")

            _, cpu_alert = check_cpu_usage(args.cpu_threshold, args.sample_interval, logger)
            _, mem_alert = check_memory_usage(args.memory_threshold, logger)
            disk_alerts = check_disk_usage(disk_paths, args.disk_threshold, logger)
            _, high_cpu_procs, proc_alerts = check_running_processes(
                args.process_cpu_threshold, args.process_count_threshold, args.sample_interval, logger
            )

            if cpu_alert or mem_alert or disk_alerts or high_cpu_procs or proc_alerts:
                cycle_alerts = True

            if cycle_alerts:
                logger.warning("One or more alerts raised this cycle.")
            else:
                logger.info("All checks OK this cycle.")

            logger.info("---- Cycle completed ----\n")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user.")
    except Exception as e:
        logger.exception(f"Unhandled exception in monitor: {e}")


if __name__ == "__main__":
    main()