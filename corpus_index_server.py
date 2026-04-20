"""Ground Wire Corpus Index Server v2 — Lightweight JSON-backed MCP server.

Serves structured metadata lookups for 697 Treasury Bulletin files.
Replaces the 82MB SQLite/FTS5 server with a ~3.7MB JSON index loaded in memory.

Tools:
  - search_files_by_topic: Find files by topic or keyword
  - find_tables: Find tables by code or name pattern
  - get_files_for_period: Get files for a year/month/fiscal year
  - get_file_info: Get all tables and metadata for a specific file

Usage:
    python3 mcp/corpus_index_server.py
"""

import json
import sys
import os
from pathlib import Path

# --- Load index ---

INDEX_PATH = os.environ.get(
    "CORPUS_INDEX_PATH",
    str(Path(__file__).parent / "corpus_index.json")
)

with open(INDEX_PATH) as f:
    INDEX = json.load(f)

FILES = INDEX["files"]
TEMPORAL = INDEX["temporal"]
TABLE_CODES = INDEX["table_codes"]
TABLE_NAMES = INDEX["table_names"]  # {file: [[line, code, name], ...]}
KEYWORDS = INDEX["keywords"]
TOPICS = INDEX["topics"]


# --- Tool handlers ---

def search_files_by_topic(args):
    """Find files by topic name or keyword."""
    topic = args.get("topic", "").lower().strip()
    keyword = args.get("keyword", "").lower().strip()
    limit = args.get("limit", 20)

    results = set()

    # Check topic definitions
    if topic:
        for tname, tdef in TOPICS.items():
            if topic in tname or any(topic in kw for kw in tdef["keywords"]):
                # Return files that have any of this topic's table codes
                for code in tdef["codes"]:
                    if code in TABLE_CODES:
                        for entry in TABLE_CODES[code]:
                            results.add(entry["file"])

    # Check keyword index — match any word in the search term
    search_term = keyword or topic
    if search_term:
        search_words = search_term.lower().split()
        for kw, files in KEYWORDS.items():
            if any(w in kw for w in search_words):
                results.update(files)

    if not results:
        return f"No files found for topic='{topic}' keyword='{keyword}'"

    # Sort by year descending (most recent first)
    sorted_files = sorted(results, key=lambda f: (FILES.get(f, {}).get("year", 0), f), reverse=True)[:limit]

    lines = [f"Found {len(results)} files (showing {len(sorted_files)}):"]
    for fname in sorted_files:
        meta = FILES.get(fname, {})
        lines.append(f"  {fname}  (year={meta.get('year')}, month={meta.get('month')}, tables={meta.get('table_count', '?')})")

    return "\n".join(lines)


def find_tables(args):
    """Find tables by code or name pattern, optionally filtered by year."""
    code = args.get("code", "").upper().strip()
    pattern = args.get("pattern", "").lower().strip()
    year = args.get("year")
    limit = args.get("limit", 20)

    results = []

    # Direct code lookup
    if code:
        entries = TABLE_CODES.get(code, [])
        for entry in entries:
            if year and FILES.get(entry["file"], {}).get("year") != year:
                continue
            # Look up table name from table_names
            name = ""
            for t in TABLE_NAMES.get(entry["file"], []):
                if t[0] == entry["line"]:
                    name = t[2]
                    break
            results.append({
                "file": entry["file"],
                "line": entry["line"],
                "code": code,
                "name": name
            })

    # Pattern search across table names
    if pattern and not results:
        for fname, tables in TABLE_NAMES.items():
            if year and FILES.get(fname, {}).get("year") != year:
                continue
            for t in tables:
                line_num, tcode, tname = t
                if pattern in tname.lower():
                    results.append({
                        "file": fname,
                        "line": line_num,
                        "code": tcode or "",
                        "name": tname
                    })

    if not results:
        return f"No tables found for code='{code}' pattern='{pattern}' year={year}"

    results = sorted(results, key=lambda r: (r["file"], r["line"]))[:limit]

    lines = [f"Found {len(results)} table(s):"]
    for r in results:
        lines.append(f"  {r['file']} line {r['line']}: [{r['code']}] {r['name']}")

    return "\n".join(lines)


def get_files_for_period(args):
    """Get files covering a specific time period."""
    year = args.get("year")
    month = args.get("month")
    fiscal_year = args.get("fiscal_year")

    if fiscal_year:
        # Fiscal year end: June 30 before 1976, Sept 30 after 1976
        fy = int(fiscal_year)
        if fy <= 1976:
            # FY ends June 30 — summary in June or next quarterly issue
            target_years = [str(fy - 1), str(fy)]
        else:
            # FY ends Sept 30 — summary in September or December issue
            target_years = [str(fy - 1), str(fy)]

        results = []
        for ty in target_years:
            results.extend(TEMPORAL.get(ty, []))

        fy_note = f"FY{fy} ends {'June 30' if fy <= 1976 else 'Sept 30'}."
        if fy <= 1976:
            fy_note += f" Look for the June {fy} or next available bulletin."
        else:
            fy_note += f" Look for the September {fy} or December {fy} bulletin."

        lines = [f"Fiscal Year {fy}: {fy_note}", f"Files from {target_years[0]}-{target_years[1]}:"]
        for fname in sorted(results):
            meta = FILES.get(fname, {})
            lines.append(f"  {fname}  (month={meta.get('month')})")
        return "\n".join(lines)

    if year:
        files = TEMPORAL.get(str(year), [])
        if not files:
            return f"No files found for year {year}"

        if month:
            # Filter to specific month
            filtered = [f for f in files if FILES.get(f, {}).get("month") == int(month)]
            if filtered:
                files = filtered
            else:
                # Find nearest month
                lines = [f"No exact match for {year}-{month:02d}. Available files for {year}:"]
                for fname in files:
                    meta = FILES.get(fname, {})
                    lines.append(f"  {fname}  (month={meta.get('month')}, era={meta.get('era')})")
                era = FILES.get(files[0], {}).get("era", "unknown")
                if era == "quarterly":
                    lines.append(f"\nNote: Post-1983 bulletins are quarterly (Mar, Jun, Sep, Dec).")
                return "\n".join(lines)

        lines = [f"Files for {year}" + (f" month {month}" if month else "") + ":"]
        for fname in sorted(files):
            meta = FILES.get(fname, {})
            lines.append(f"  {fname}  (month={meta.get('month')}, era={meta.get('era')}, tables={meta.get('table_count', '?')})")
        return "\n".join(lines)

    return "Please specify year, month, or fiscal_year."


