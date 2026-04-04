"""
Report Generator for Video Asset Processing Logs
=================================================

Reads the JSONL log file and generates a human-readable report.

Usage:
    python report_generator.py [--output report.txt]
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load and parse the JSONL file."""
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def classify_status(record: Dict[str, Any]) -> str:
    """Classify the final status based on status and message."""
    if record.get("status") == "success":
        return "Accessed"

    message = record.get("message", "").lower()

    if any(keyword in message for keyword in [
        "yt-dlp returned non-zero exit code",
        "unable to extract",
        "video unavailable"
    ]):
        return "Broken"

    if any(keyword in message for keyword in [
        "timeout", "connection", "network"
    ]):
        return "Temporary Issue"

    return "Unknown"


def extract_failure_reason(message: str) -> str:
    """Extract a short failure reason from the message."""
    # Simple extraction: take the first part before '->' or first 50 chars
    if "->" in message:
        return message.split("->")[0].strip()
    return message[:50] + "..." if len(message) > 50 else message


def generate_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics."""
    total_links = len(records)
    accessed_count = sum(1 for r in records if classify_status(r) == "Accessed")
    broken_count = sum(1 for r in records if classify_status(r) == "Broken")
    temporary_count = sum(1 for r in records if classify_status(r) == "Temporary Issue")

    return {
        "total_links": total_links,
        "accessed_count": accessed_count,
        "broken_count": broken_count,
        "temporary_count": temporary_count,
    }


def generate_platform_analysis(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Group by platform and count success/failure."""
    platform_stats = defaultdict(lambda: {"success": 0, "failure": 0})

    for record in records:
        platform = record.get("platform", "unknown")
        status = record.get("status", "failure")
        if status == "success":
            platform_stats[platform]["success"] += 1
        else:
            platform_stats[platform]["failure"] += 1

    return dict(platform_stats)


def generate_report(records: List[Dict[str, Any]]) -> str:
    """Generate the full report as a string."""
    summary = generate_summary(records)
    platform_analysis = generate_platform_analysis(records)

    report_lines = []

    # Summary Section
    report_lines.append("=== VIDEO ASSET PROCESSING REPORT ===\n")
    report_lines.append("SUMMARY:")
    report_lines.append(f"  Total Links Processed: {summary['total_links']}")
    report_lines.append(f"  Successfully Accessed: {summary['accessed_count']}")
    report_lines.append(f"  Broken Links: {summary['broken_count']}")
    report_lines.append(f"  Temporary Issues: {summary['temporary_count']}")
    report_lines.append("")

    # Detailed Per-Link Section
    report_lines.append("DETAILED RESULTS:")
    for i, record in enumerate(records, 1):
        final_status = classify_status(record)
        failure_reason = extract_failure_reason(record.get("message", "")) if final_status != "Accessed" else ""
        platform = record.get("platform", "unknown")
        url = record.get("url", "")
        timestamp = record.get("timestamp", "")

        report_lines.append(f"{i}. URL: {url}")
        report_lines.append(f"   Platform: {platform}")
        report_lines.append(f"   Status: {final_status}")
        if failure_reason:
            report_lines.append(f"   Reason: {failure_reason}")
        report_lines.append(f"   Timestamp: {timestamp}")
        report_lines.append("")

    # Platform Breakdown Section
    report_lines.append("PLATFORM BREAKDOWN:")
    for platform, stats in platform_analysis.items():
        report_lines.append(f"  {platform}:")
        report_lines.append(f"    Success: {stats['success']}")
        report_lines.append(f"    Failure: {stats['failure']}")
        report_lines.append("")

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="Generate report from JSONL log")
    parser.add_argument("--output", help="Output file path (default: print to console)")
    parser.add_argument("--logfile", default="logs/download_log.jsonl", help="Path to JSONL log file")

    args = parser.parse_args()

    log_path = Path(args.logfile)
    if not log_path.exists():
        print(f"Error: Log file {log_path} not found.")
        return

    records = load_jsonl(str(log_path))
    report = generate_report(records)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()