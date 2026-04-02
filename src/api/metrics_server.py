"""
Metrics HTTP Server - Prometheus metrics exposure endpoint.

Lightweight HTTP server exposing /metrics endpoint for Prometheus scraping.
"""

import argparse
import logging
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from monitoring.metrics import ApplicationMetrics, MetricsCollector
except ImportError:
    # Fallback if monitoring module not available
    ApplicationMetrics = None  # type: ignore[misc]
    MetricsCollector = None  # type: ignore[misc]


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoint."""

    # Class-level metrics collector (shared across requests)
    metrics_collector: Optional['MetricsCollector'] = None

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger."""
        logger.info(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == '/metrics':
            self._handle_metrics()
        elif self.path == '/health':
            self._handle_health()
        else:
            self._send_404()

    def _handle_metrics(self) -> None:
        """Handle /metrics endpoint."""
        try:
            if self.metrics_collector:
                content = self.metrics_collector.generate_metrics()
            else:
                content = self._generate_default_metrics()

            self._send_response(200, content, 'text/plain; version=0.0.4')
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            self._send_response(500, f"Error: {e}", 'text/plain')

    def _handle_health(self) -> None:
        """Handle /health endpoint."""
        health_data = {
            "status": "healthy",
            "service": "opc200-metrics",
            "version": "2.3.0"
        }
        import json
        self._send_response(200, json.dumps(health_data), 'application/json')

    def _send_404(self) -> None:
        """Send 404 response."""
        self._send_response(404, "Not Found", 'text/plain')

    def _send_response(self, status_code: int, content: str, content_type: str) -> None:
        """Send HTTP response."""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def _generate_default_metrics(self) -> str:
        """Generate default metrics when collector is not available."""
        return """# HELP opc200_metrics_server_up Metrics server is running
# TYPE opc200_metrics_server_up gauge
opc200_metrics_server_up 1

# HELP opc200_metrics_server_info Metrics server information
# TYPE opc200_metrics_server_info gauge
opc200_metrics_server_info{version="2.3.0"} 1
"""


def create_metrics_handler(collector: Optional['MetricsCollector'] = None) -> type:
    """Create a metrics handler class with injected collector."""
    class ConfiguredMetricsHandler(MetricsHandler):
        metrics_collector = collector

    return ConfiguredMetricsHandler


def run_server(
    port: int = 9090,
    host: str = '0.0.0.0',
    collector: Optional['MetricsCollector'] = None
) -> None:
    """Run the metrics HTTP server."""
    handler_class = create_metrics_handler(collector)
    server = HTTPServer((host, port), handler_class)

    logger.info(f"Starting metrics server on {host}:{port}")
    logger.info(f"Endpoints: http://{host}:{port}/metrics, http://{host}:{port}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server...")
    finally:
        server.server_close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='OPC200 Metrics Server')
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=9090,
        help='Port to listen on (default: 9090)'
    )
    parser.add_argument(
        '--host', '-H',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--with-app-metrics',
        action='store_true',
        help='Enable application metrics collection'
    )

    args = parser.parse_args()

    # Initialize metrics collector if requested
    collector: Optional[MetricsCollector] = None
    if args.with_app_metrics and ApplicationMetrics:
        app_metrics = ApplicationMetrics()
        collector = app_metrics.collector
        logger.info("Application metrics enabled")

    run_server(port=args.port, host=args.host, collector=collector)


if __name__ == '__main__':
    main()
