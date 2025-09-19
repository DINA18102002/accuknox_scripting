#!/usr/bin/env python3
"""
app_uptime_monitor.py

Production-ready application uptime monitor using HTTP status codes.
- Detects if the application is 'UP' (functioning correctly) or 'DOWN' (unavailable/not responding)
- Supports multiple URLs
- Efficient logging with rotation
- Handles network errors gracefully

"""

import requests
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import argparse
import os
#-----------------
# Logger setup
#-----------------

def setup_logger(log_file="app_uptime.log"):
    logger = logging.getLogger("AppUptimeMonitor")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Rotating file handler
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        fh.setFormatter(formatter)
        fh.setLevel(logging.INFO)
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.setLevel(logging.INFO)
        logger.addHandler(ch)
    
    return logger

#-----------------
# read URLs from config file
#-----------------

def read_urls_from_config(file_path="config.txt"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file {file_path} not found.")
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return urls

#-----------------
# check application status
#-----------------

def check_app_status(url, timeout=10):
    """
    checks application status by sending an HTTp GET request
    return a tuple: (status, status_code)
    """

    try:
        response = requests.get(url, timeout=timeout)
        code = response.status_code
        if 200 <=code <300:
            return "UP", code
        else:
            return "DOWN", code
    except requests.RequestException:
        return "DOWN", None
    
#-----------------
# monitor function
#-----------------

def monitor(urls, timeout=10, logger=None):
    results =[]
    for url in urls:
        status, code = check_app_status(url, timeout)
        if code:
            logger.info(f"Application {url} is {status} (HTTP {code})")
        else:
            logger.warning(f"Application {url} is {status} (No response)")
        results.append((url, status, code))
    return results

#-----------------
# Main function
#-----------------

def main():
    parser = argparse.ArgumentParser(description="Monitor uptime of applications via HTTP requests")
    parser.add_argument("--config", default="config.txt", help="Path to config file containing URLs (default: config.txt)")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout for HTTP requests in seconds (default: 10)")
    parser.add_argument("--logfile", default="app_uptime.log", help="Log file path (default: app_uptime.log)")
    args = parser.parse_args()

    try:
        urls = read_urls_from_config(args.config)
    except FileNotFoundError as e:
        print(e)
        return
    
    logger = setup_logger(args.logfile)
    logger.info("Starting application uptime check...")
    monitor(urls, timeout=args.timeout, logger=logger)
    logger.info("Application uptime check completed.")

if __name__ == "__main__":
    main()
