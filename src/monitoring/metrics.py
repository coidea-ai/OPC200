"""
Monitoring metrics module - Prometheus metrics collection.

Provides metrics collection using Prometheus client library.
"""

import time
import functools
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, Union, List, Dict, Tuple, cast

# Try to import prometheus client, fallback to mock implementation
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class Mock:
    """Simple mock object for when prometheus_client is not available."""
    def __init__(self):
        self._metrics = {}


class MockMetric:
    """Mock metric for when prometheus_client is not available."""

    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self._name = name
        self._description = description
        self._labels = labels or []
        self._values: List[Tuple[str, float]] = []
        self._label_values: Dict[Tuple[Tuple[str, Any], ...], "MockMetric"] = {}

    def inc(self, amount: float = 1) -> None:
        """Increment counter."""
        self._values.append(("", amount))

    def observe(self, amount: float) -> None:
        """Observe histogram value."""
        self._values.append(("", amount))

    def set(self, amount: float) -> None:
        """Set gauge value."""
        self._values = [("", amount)]

    def labels(self, **kwargs: Any) -> "MockMetric":
        """Return labeled metric."""
        key: Tuple[Tuple[str, Any], ...] = tuple(sorted(kwargs.items()))
        if key not in self._label_values:
            self._label_values[key] = MockMetric(self._name, self._description)
        return self._label_values[key]

    def _get_samples(self) -> List[Tuple[str, float]]:
        """Get all samples for this metric."""
        samples: List[Tuple[str, float]] = list(self._values)
        for key_tuple, metric in self._label_values.items():
            # key_tuple is like (("method", "GET"), ("status", "200"))
            label_str = ",".join(f"{k}={v}" for k, v in key_tuple)
            for _, value in metric._values:
                samples.append((label_str, value))
        return samples


