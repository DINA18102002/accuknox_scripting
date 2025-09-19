# 🖥️ System & Application Monitoring Exercises

This repository contains **two Python scripts** for monitoring system health and application uptime on Linux. Both scripts are production-ready, configurable, and use rotating logs to prevent disk overuse.



## Exercise 1: 🖥️ System Health Monitor

**Script:** `system_health_monitor.py`  

### Features
- CPU, Memory, Disk usage monitoring
- Process count & high CPU processes detection
- Configurable thresholds & intervals
- Rotating logs (max 5MB, 3 backups)
- Robust error handling

### Prerequisites
```bash
python3 --version
pip install psutil


How to Run
cd exercise1
python3 system_health_monitor.py


Optional customization:
python3 system_health_monitor.py --interval 30 --cpu-threshold 70 --disk-paths /,/home --log-file system_health_custom.log

Check logs:
tail -f system_health_v1.log
```

## Exercise 2: 🌐 Application Uptime Monitor

Script: app_uptime_monitor.py

Features
Monitors URLs from config.txt
Detects UP (HTTP 2xx) / DOWN (non-2xx or no response)
Configurable timeout & logging
Rotating logs (max 5MB, 3 backups)
Graceful error handling

```
Prerequisites
pip install requests

How to Run
cd exercise2
python3 app_uptime_monitor.py


Optional customization:
python3 app_uptime_monitor.py --config custom_urls.txt --timeout 5 --logfile app_custom.log


Check logs:
tail -f app_uptime.log

⚡ Tips & Notes
Stop scripts with Ctrl+C.
Logs automatically rotate to prevent disk overuse.
Use a virtual environment (venv) to manage dependencies.
Test high CPU/memory or invalid URLs to trigger warnings.

Optional: Run continuously using screen or systemd.

Example Logs
System Health:
INFO - CPU usage: 5.0%
INFO - Memory usage: 45.2%
WARNING - High CPU usage: 85.1% (Threshold: 80%)


Application Uptime:

INFO - Application https://example.com is UP (HTTP 200)
WARNING - Application http://nonexistent.local is DOWN (No response)
```
