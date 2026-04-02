"""
Metrics Mixin Module - Easy instrumentation for core modules.

Provides a reusable mixin class for adding Prometheus metrics to any class.
"""
import functools
import time
from typing import Any, Callable, Optional, TypeVar, cast

from src.monitoring.metrics import ApplicationMetrics, MetricsCollector

F = TypeVar('F', bound=Callable[..., Any])


class MetricsMixin:
    """Mixin class adding metrics collection capabilities.

    Usage:
        class MyClass(MetricsMixin):
            def __init__(self):
                super().__init__()
                self._init_metrics("my_class")

            @MetricsMixin.timed("operation_duration")
            def my_method(self):
                pass
    """

    def __init__(self) -> None:
        """Initialize mixin."""
        self._metrics: Optional[ApplicationMetrics] = None
        self._metrics_prefix: str = ""

    def _init_metrics(self, prefix: str, collector: Optional[MetricsCollector] = None) -> None:
        """Initialize metrics for this instance.

        Args:
            prefix: Metric name prefix (e.g., "journal_manager")
            collector: Optional custom collector
        """
        self._metrics_prefix = prefix
        if collector:
            self._metrics = ApplicationMetrics(collector)
        else:
            self._metrics = ApplicationMetrics()

    def _record_counter(self, name: str, amount: float = 1, **labels) -> None:
        """Record a counter metric.

        Args:
            name: Metric name suffix (prefix added automatically)
            amount: Amount to increment
            **labels: Label values for the counter
        """
        if self._metrics is None:
            return

        full_name = f"{self._metrics_prefix}_{name}"
        # Create counter if not exists
        counter = self._metrics.collector.create_counter(
            full_name,
            f"Counter for {full_name}",
            list(labels.keys()) if labels else None
        )

        if labels:
            counter.labels(**labels).inc(amount)
        else:
            counter.inc(amount)

    def _record_histogram(self, name: str, value: float, **labels) -> None:
        """Record a histogram observation.

        Args:
            name: Metric name suffix
            value: Value to observe
            **labels: Label values for the histogram
        """
        if self._metrics is None:
            return

        full_name = f"{self._metrics_prefix}_{name}"
        histogram = self._metrics.collector.create_histogram(
            full_name,
            f"Histogram for {full_name}",
            labels=list(labels.keys()) if labels else None
        )

        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)

    def _record_gauge(self, name: str, value: float, **labels) -> None:
        """Record a gauge value.

        Args:
            name: Metric name suffix
            value: Value to set
            **labels: Label values for the gauge
        """
        if self._metrics is None:
            return

        full_name = f"{self._metrics_prefix}_{name}"
        gauge = self._metrics.collector.create_gauge(
            full_name,
            f"Gauge for {full_name}",
            labels=list(labels.keys()) if labels else None
        )

        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)

    @staticmethod
    def timed(name: str, **labels: Any) -> Callable[[F], F]:
        """Decorator to time method execution.

        Usage:
            @MetricsMixin.timed("method_duration", operation="create")
            def my_method(self):
                pass
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    return func(self, *args, **kwargs)
                finally:
                    duration = time.time() - start_time
                    if isinstance(self, MetricsMixin):
                        self._record_histogram(name, duration, **labels)
            return cast(F, wrapper)
        return decorator

    @staticmethod
    def counted(name: str, **labels: Any) -> Callable[[F], F]:
        """Decorator to count method calls.

        Usage:
            @MetricsMixin.counted("method_calls", operation="create")
            def my_method(self):
                pass
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                if isinstance(self, MetricsMixin):
                    self._record_counter(name, **labels)
                return func(self, *args, **kwargs)
            return cast(F, wrapper)
        return decorator