def get_file_info(args):
    """Get metadata and table listing for a specific file."""
    filename = args.get("filename", "")

    meta = FILES.get(filename)
    if not meta:
        # Try fuzzy match
        matches = [f for f in FILES if filename.lower() in f.lower()]
        if matches:
            return f"File not found: '{filename}'. Did you mean: {', '.join(matches[:5])}"
        return f"File not found: '{filename}'"

    lines = [
        f"File: {filename}",
        f"Year: {meta['year']}, Month: {meta['month']}, Era: {meta['era']}",
        f"Lines: {meta['lines']}, Tables: {meta['table_count']}",
        ""
    ]

    tables = TABLE_NAMES.get(filename, [])
    if tables:
        lines.append("Tables (coded):")
        for t in sorted(tables, key=lambda x: x[0]):
            line_num, code, name = t
            lines.append(f"  Line {line_num}: [{code}] {name}")
    else:
        lines.append("No coded tables found. Use grep to search this file.")

    return "\n".join(lines)


# --- MCP Protocol ---

TOOLS = [
    {
        "name": "search_files_by_topic",
        "description": "Find Treasury Bulletin files by topic or keyword. Topics include: fiscal_operations, federal_debt, public_debt_operations, ownership, treasury_account, international, capital_movements, currency, savings_bonds, exchange_stabilization. You can also search by any keyword (e.g., 'savings bonds', 'public debt', 'receipts').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic name (e.g., 'federal_debt', 'international')"},
                "keyword": {"type": "string", "description": "Keyword to search (e.g., 'savings bonds', 'receipts')"},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20}
            }
        }
    },
    {
        "name": "find_tables",
        "description": "Find specific tables by code (e.g., 'FFO-1', 'FD-3', 'IFS-2') or by name pattern. Returns file, line number, and table name. Use this to jump directly to a table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Table code (e.g., 'FFO-1', 'FD-3')"},
                "pattern": {"type": "string", "description": "Table name pattern (e.g., 'savings bonds', 'debt subject')"},
                "year": {"type": "integer", "description": "Filter by bulletin year"},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20}
            }
        }
    },
    {
        "name": "get_files_for_period",
        "description": "Get bulletin files for a specific time period. Handles calendar years, months, and fiscal years (FY ends June 30 pre-1976, Sept 30 post-1976). Note: bulletins are monthly before 1983, quarterly after.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Calendar year (e.g., 1985)"},
                "month": {"type": "integer", "description": "Calendar month (1-12)"},
                "fiscal_year": {"type": "integer", "description": "Fiscal year (e.g., 1985)"}
            }
        }
    },
    {
        "name": "get_file_info",
        "description": "Get metadata and table listing for a specific bulletin file. Returns year, month, era, line count, and all coded tables with line numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Bulletin filename (e.g., 'treasury_bulletin_2011_09.txt')"}
            },
            "required": ["filename"]
        }
    }
]

HANDLERS = {
    "search_files_by_topic": search_files_by_topic,
    "find_tables": find_tables,
    "get_files_for_period": get_files_for_period,
    "get_file_info": get_file_info,
}


def send(msg):
    out = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(out)}\r\n\r\n{out}")
    sys.stdout.flush()


def main():
    buf = b""
    while True:
        chunk = sys.stdin.buffer.read(1)
        if not chunk:
            break
        buf += chunk

        if b"\r\n\r\n" not in buf:
            continue

        header, rest = buf.split(b"\r\n\r\n", 1)
        length = int(header.split(b"Content-Length: ")[1])

        while len(rest) < length:
            rest += sys.stdin.buffer.read(length - len(rest))

        body = rest[:length]
        buf = rest[length:]

        msg = json.loads(body)
        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "corpus-index",
                        "version": "2.0.0",
                    },
                },
            })

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS},
            })

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = HANDLERS.get(tool_name)
            if handler:
                try:
                    result_text = handler(arguments)
                    send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {"content": [{"type": "text", "text": result_text}]},
                    })
                except Exception as e:
                    send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {"content": [{"type": "text", "text": f"Error: {e}"}]},
                    })
            else:
                send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                })

        elif msg_id is not None:
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            })


if __name__ == "__main__":
    main()