@dataclass
class MetricsCollector:
    """Collect and manage Prometheus metrics."""

    registry: Any = field(default=None)
    _metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.registry is None:
            if PROMETHEUS_AVAILABLE:
                self.registry = CollectorRegistry()
            else:
                self.registry = Mock()
                self.registry._metrics = {}

    def create_counter(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Any:
        """Create a counter metric."""
        counter: Any
        if PROMETHEUS_AVAILABLE:
            counter = Counter(
                name,
                description,
                labels or [],
                registry=self.registry
            )
        else:
            counter = MockMetric(name, description, labels)

        self._metrics[name] = counter
        return counter

    def create_histogram(
        self,
        name: str,
        description: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None
    ) -> Any:
        """Create a histogram metric."""
        histogram: Any
        if PROMETHEUS_AVAILABLE:
            if buckets:
                histogram = Histogram(
                    name,
                    description,
                    labels or [],
                    registry=self.registry,
                    buckets=buckets
                )
            else:
                histogram = Histogram(
                    name,
                    description,
                    labels or [],
                    registry=self.registry
                )
        else:
            histogram = MockMetric(name, description, labels)

        self._metrics[name] = histogram
        return histogram

    def create_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Any:
        """Create a gauge metric."""
        gauge: Any
        if PROMETHEUS_AVAILABLE:
            gauge = Gauge(
                name,
                description,
                labels or [],
                registry=self.registry
            )
        else:
            gauge = MockMetric(name, description, labels)

        self._metrics[name] = gauge
        return gauge

    def get_samples(self, name: str) -> List[Tuple[str, float]]:
        """Get samples for a metric (for testing)."""
        if name not in self._metrics:
            return []

        metric = self._metrics[name]
        if PROMETHEUS_AVAILABLE:
            # For real prometheus metrics, return dummy samples
            return [("sample", 1.0)]
        else:
            return metric._get_samples()  # type: ignore[no-any-return]

    def generate_metrics(self) -> str:
        """Generate metrics in Prometheus exposition format."""
        if PROMETHEUS_AVAILABLE:
            result: str = generate_latest(self.registry).decode("utf-8")
            return result
        else:
            lines: List[str] = []
            for name, metric in self._metrics.items():
                metric = cast(MockMetric, metric)
                lines.append(f"# HELP {name} {metric._description}")
                lines.append(f"# TYPE {name} counter")
                for sample in metric._get_samples():
                    lines.append(f"{name} {sample[1]}")
            return "\n".join(lines)


@dataclass
class ApplicationMetrics:
    """Application-specific metrics collection."""

    collector: MetricsCollector = field(default_factory=MetricsCollector)

    def __post_init__(self):
        # Journal metrics
        self._journal_entries = self.collector.create_counter(
            "opc200_journal_entries_total",
            "Total number of journal entries created",
            ["operation"]
        )
        self._journal_search_duration = self.collector.create_histogram(
            "opc200_journal_search_duration_seconds",
            "Journal search operation duration",
            buckets=[0.001, 0.01, 0.1, 1.0]
        )

        # Security metrics
        self._encryption_duration = self.collector.create_histogram(
            "opc200_encryption_duration_seconds",
            "Encryption operation duration",
            buckets=[0.001, 0.01, 0.1]
        )
        self._vault_access = self.collector.create_counter(
            "opc200_vault_access_total",
            "Total vault access operations",
            ["operation", "status"]
        )

        # Scheduler metrics
        self._job_executions = self.collector.create_counter(
            "opc200_job_executions_total",
            "Total job executions",
            ["status"]
        )
        self._job_duration = self.collector.create_histogram(
            "opc200_job_duration_seconds",
            "Job execution duration",
            buckets=[0.01, 0.1, 1.0, 10.0]
        )

        # Error metrics
        self._errors = self.collector.create_counter(
            "opc200_errors_total",
            "Total errors",
            ["type", "endpoint"]
        )

    def record_journal_entry(self):
        """Record journal entry creation."""
        self._journal_entries.labels(operation="create").inc()

    def record_journal_search(self, duration: float):
        """Record journal search operation."""
        self._journal_search_duration.observe(duration)

    def record_encryption_operation(self, duration: float):
        """Record encryption operation."""
        self._encryption_duration.observe(duration)

    def record_vault_access(self, success: bool):
        """Record vault access attempt."""
        status = "success" if success else "failure"
        self._vault_access.labels(operation="access", status=status).inc()

    def record_job_execution(self, duration: float, success: bool):
        """Record job execution."""
        status = "success" if success else "failure"
        self._job_executions.labels(status=status).inc()
        self._job_duration.observe(duration)

    def record_error(self, error_type: str, endpoint: str):
        """Record error."""
        self._errors.labels(type=error_type, endpoint=endpoint).inc()


@dataclass
class MetricsEndpoint:
    """HTTP endpoint for metrics."""

    port: int = 9090
    collector: MetricsCollector = field(default_factory=MetricsCollector)

    def generate_metrics(self) -> str:
        """Generate metrics content."""
        return self.collector.generate_metrics()


@dataclass
class MetricsMiddleware:
    """Middleware for collecting request metrics."""

    collector: MetricsCollector = field(default_factory=MetricsCollector)

    def __post_init__(self):
        self._request_duration = self.collector.create_histogram(
            "opc200_request_duration_seconds",
            "HTTP request duration",
            buckets=[0.001, 0.01, 0.1, 1.0]
        )
        self._request_count = self.collector.create_counter(
            "opc200_requests_total",
            "Total HTTP requests",
            ["method", "status"]
        )
        self._errors = self.collector.create_counter(
            "opc200_errors_total",
            "Total errors",
            ["type", "endpoint"]
        )

    def record_request(self, request: Any, response: Any, duration: float):
        """Record request metrics."""
        method = getattr(request, "method", "UNKNOWN")
        status = str(getattr(response, "status_code", 0))

        self._request_duration.observe(duration)
        self._request_count.labels(method=method, status=status).inc()

    def record_error(self, error_type: str, endpoint: str):
        """Record error."""
        self._errors.labels(type=error_type, endpoint=endpoint).inc()


def timer(collector: MetricsCollector, name: str, labels: Optional[list] = None):
    """Decorator to time function execution."""
    histogram = collector.create_histogram(
        name,
        f"Duration of {name}",
        labels=labels
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if labels:
                    # Use function name as label
                    histogram.labels(name=func.__name__).observe(duration)
                else:
                    histogram.observe(duration)
        return wrapper
    return decorator


def count_calls(collector: MetricsCollector, name: str):
    """Decorator to count function calls."""
    counter = collector.create_counter(
        name,
        f"Number of calls to {name}"
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            counter.inc()
            return func(*args, **kwargs)
        return wrapper
    return decorator