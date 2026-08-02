"""
dashboard.py — CLI monitoring report for Job Search Assistant.

Run from the project root:
    python Assets/dashboard.py

Prints a formatted summary of:
  - Overall search performance
  - Top searched job titles & locations
  - Zero-result queries (coverage gaps)
  - API health per service / endpoint
  - User engagement (chat session stats)
  - Recent errors
"""

import os
import sys

# Allow imports from Assets/ when run from project root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from monitor import monitor, DB_PATH

# ── Formatting helpers ─────────────────────────────────────────────────────────

W = 62  # report width


def _header(title: str) -> str:
    pad = (W - len(title) - 2) // 2
    return f"\n{'=' * W}\n{'=' * pad} {title} {'=' * (W - pad - len(title) - 2)}\n{'=' * W}"


def _row(label: str, value, width: int = 36) -> str:
    label_str = f"  {label}".ljust(width)
    return f"{label_str}: {value}"


def _bar(value: float, max_value: float, width: int = 20) -> str:
    """ASCII progress bar scaled to max_value."""
    if max_value <= 0:
        return "[" + " " * width + "]"
    filled = int(round(value / max_value * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _pct(num, denom) -> str:
    if not denom:
        return "N/A"
    return f"{100 * num / denom:.1f}%"


def _fmt_ms(ms) -> str:
    if ms is None:
        return "N/A"
    return f"{ms:,.1f} ms"


def _fmt_s(s) -> str:
    if s is None:
        return "N/A"
    minutes, seconds = divmod(int(s), 60)
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


# ── Section renderers ──────────────────────────────────────────────────────────

def _section_search(stats: dict) -> str:
    if not stats or not stats.get("total_searches"):
        return "\n  No search data yet.\n"

    total     = stats["total_searches"] or 0
    success   = stats["successful"] or 0
    no_res    = stats["no_results"] or 0
    errors    = stats["errors"] or 0

    lines = [
        _row("Total searches",          total),
        _row("Successful",              f"{success}  {_bar(success, total)}  {_pct(success, total)}"),
        _row("No results",              f"{no_res}   {_bar(no_res, total)}  {_pct(no_res, total)}"),
        _row("Errors",                  f"{errors}   {_bar(errors, total)}  {_pct(errors, total)}"),
        "",
        _row("Avg latency",             _fmt_ms(stats.get("avg_latency_ms"))),
        _row("Min latency",             _fmt_ms(stats.get("min_latency_ms"))),
        _row("Max latency",             _fmt_ms(stats.get("max_latency_ms"))),
        "",
        _row("Total results delivered", f"{stats.get('total_results_delivered', 0):,}"),
        _row("Unique titles searched",  stats.get("unique_titles_searched", 0)),
        _row("Unique locations searched", stats.get("unique_locations_searched", 0)),
    ]
    return "\n".join(lines)


def _section_top(items: list, label: str) -> str:
    if not items:
        return "\n  No data yet.\n"
    max_count = items[0]["count"] if items else 1
    lines = []
    for i, item in enumerate(items, 1):
        bar = _bar(item["count"], max_count, width=16)
        lines.append(f"  {i}. {item['value']:<30} {bar}  {item['count']} searches")
    return "\n".join(lines)


def _section_zero_results(items: list) -> str:
    if not items:
        return "\n  None — great coverage!\n"
    lines = ["  These searches never returned results (consider broadening):"]
    lines.append(f"  {'Title':<25} {'Location':<20} {'Attempts':>8}  {'Last Seen'}")
    lines.append("  " + "-" * 60)
    for item in items:
        lines.append(
            f"  {item['job_title'][:24]:<25} {item['location'][:19]:<20}"
            f"  {item['attempts']:>7}  {item['last_attempt'][:16]}"
        )
    return "\n".join(lines)


def _section_api_health(rows: list) -> str:
    if not rows:
        return "\n  No API call data yet.\n"
    lines = [
        f"  {'Service':<10} {'Endpoint':<20} {'Calls':>6} {'Success%':>9} "
        f"{'Avg ms':>8} {'Max ms':>8} {'Retries':>8}",
        "  " + "-" * 68,
    ]
    for r in rows:
        lines.append(
            f"  {r['service']:<10} {r['endpoint']:<20} "
            f"{r['total_calls']:>6} {str(r['success_rate_pct']) + '%':>9} "
            f"{_fmt_ms(r['avg_latency_ms']):>8} {_fmt_ms(r['max_latency_ms']):>8} "
            f"{r['total_retries']:>8}"
        )
    return "\n".join(lines)


def _section_sessions(stats: dict) -> str:
    if not stats or not stats.get("total_sessions"):
        return "\n  No session data yet.\n"
    lines = [
        _row("Total sessions",          stats.get("total_sessions", 0)),
        _row("Avg session duration",    _fmt_s(stats.get("avg_duration_s"))),
        _row("Avg messages / session",  stats.get("avg_messages", "N/A")),
        _row("Avg job searches / session", stats.get("avg_tool_calls", "N/A")),
        "",
        _row("Total messages sent",     f"{stats.get('total_messages', 0):,}"),
        _row("Total job searches run",  f"{stats.get('total_tool_calls', 0):,}"),
        _row("Total LLM errors",        stats.get("total_errors", 0)),
    ]
    return "\n".join(lines)


def _section_errors(errors: list) -> str:
    if not errors:
        return "\n  No errors recorded.\n"
    lines = [
        f"  {'Timestamp':<22} {'Source':<12} {'Context':<28} Error Type",
        "  " + "-" * 72,
    ]
    for e in errors:
        lines.append(
            f"  {str(e['ts'])[:19]:<22} {str(e['source'])[:11]:<12} "
            f"{str(e['context'])[:27]:<28} {e['error_type'] or 'unknown'}"
        )
    return "\n".join(lines)


# ── Main render ────────────────────────────────────────────────────────────────

def print_dashboard() -> None:
    if not os.path.exists(DB_PATH):
        print(f"\n[!] No metrics database found at {DB_PATH}")
        print("    Run the chatbot or scraper first to generate data.\n")
        return

    data = monitor.get_summary()
    if not data:
        print("\n[!] Could not read metrics. Check logs/api_errors.log for details.\n")
        return

    print(_header("JOB SEARCH ASSISTANT — MONITORING DASHBOARD"))
    print(f"  Database : {DB_PATH}")
    print(f"  Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(_header("SEARCH PERFORMANCE"))
    print(_section_search(data.get("search_stats", {})))

    print(_header("TOP 5 JOB TITLES SEARCHED"))
    print(_section_top(data.get("top_titles", []), "title"))

    print(_header("TOP 5 LOCATIONS SEARCHED"))
    print(_section_top(data.get("top_locations", []), "location"))

    print(_header("ZERO-RESULT QUERIES  (coverage gaps)"))
    print(_section_zero_results(data.get("zero_result_queries", [])))

    print(_header("API HEALTH"))
    print(_section_api_health(data.get("api_health", [])))

    print(_header("USER ENGAGEMENT  (chat sessions)"))
    print(_section_sessions(data.get("session_stats", {})))

    print(_header("RECENT ERRORS  (last 10)"))
    print(_section_errors(data.get("recent_errors", [])))

    print("\n" + "=" * W + "\n")


if __name__ == "__main__":
    print_dashboard()
