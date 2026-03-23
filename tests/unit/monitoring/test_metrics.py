"""
Unit tests for monitoring/metrics.py - Prometheus metrics collection.
Following TDD: Red-Green-Refactor cycle.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

pytestmark = pytest.mark.unit


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_collector_initialization(self):
        """Test metrics collector initialization."""
        # Arrange & Act
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()

        # Assert
        assert collector is not None
        assert collector.registry is not None

    def test_counter_creation(self):
        """Test creating a counter metric."""
        # Arrange
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()

        # Act
        counter = collector.create_counter(
            name="test_requests_total",
            description="Total test requests",
            labels=["method", "status"]
        )

        # Assert
        assert counter is not None
        assert counter._name == "test_requests_total"

    def test_counter_increment(self):
        """Test incrementing a counter."""
        # Arrange
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()
        counter = collector.create_counter(
            name="requests_total",
            description="Total requests",
            labels=["method"]
        )

        # Act
        counter.inc()
        counter.labels(method="GET").inc()
        counter.labels(method="GET").inc()
        counter.labels(method="POST").inc()

        # Assert
        samples = collector.get_samples("requests_total")
        assert len(samples) == 4  # Total + GET + GET + POST

    def test_histogram_creation(self):
        """Test creating a histogram metric."""
        # Arrange
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()

        # Act
        histogram = collector.create_histogram(
            name="request_duration_seconds",
            description="Request duration",
            buckets=[0.1, 0.5, 1.0, 5.0],
            labels=["endpoint"]
        )

        # Assert
        assert histogram is not None
        assert histogram._name == "request_duration_seconds"

    def test_histogram_observe(self):
        """Test observing values in histogram."""
        # Arrange
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()
        histogram = collector.create_histogram(
            name="duration_seconds",
            description="Duration",
            buckets=[0.1, 0.5, 1.0]
        )

        # Act
        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)

        # Assert
        samples = collector.get_samples("duration_seconds")
        assert len(samples) > 0

    def test_gauge_creation(self):
        """Test creating a gauge metric."""
        # Arrange
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()

        # Act
        gauge = collector.create_gauge(
            name="active_connections",
            description="Active connections",
            labels=["service"]
        )

        # Assert
        assert gauge is not None
        assert gauge._name == "active_connections"

    def test_gauge_set(self):
        """Test setting gauge value."""
        # Arrange
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()
        gauge = collector.create_gauge(
            name="connections",
            description="Connections"
        )

        # Act
        gauge.set(10)
        gauge.set(5)

        # Assert
        samples = collector.get_samples("connections")
        assert len(samples) == 1


class TestApplicationMetrics:
    """Tests for application-specific metrics."""

    def test_journal_metrics(self):
        """Test journal operation metrics."""
        # Arrange
        from src.monitoring.metrics import ApplicationMetrics

        app_metrics = ApplicationMetrics()

        # Act
        app_metrics.record_journal_entry()
        app_metrics.record_journal_entry()
        app_metrics.record_journal_search(duration=0.05)

        # Assert
        samples = app_metrics.collector.get_samples("opc200_journal_entries_total")
        assert len(samples) > 0

    def test_security_metrics(self):
        """Test security operation metrics."""
        # Arrange
        from src.monitoring.metrics import ApplicationMetrics

        app_metrics = ApplicationMetrics()

        # Act
        app_metrics.record_encryption_operation(duration=0.01)
        app_metrics.record_vault_access(success=True)
        app_metrics.record_vault_access(success=False)

        # Assert
        samples = app_metrics.collector.get_samples("opc200_encryption_duration_seconds")
        assert len(samples) > 0

    def test_scheduler_metrics(self):
        """Test scheduler operation metrics."""
        # Arrange
        from src.monitoring.metrics import ApplicationMetrics

        app_metrics = ApplicationMetrics()

        # Act
        app_metrics.record_job_execution(duration=0.1, success=True)
        app_metrics.record_job_execution(duration=0.2, success=False)

        # Assert
        samples = app_metrics.collector.get_samples("opc200_job_executions_total")
        assert len(samples) > 0


class TestMetricsEndpoint:
    """Tests for metrics HTTP endpoint."""

    def test_metrics_endpoint(self):
        """Test metrics endpoint returns Prometheus format."""
        # Arrange
        from src.monitoring.metrics import MetricsEndpoint

        endpoint = MetricsEndpoint(port=9099)
        endpoint.collector.create_counter("test_counter", "Test")

        # Act
        content = endpoint.generate_metrics()

        # Assert
        assert "test_counter" in content
        assert "# HELP" in content
        assert "# TYPE" in content


class TestMetricsMiddleware:
    """Tests for metrics collection middleware."""

    def test_request_timing_middleware(self):
        """Test middleware times requests."""
        # Arrange
        from src.monitoring.metrics import MetricsMiddleware

        middleware = MetricsMiddleware()

        # Create mock request/response
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.path = "/api/test"

        mock_response = Mock()
        mock_response.status_code = 200

        # Act & Assert (should not raise)
        middleware.record_request(mock_request, mock_response, duration=0.05)

    def test_error_tracking(self):
        """Test middleware tracks errors."""
        # Arrange
        from src.monitoring.metrics import MetricsMiddleware

        middleware = MetricsMiddleware()

        # Act
        middleware.record_error("ValueError", "/api/test")

        # Assert
        samples = middleware.collector.get_samples("opc200_errors_total")
        assert len(samples) > 0


class TestMetricsDecorators:
    """Tests for metrics decorators."""

    def test_timer_decorator(self):
        """Test timer decorator records duration."""
        # Arrange
        from src.monitoring.metrics import timer, MetricsCollector

        collector = MetricsCollector()

        @timer(collector, "function_duration_seconds", ["name"])
        def sample_function():
            return "result"

        # Act
        result = sample_function()

        # Assert
        assert result == "result"
        samples = collector.get_samples("function_duration_seconds")
        assert len(samples) > 0

    def test_count_decorator(self):
        """Test count decorator records calls."""
        # Arrange
        from src.monitoring.metrics import count_calls, MetricsCollector

        collector = MetricsCollector()

        @count_calls(collector, "function_calls_total")
        def sample_function():
            return "result"

        # Act
        sample_function()
        sample_function()

        # Assert
        samples = collector.get_samples("function_calls_total")
        assert len(samples) > 0