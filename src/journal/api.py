"""Minimal Journal API service for container runtime health."""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body = json.dumps({"status": "healthy", "service": "opc200-journal"})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    host = os.environ.get("JOURNAL_API_HOST", "0.0.0.0")  # nosec B104
    port = int(os.environ.get("JOURNAL_API_PORT", "8080"))
    server = HTTPServer((host, port), _Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
