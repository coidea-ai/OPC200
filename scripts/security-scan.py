#!/usr/bin/env python3
"""
Security scanning script for OPC200.
Runs bandit (static analysis) and safety (dependency vulnerability) scans.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_bandit():
    """Run bandit security scanner."""
    print("🔍 Running Bandit security scan...")
    
    cmd = [
        "bandit",
        "-r", "src/",
        "-c", ".bandit.yml",
        "-f", "json",
        "-o", "/tmp/bandit-report.json"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Bandit returns non-zero if issues found
    try:
        with open("/tmp/bandit-report.json") as f:
            report = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        report = {"results": [], "metrics": {}}
    
    high_severity = [r for r in report.get("results", []) if r.get("issue_severity") == "HIGH"]
    medium_severity = [r for r in report.get("results", []) if r.get("issue_severity") == "MEDIUM"]
    
    print(f"   Found {len(high_severity)} high, {len(medium_severity)} medium severity issues")
    
    return len(high_severity) == 0, report


def run_safety():
    """Run safety dependency vulnerability scan."""
    print("🔍 Running Safety dependency scan...")
    
    cmd = ["safety", "check", "--json", "--full-report"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        report = json.loads(result.stdout) if result.stdout else {"vulnerabilities": []}
    except json.JSONDecodeError:
        report = {"vulnerabilities": []}
    
    vulnerabilities = report.get("vulnerabilities", [])
    
    # Filter for high severity (CVSS >= 7.0)
    high_vulns = [v for v in vulnerabilities if v.get("cvssv3", 0) >= 7.0]
    
    print(f"   Found {len(high_vulns)} high severity vulnerabilities")
    
    return len(high_vulns) == 0, report


def generate_report(bandit_ok, bandit_report, safety_ok, safety_report):
    """Generate consolidated security report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "bandit_passed": bandit_ok,
            "safety_passed": safety_ok,
            "overall_passed": bandit_ok and safety_ok
        },
        "bandit": bandit_report,
        "safety": safety_report
    }
    
    # Save report
    report_path = Path("reports/security-scan.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Report saved to {report_path}")
    
    return report


def main():
    """Main entry point."""
    print("=" * 60)
    print("OPC200 Security Scanner")
    print("=" * 60)
    print()
    
    bandit_ok, bandit_report = run_bandit()
    print()
    safety_ok, safety_report = run_safety()
    print()
    
    generate_report(bandit_ok, bandit_report, safety_ok, safety_report)
    
    print("\n" + "=" * 60)
    if bandit_ok and safety_ok:
        print("✅ Security scan PASSED")
        return 0
    else:
        print("❌ Security scan FAILED")
        if not bandit_ok:
            print("   - Bandit found high severity issues")
        if not safety_ok:
            print("   - Safety found high severity vulnerabilities")
        return 1


if __name__ == "__main__":
    sys.exit(main())