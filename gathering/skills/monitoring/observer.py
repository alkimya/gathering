"""
Monitoring Skill for GatheRing.
Provides metrics collection, log analysis, and health monitoring.
"""

import os
import re
import json
import time
import logging
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self._metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}

    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        self._metrics[name].append({
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or {}
        })
        # Keep only last 1000 entries per metric
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-1000:]

    def increment(self, name: str, value: float = 1.0):
        """Increment a counter."""
        self._counters[name] += value

    def gauge(self, name: str, value: float):
        """Set a gauge value."""
        self._gauges[name] = value

    def get_metrics(self, name: str, since_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metrics for a name."""
        cutoff = datetime.now() - timedelta(minutes=since_minutes)
        return [
            m for m in self._metrics.get(name, [])
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]

    def get_counter(self, name: str) -> float:
        """Get counter value."""
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value."""
        return self._gauges.get(name)

    def list_metrics(self) -> Dict[str, int]:
        """List all metric names and counts."""
        return {name: len(values) for name, values in self._metrics.items()}

    def clear(self, name: Optional[str] = None):
        """Clear metrics."""
        if name:
            self._metrics.pop(name, None)
            self._counters.pop(name, None)
            self._gauges.pop(name, None)
        else:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()


class MonitoringSkill(BaseSkill):
    """
    Skill for system monitoring and observability.

    Features:
    - System metrics (CPU, memory, disk, network)
    - Log file analysis
    - Custom metrics collection
    - Health checks
    - Alerting thresholds

    Security:
    - Read-only system access
    - Configurable log paths
    """

    name = "monitoring"
    description = "System monitoring, metrics, and log analysis"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._collector = MetricsCollector()
        self._allowed_log_paths = self.config.get("allowed_log_paths", []) if self.config else []
        self._alerts: List[Dict[str, Any]] = []

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "monitor_system",
                "description": "Get current system metrics (CPU, memory, disk, network)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_processes": {
                            "type": "boolean",
                            "description": "Include top processes",
                            "default": False
                        },
                        "process_count": {
                            "type": "integer",
                            "description": "Number of top processes to include",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "monitor_process",
                "description": "Monitor a specific process",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pid": {
                            "type": "integer",
                            "description": "Process ID"
                        },
                        "name": {
                            "type": "string",
                            "description": "Process name to search for"
                        }
                    }
                }
            },
            {
                "name": "monitor_logs",
                "description": "Analyze log files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Log file path"
                        },
                        "lines": {
                            "type": "integer",
                            "description": "Number of lines to read",
                            "default": 100
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Filter pattern (regex)"
                        },
                        "level": {
                            "type": "string",
                            "description": "Filter by log level",
                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                        },
                        "since": {
                            "type": "string",
                            "description": "Filter logs since (ISO format or relative like '1h', '30m')"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "monitor_log_stats",
                "description": "Get statistics from log file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Log file path"
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Analyze last N hours",
                            "default": 24
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "monitor_record",
                "description": "Record a custom metric",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Metric name"
                        },
                        "value": {
                            "type": "number",
                            "description": "Metric value"
                        },
                        "type": {
                            "type": "string",
                            "description": "Metric type",
                            "enum": ["gauge", "counter", "histogram"],
                            "default": "gauge"
                        },
                        "tags": {
                            "type": "object",
                            "description": "Optional tags"
                        }
                    },
                    "required": ["name", "value"]
                }
            },
            {
                "name": "monitor_get_metrics",
                "description": "Get recorded custom metrics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Metric name (empty for all)"
                        },
                        "since_minutes": {
                            "type": "integer",
                            "description": "Get metrics from last N minutes",
                            "default": 60
                        }
                    }
                }
            },
            {
                "name": "monitor_health_check",
                "description": "Run health checks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "checks": {
                            "type": "array",
                            "description": "List of health checks to run",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {
                                        "type": "string",
                                        "enum": ["http", "tcp", "process", "disk", "memory"]
                                    },
                                    "target": {"type": "string"},
                                    "threshold": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "monitor_set_alert",
                "description": "Set up an alert threshold",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Alert name"
                        },
                        "metric": {
                            "type": "string",
                            "description": "Metric to monitor",
                            "enum": ["cpu", "memory", "disk", "custom"]
                        },
                        "custom_metric": {
                            "type": "string",
                            "description": "Custom metric name (if metric=custom)"
                        },
                        "operator": {
                            "type": "string",
                            "description": "Comparison operator",
                            "enum": [">", "<", ">=", "<=", "=="]
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Threshold value"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "Enable/disable alert",
                            "default": True
                        }
                    },
                    "required": ["name", "metric", "operator", "threshold"]
                }
            },
            {
                "name": "monitor_check_alerts",
                "description": "Check all configured alerts",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "monitor_disk",
                "description": "Get detailed disk usage",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to check",
                            "default": "/"
                        },
                        "include_inodes": {
                            "type": "boolean",
                            "description": "Include inode usage",
                            "default": False
                        }
                    }
                }
            },
            {
                "name": "monitor_network",
                "description": "Get network statistics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "interface": {
                            "type": "string",
                            "description": "Network interface (empty for all)"
                        },
                        "include_connections": {
                            "type": "boolean",
                            "description": "Include active connections",
                            "default": False
                        }
                    }
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute monitoring tool."""
        try:
            if tool_name == "monitor_system":
                return self._system_metrics(tool_input)
            elif tool_name == "monitor_process":
                return self._process_metrics(tool_input)
            elif tool_name == "monitor_logs":
                return self._analyze_logs(tool_input)
            elif tool_name == "monitor_log_stats":
                return self._log_stats(tool_input)
            elif tool_name == "monitor_record":
                return self._record_metric(tool_input)
            elif tool_name == "monitor_get_metrics":
                return self._get_metrics(tool_input)
            elif tool_name == "monitor_health_check":
                return self._health_check(tool_input)
            elif tool_name == "monitor_set_alert":
                return self._set_alert(tool_input)
            elif tool_name == "monitor_check_alerts":
                return self._check_alerts()
            elif tool_name == "monitor_disk":
                return self._disk_usage(tool_input)
            elif tool_name == "monitor_network":
                return self._network_stats(tool_input)
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool"
                )
        except Exception as e:
            logger.exception(f"Monitoring tool error: {e}")
            return SkillResponse(
                success=False,
                message=f"Monitoring operation failed: {str(e)}",
                error=str(e)
            )

    def _system_metrics(self, params: Dict[str, Any]) -> SkillResponse:
        """Get system metrics."""
        include_processes = params.get("include_processes", False)
        process_count = params.get("process_count", 10)

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # Memory
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk
        disk = psutil.disk_usage("/")

        # Load average (Unix only)
        try:
            load_avg = os.getloadavg()
        except (OSError, AttributeError):
            load_avg = (0, 0, 0)

        result = {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else None,
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "percent": swap.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round(disk.percent, 1),
            },
            "load_average": {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2),
            },
            "uptime_seconds": time.time() - psutil.boot_time(),
        }

        if include_processes:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    pinfo = proc.info
                    processes.append({
                        "pid": pinfo["pid"],
                        "name": pinfo["name"],
                        "cpu_percent": pinfo["cpu_percent"] or 0,
                        "memory_percent": round(pinfo["memory_percent"] or 0, 2),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU and get top N
            processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
            result["top_processes"] = processes[:process_count]

        return SkillResponse(
            success=True,
            message="System metrics collected",
            data=result
        )

    def _process_metrics(self, params: Dict[str, Any]) -> SkillResponse:
        """Get metrics for a specific process."""
        pid = params.get("pid")
        name = params.get("name")

        if not pid and not name:
            return SkillResponse(
                success=False,
                message="Either pid or name is required",
                error="missing_parameter"
            )

        processes = []

        if pid:
            try:
                proc = psutil.Process(pid)
                processes.append(proc)
            except psutil.NoSuchProcess:
                return SkillResponse(
                    success=False,
                    message=f"Process {pid} not found",
                    error="not_found"
                )
        else:
            for proc in psutil.process_iter(["name"]):
                if name.lower() in proc.info["name"].lower():
                    processes.append(proc)

        if not processes:
            return SkillResponse(
                success=False,
                message=f"No process found matching '{name}'",
                error="not_found"
            )

        results = []
        for proc in processes[:10]:  # Limit to 10 matches
            try:
                with proc.oneshot():
                    results.append({
                        "pid": proc.pid,
                        "name": proc.name(),
                        "status": proc.status(),
                        "cpu_percent": proc.cpu_percent(),
                        "memory_percent": round(proc.memory_percent(), 2),
                        "memory_mb": round(proc.memory_info().rss / (1024**2), 2),
                        "threads": proc.num_threads(),
                        "open_files": len(proc.open_files()),
                        "connections": len(proc.connections()),
                        "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                        "cmdline": " ".join(proc.cmdline()[:5]),  # First 5 args
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return SkillResponse(
            success=True,
            message=f"Found {len(results)} process(es)",
            data={"processes": results}
        )

    def _analyze_logs(self, params: Dict[str, Any]) -> SkillResponse:
        """Analyze log file."""
        path = params["path"]
        lines_count = params.get("lines", 100)
        pattern = params.get("pattern")
        level = params.get("level")
        since = params.get("since")

        # Security check
        if self._allowed_log_paths and not any(path.startswith(p) for p in self._allowed_log_paths):
            return SkillResponse(
                success=False,
                message=f"Path not in allowed log paths: {path}",
                error="access_denied"
            )

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"Log file not found: {path}",
                error="not_found"
            )

        # Parse since parameter
        since_dt = None
        if since:
            if since.endswith("h"):
                since_dt = datetime.now() - timedelta(hours=int(since[:-1]))
            elif since.endswith("m"):
                since_dt = datetime.now() - timedelta(minutes=int(since[:-1]))
            else:
                try:
                    since_dt = datetime.fromisoformat(since)
                except ValueError:
                    pass

        # Read log file
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                # Read last N lines
                all_lines = f.readlines()
                lines = all_lines[-lines_count:]
        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Error reading log: {e}",
                error=str(e)
            )

        # Filter by pattern
        if pattern:
            regex = re.compile(pattern, re.IGNORECASE)
            lines = [l for l in lines if regex.search(l)]

        # Filter by level
        if level:
            level_pattern = re.compile(rf"\b{level}\b", re.IGNORECASE)
            lines = [l for l in lines if level_pattern.search(l)]

        # Filter by time (basic timestamp detection)
        if since_dt:
            filtered = []
            timestamp_pattern = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")
            for line in lines:
                match = timestamp_pattern.search(line)
                if match:
                    try:
                        line_dt = datetime.fromisoformat(match.group().replace(" ", "T"))
                        if line_dt >= since_dt:
                            filtered.append(line)
                    except ValueError:
                        filtered.append(line)  # Keep if can't parse
                else:
                    filtered.append(line)  # Keep if no timestamp
            lines = filtered

        return SkillResponse(
            success=True,
            message=f"Retrieved {len(lines)} log line(s)",
            data={
                "path": path,
                "lines": [l.strip() for l in lines],
                "total_lines": len(all_lines),
                "filters_applied": {
                    "pattern": pattern,
                    "level": level,
                    "since": since,
                }
            }
        )

    def _log_stats(self, params: Dict[str, Any]) -> SkillResponse:
        """Get log file statistics."""
        path = params["path"]
        hours = params.get("hours", 24)

        if not os.path.exists(path):
            return SkillResponse(
                success=False,
                message=f"Log file not found: {path}",
                error="not_found"
            )

        level_counts = defaultdict(int)
        hourly_counts = defaultdict(int)
        error_samples = []

        timestamp_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}):\d{2}:\d{2}")
        level_pattern = re.compile(r"\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b", re.IGNORECASE)

        cutoff = datetime.now() - timedelta(hours=hours)

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    # Extract timestamp
                    ts_match = timestamp_pattern.search(line)
                    if ts_match:
                        try:
                            hour_key = ts_match.group(1).replace(" ", "T")
                            line_dt = datetime.fromisoformat(hour_key + ":00:00")
                            if line_dt < cutoff:
                                continue
                            hourly_counts[hour_key] += 1
                        except ValueError:
                            pass

                    # Extract level
                    level_match = level_pattern.search(line)
                    if level_match:
                        level = level_match.group(1).upper()
                        if level == "WARN":
                            level = "WARNING"
                        elif level == "FATAL":
                            level = "CRITICAL"
                        level_counts[level] += 1

                        # Sample errors
                        if level in ("ERROR", "CRITICAL") and len(error_samples) < 5:
                            error_samples.append(line.strip()[:200])

        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Error analyzing log: {e}",
                error=str(e)
            )

        # File stats
        stat = os.stat(path)

        return SkillResponse(
            success=True,
            message="Log statistics collected",
            data={
                "path": path,
                "file_size_mb": round(stat.st_size / (1024**2), 2),
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "level_counts": dict(level_counts),
                "hourly_counts": dict(sorted(hourly_counts.items())[-24:]),
                "error_samples": error_samples,
                "analysis_period_hours": hours,
            }
        )

    def _record_metric(self, params: Dict[str, Any]) -> SkillResponse:
        """Record a custom metric."""
        name = params["name"]
        value = params["value"]
        metric_type = params.get("type", "gauge")
        tags = params.get("tags", {})

        if metric_type == "counter":
            self._collector.increment(name, value)
        elif metric_type == "gauge":
            self._collector.gauge(name, value)
        else:
            self._collector.record(name, value, tags)

        return SkillResponse(
            success=True,
            message=f"Recorded {metric_type} metric: {name}={value}",
            data={"name": name, "value": value, "type": metric_type, "tags": tags}
        )

    def _get_metrics(self, params: Dict[str, Any]) -> SkillResponse:
        """Get recorded metrics."""
        name = params.get("name")
        since_minutes = params.get("since_minutes", 60)

        if name:
            metrics = self._collector.get_metrics(name, since_minutes)
            counter = self._collector.get_counter(name)
            gauge = self._collector.get_gauge(name)

            return SkillResponse(
                success=True,
                message=f"Retrieved metrics for {name}",
                data={
                    "name": name,
                    "history": metrics,
                    "counter": counter,
                    "gauge": gauge,
                }
            )
        else:
            all_metrics = self._collector.list_metrics()
            return SkillResponse(
                success=True,
                message=f"Found {len(all_metrics)} metric(s)",
                data={"metrics": all_metrics}
            )

    def _health_check(self, params: Dict[str, Any]) -> SkillResponse:
        """Run health checks."""
        checks = params.get("checks", [])

        if not checks:
            # Default checks
            checks = [
                {"name": "cpu", "type": "memory", "threshold": 90},
                {"name": "memory", "type": "memory", "threshold": 90},
                {"name": "disk", "type": "disk", "target": "/", "threshold": 90},
            ]

        results = []
        all_healthy = True

        for check in checks:
            check_result = {"name": check["name"], "type": check["type"]}

            try:
                if check["type"] == "memory":
                    memory = psutil.virtual_memory()
                    check_result["value"] = memory.percent
                    check_result["healthy"] = memory.percent < check.get("threshold", 90)

                elif check["type"] == "disk":
                    disk = psutil.disk_usage(check.get("target", "/"))
                    check_result["value"] = disk.percent
                    check_result["healthy"] = disk.percent < check.get("threshold", 90)

                elif check["type"] == "process":
                    found = False
                    for proc in psutil.process_iter(["name"]):
                        if check["target"].lower() in proc.info["name"].lower():
                            found = True
                            break
                    check_result["value"] = found
                    check_result["healthy"] = found

                elif check["type"] == "tcp":
                    import socket
                    target = check["target"]
                    host, port = target.rsplit(":", 1)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, int(port)))
                    sock.close()
                    check_result["value"] = result == 0
                    check_result["healthy"] = result == 0

                elif check["type"] == "http":
                    import urllib.request
                    try:
                        response = urllib.request.urlopen(check["target"], timeout=10)
                        check_result["value"] = response.status
                        check_result["healthy"] = 200 <= response.status < 400
                    except Exception as e:
                        check_result["value"] = str(e)
                        check_result["healthy"] = False

                else:
                    check_result["healthy"] = False
                    check_result["error"] = f"Unknown check type: {check['type']}"

            except Exception as e:
                check_result["healthy"] = False
                check_result["error"] = str(e)

            if not check_result.get("healthy", False):
                all_healthy = False

            results.append(check_result)

        return SkillResponse(
            success=True,
            message="Health checks completed" if all_healthy else "Some health checks failed",
            data={
                "healthy": all_healthy,
                "checks": results,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _set_alert(self, params: Dict[str, Any]) -> SkillResponse:
        """Set up an alert."""
        alert = {
            "name": params["name"],
            "metric": params["metric"],
            "custom_metric": params.get("custom_metric"),
            "operator": params["operator"],
            "threshold": params["threshold"],
            "enabled": params.get("enabled", True),
            "created_at": datetime.now().isoformat(),
        }

        # Replace existing alert with same name
        self._alerts = [a for a in self._alerts if a["name"] != alert["name"]]
        self._alerts.append(alert)

        return SkillResponse(
            success=True,
            message=f"Alert '{params['name']}' configured",
            data={"alert": alert}
        )

    def _check_alerts(self) -> SkillResponse:
        """Check all configured alerts."""
        triggered = []
        ok = []

        for alert in self._alerts:
            if not alert.get("enabled", True):
                continue

            current_value = None

            if alert["metric"] == "cpu":
                current_value = psutil.cpu_percent()
            elif alert["metric"] == "memory":
                current_value = psutil.virtual_memory().percent
            elif alert["metric"] == "disk":
                current_value = psutil.disk_usage("/").percent
            elif alert["metric"] == "custom":
                current_value = self._collector.get_gauge(alert["custom_metric"])

            if current_value is None:
                continue

            # Evaluate condition
            op = alert["operator"]
            threshold = alert["threshold"]

            is_triggered = False
            if op == ">" and current_value > threshold:
                is_triggered = True
            elif op == "<" and current_value < threshold:
                is_triggered = True
            elif op == ">=" and current_value >= threshold:
                is_triggered = True
            elif op == "<=" and current_value <= threshold:
                is_triggered = True
            elif op == "==" and current_value == threshold:
                is_triggered = True

            result = {
                "name": alert["name"],
                "metric": alert["metric"],
                "current_value": current_value,
                "threshold": threshold,
                "operator": op,
            }

            if is_triggered:
                triggered.append(result)
            else:
                ok.append(result)

        return SkillResponse(
            success=True,
            message=f"{len(triggered)} alert(s) triggered, {len(ok)} OK",
            data={
                "triggered": triggered,
                "ok": ok,
                "total_alerts": len(self._alerts),
            }
        )

    def _disk_usage(self, params: Dict[str, Any]) -> SkillResponse:
        """Get detailed disk usage."""
        path = params.get("path", "/")
        include_inodes = params.get("include_inodes", False)

        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                part_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": round(usage.percent, 1),
                }
                partitions.append(part_info)
            except (PermissionError, OSError):
                continue

        result = {
            "partitions": partitions,
        }

        # Specific path usage
        try:
            usage = psutil.disk_usage(path)
            result["path_usage"] = {
                "path": path,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": round(usage.percent, 1),
            }
        except (PermissionError, OSError) as e:
            result["path_usage_error"] = str(e)

        # IO counters
        try:
            io = psutil.disk_io_counters()
            result["io_counters"] = {
                "read_mb": round(io.read_bytes / (1024**2), 2),
                "write_mb": round(io.write_bytes / (1024**2), 2),
                "read_count": io.read_count,
                "write_count": io.write_count,
            }
        except Exception:
            pass

        return SkillResponse(
            success=True,
            message=f"Disk usage for {len(partitions)} partition(s)",
            data=result
        )

    def _network_stats(self, params: Dict[str, Any]) -> SkillResponse:
        """Get network statistics."""
        interface = params.get("interface")
        include_connections = params.get("include_connections", False)

        # Network IO
        io_counters = psutil.net_io_counters(pernic=True)

        interfaces = {}
        for name, counters in io_counters.items():
            if interface and name != interface:
                continue

            interfaces[name] = {
                "bytes_sent_mb": round(counters.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(counters.bytes_recv / (1024**2), 2),
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errors_in": counters.errin,
                "errors_out": counters.errout,
                "drops_in": counters.dropin,
                "drops_out": counters.dropout,
            }

        result = {
            "interfaces": interfaces,
        }

        # Network addresses
        addrs = psutil.net_if_addrs()
        result["addresses"] = {}
        for name, addr_list in addrs.items():
            if interface and name != interface:
                continue
            result["addresses"][name] = [
                {"family": str(addr.family), "address": addr.address}
                for addr in addr_list
            ]

        # Active connections
        if include_connections:
            connections = []
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "ESTABLISHED":
                    connections.append({
                        "local": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        "remote": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        "status": conn.status,
                        "pid": conn.pid,
                    })
            result["connections"] = connections[:50]  # Limit to 50

        return SkillResponse(
            success=True,
            message=f"Network stats for {len(interfaces)} interface(s)",
            data=result
        )
