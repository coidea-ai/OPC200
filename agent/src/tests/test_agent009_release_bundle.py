"""AGENT-009: GNU sha256sum line format for opc200-agent zip."""

import hashlib


def test_sha256sums_two_space_format():
    name = "opc200-agent-2.5.0.zip"
    payload = b"test-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    line = f"{digest}  {name}\n"
    assert "  " in line
    parts = line.strip().split(None, 1)
    assert len(parts) == 2
    assert parts[0] == digest
    assert parts[1] == name
