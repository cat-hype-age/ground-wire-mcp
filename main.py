"""Ground Wire MCP Server — Dedalus deployment.

Corpus index + external data tools for the OfficeQA competition.
Provides structured access to 697 Treasury Bulletin files and
external reference data (CPI-U, exchange rates).
"""

import asyncio
import json
import os
from pathlib import Path

from dedalus_mcp import MCPServer, tool

server = MCPServer("ground-wire-tools")

# ---------------------------------------------------------------------------
# Corpus Index Data
# ---------------------------------------------------------------------------

INDEX_PATH = os.environ.get(
    "CORPUS_INDEX_PATH",
    str(Path(__file__).parent / "corpus_index.json")
)

try:
    with open(INDEX_PATH) as f:
        INDEX = json.load(f)
    FILES = INDEX["files"]
    TEMPORAL = INDEX["temporal"]
    TABLE_CODES = INDEX["table_codes"]
    TABLE_NAMES = INDEX["table_names"]
    KEYWORDS = INDEX["keywords"]
    TOPICS = INDEX["topics"]
    CORPUS_INDEX_LOADED = True
except Exception as e:
    print(f"Warning: Could not load corpus index: {e}")
    FILES, TEMPORAL, TABLE_CODES, TABLE_NAMES, KEYWORDS, TOPICS = {}, {}, {}, {}, {}, {}
    CORPUS_INDEX_LOADED = False

# ---------------------------------------------------------------------------
# CPI-U Data
# ---------------------------------------------------------------------------

CPI_ANNUAL = {
    1939: 13.9, 1940: 14.0, 1941: 14.7, 1942: 16.3, 1943: 17.3,
    1944: 17.6, 1945: 18.0, 1946: 19.5, 1947: 22.3, 1948: 24.1,
    1949: 23.8, 1950: 24.1, 1951: 26.0, 1952: 26.5, 1953: 26.7,
    1954: 26.9, 1955: 26.8, 1956: 27.2, 1957: 28.1, 1958: 28.9,
    1959: 29.1, 1960: 29.6, 1961: 29.9, 1962: 30.2, 1963: 30.6,
    1964: 31.0, 1965: 31.5, 1966: 32.4, 1967: 33.4, 1968: 34.8,
    1969: 36.7, 1970: 38.8, 1971: 40.5, 1972: 41.8, 1973: 44.4,
    1974: 49.3, 1975: 53.8, 1976: 56.9, 1977: 60.6, 1978: 65.2,
    1979: 72.6, 1980: 82.4, 1981: 90.9, 1982: 96.5, 1983: 99.6,
    1984: 103.9, 1985: 107.6, 1986: 109.6, 1987: 113.6, 1988: 118.3,
    1989: 124.0, 1990: 130.7, 1991: 136.2, 1992: 140.3, 1993: 144.5,
    1994: 148.2, 1995: 152.4, 1996: 156.9, 1997: 160.5, 1998: 163.0,
    1999: 166.6, 2000: 172.2, 2001: 177.1, 2002: 179.9, 2003: 184.0,
    2004: 188.9, 2005: 195.3, 2006: 201.6, 2007: 207.3, 2008: 215.3,
    2009: 214.5, 2010: 218.1, 2011: 224.9, 2012: 229.6, 2013: 233.0,
    2014: 236.7, 2015: 237.0, 2016: 240.0, 2017: 245.1, 2018: 251.1,
    2019: 255.7, 2020: 258.8, 2021: 270.9, 2022: 292.7, 2023: 304.7,
    2024: 313.5, 2025: 320.2,
}

CPI_MONTHLY = {
    1946: {1: 18.2, 2: 18.2, 3: 18.3, 4: 18.4, 5: 18.5, 6: 18.7,
           7: 20.0, 8: 20.4, 9: 20.4, 10: 20.8, 11: 21.2, 12: 21.5},
    1947: {1: 21.5, 2: 21.5, 3: 21.9, 4: 21.9, 5: 21.9, 6: 22.0,
           7: 22.2, 8: 22.5, 9: 23.0, 10: 23.0, 11: 23.1, 12: 23.4},
    1948: {1: 23.7, 2: 23.5, 3: 23.4, 4: 23.8, 5: 23.9, 6: 24.1,
           7: 24.4, 8: 24.5, 9: 24.5, 10: 24.4, 11: 24.2, 12: 24.1},
    1949: {1: 24.0, 2: 23.8, 3: 23.8, 4: 23.9, 5: 23.8, 6: 23.9,
           7: 23.7, 8: 23.7, 9: 23.9, 10: 23.7, 11: 23.8, 12: 23.5},
    1969: {1: 34.1, 2: 34.2, 3: 34.5, 4: 34.7, 5: 34.9, 6: 35.2,
           7: 35.4, 8: 35.6, 9: 35.8, 10: 36.0, 11: 36.3, 12: 36.6},
    1979: {1: 68.3, 2: 69.1, 3: 69.8, 4: 70.6, 5: 71.5, 6: 72.3,
           7: 73.1, 8: 73.8, 9: 74.6, 10: 75.2, 11: 75.9, 12: 76.7},
    1980: {1: 77.8, 2: 78.9, 3: 80.1, 4: 81.0, 5: 81.8, 6: 82.7,
           7: 82.7, 8: 83.3, 9: 84.0, 10: 84.8, 11: 85.5, 12: 86.3},
    1981: {1: 87.0, 2: 87.9, 3: 88.5, 4: 89.1, 5: 89.8, 6: 90.6,
           7: 91.6, 8: 92.3, 9: 93.2, 10: 93.4, 11: 93.7, 12: 94.0},
}

# ---------------------------------------------------------------------------
# Exchange Rate Data
# ---------------------------------------------------------------------------

USD_GBP = {
    1939: 4.03, 1940: 3.83, 1941: 4.03, 1942: 4.03, 1943: 4.03,
    1944: 4.03, 1945: 4.03, 1946: 4.03, 1947: 4.03, 1948: 4.03,
    1949: 3.69, 1950: 2.80, 1951: 2.80, 1952: 2.80, 1953: 2.81,
    1954: 2.81, 1955: 2.79, 1956: 2.80, 1957: 2.79, 1958: 2.81,
    1959: 2.81, 1960: 2.81, 1961: 2.80, 1962: 2.81, 1963: 2.80,
    1964: 2.79, 1965: 2.80, 1966: 2.79, 1967: 2.75, 1968: 2.39,
    1969: 2.39, 1970: 2.40, 1971: 2.44, 1972: 2.50, 1973: 2.45,
    1974: 2.34, 1975: 2.22, 1976: 1.805, 1977: 1.745, 1978: 1.919,
    1979: 2.122, 1980: 2.325, 1981: 2.025, 1982: 1.749, 1983: 1.516,
    1984: 1.337, 1985: 1.298, 1990: 1.784, 1991: 1.767, 1992: 1.766,
    1993: 1.502, 1994: 1.532, 1995: 1.578, 1996: 1.561, 2000: 1.516,
    2001: 1.440, 2002: 1.503, 2005: 1.820, 2010: 1.546, 2015: 1.529,
    2016: 1.356,
}

USD_DEM = {
    1960: 0.238, 1965: 0.250, 1970: 0.274, 1971: 0.289, 1972: 0.313,
    1973: 0.374, 1974: 0.382, 1975: 0.407, 1976: 0.397, 1977: 0.431,
    1978: 0.495, 1979: 0.546, 1980: 0.553, 1985: 0.338,
}

INR_USD = {
    1960: 4.76, 1961: 4.76, 1962: 4.76, 1963: 4.76, 1964: 4.76,
    1965: 4.76, 1966: 6.36, 1970: 7.50, 1975: 8.38, 1980: 7.86,
    1985: 12.37, 1990: 17.50, 1995: 32.43, 2000: 44.94,
}

JPY_USD = {
    1960: 360.0, 1970: 360.0, 1975: 296.8, 1980: 226.7, 1985: 238.5,
    1990: 144.8, 1995: 94.1, 2000: 107.8, 2004: 108.2, 2010: 87.8,
    2015: 121.0, 2016: 108.8, 2020: 106.8, 2025: 149.3,
}

CAD_USD = {
    1955: 1.01, 1959: 1.04, 1960: 1.03, 1965: 1.08, 1970: 1.04,
    1975: 1.017, 1980: 1.169, 1985: 1.366, 1990: 1.167, 2000: 1.485,
}

EXCHANGE_RATES = {
    "USD/GBP": {"data": USD_GBP, "description": "US Dollars per British Pound", "direction": "USD per 1 GBP"},
    "USD/DEM": {"data": USD_DEM, "description": "US Dollars per Deutsche Mark", "direction": "USD per 1 DEM"},
    "INR/USD": {"data": INR_USD, "description": "Indian Rupees per US Dollar", "direction": "INR per 1 USD"},
    "JPY/USD": {"data": JPY_USD, "description": "Japanese Yen per US Dollar", "direction": "JPY per 1 USD"},
    "CAD/USD": {"data": CAD_USD, "description": "Canadian Dollars per US Dollar", "direction": "CAD per 1 USD"},
}

FX_ALIASES = {
    "GBP": "USD/GBP", "POUND": "USD/GBP", "STERLING": "USD/GBP",
    "GBP/USD": "USD/GBP", "USDGBP": "USD/GBP",
    "DEM": "USD/DEM", "MARK": "USD/DEM", "DEUTSCHEMARK": "USD/DEM",
    "DEM/USD": "USD/DEM", "USDDEM": "USD/DEM",
    "INR": "INR/USD", "RUPEE": "INR/USD", "INRUSD": "INR/USD",
    "USD/INR": "INR/USD",
    "JPY": "JPY/USD", "YEN": "JPY/USD", "JPYUSD": "JPY/USD",
    "USD/JPY": "JPY/USD",
    "CAD": "CAD/USD", "CADUSD": "CAD/USD", "USD/CAD": "CAD/USD",
}


# ---------------------------------------------------------------------------
# Corpus Index Tools
# ---------------------------------------------------------------------------

@tool(description="Find Treasury Bulletin files by topic or keyword. Topics: fiscal_operations, federal_debt, public_debt_operations, ownership, treasury_account, international, capital_movements, currency, savings_bonds, exchange_stabilization.")
def search_files_by_topic(topic: str = "", keyword: str = "", limit: int = 20) -> str:
    results = set()
    if topic:
        for tname, tdef in TOPICS.items():
            if topic.lower() in tname or any(topic.lower() in kw for kw in tdef["keywords"]):
                for code in tdef["codes"]:
                    if code in TABLE_CODES:
                        for entry in TABLE_CODES[code]:
                            results.add(entry["file"])
    search_term = keyword or topic
    if search_term:
        search_words = search_term.lower().split()
        for kw, files in KEYWORDS.items():
            if any(w in kw for w in search_words):
                results.update(files)
    if not results:
        return f"No files found for topic='{topic}' keyword='{keyword}'"
    sorted_files = sorted(results, key=lambda f: (FILES.get(f, {}).get("year", 0), f), reverse=True)[:limit]
    lines = [f"Found {len(results)} files (showing {len(sorted_files)}):"]
    for fname in sorted_files:
        meta = FILES.get(fname, {})
        lines.append(f"  {fname}  (year={meta.get('year')}, month={meta.get('month')}, tables={meta.get('table_count', '?')})")
    return "\n".join(lines)


@tool(description="Find tables by code (e.g., 'FFO-1', 'FD-3') or by name pattern. Returns file, line number, and table name.")
def find_tables(code: str = "", pattern: str = "", year: int = 0, limit: int = 20) -> str:
    results = []
    if code:
        code_upper = code.upper().strip()
        entries = TABLE_CODES.get(code_upper, [])
        for entry in entries:
            if year and FILES.get(entry["file"], {}).get("year") != year:
                continue
            name = ""
            for t in TABLE_NAMES.get(entry["file"], []):
                if t[0] == entry["line"]:
                    name = t[2]
                    break
            results.append({"file": entry["file"], "line": entry["line"], "code": code_upper, "name": name})
    if pattern and not results:
        pat = pattern.lower().strip()
        for fname, tables in TABLE_NAMES.items():
            if year and FILES.get(fname, {}).get("year") != year:
                continue
            for t in tables:
                line_num, tcode, tname = t
                if pat in tname.lower():
                    results.append({"file": fname, "line": line_num, "code": tcode or "", "name": tname})
    if not results:
        return f"No tables found for code='{code}' pattern='{pattern}' year={year}"
    results = sorted(results, key=lambda r: (r["file"], r["line"]))[:limit]
    lines = [f"Found {len(results)} table(s):"]
    for r in results:
        lines.append(f"  {r['file']} line {r['line']}: [{r['code']}] {r['name']}")
    return "\n".join(lines)


@tool(description="Get bulletin files for a specific time period. Handles calendar years, months, and fiscal years (FY ends June 30 pre-1976, Sept 30 post-1976).")
def get_files_for_period(year: int = 0, month: int = 0, fiscal_year: int = 0) -> str:
    if fiscal_year:
        fy = fiscal_year
        target_years = [str(fy - 1), str(fy)]
        results = []
        for ty in target_years:
            results.extend(TEMPORAL.get(ty, []))
        fy_note = f"FY{fy} ends {'June 30' if fy <= 1976 else 'Sept 30'}."
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
            filtered = [f for f in files if FILES.get(f, {}).get("month") == month]
            if filtered:
                files = filtered
        lines = [f"Files for {year}" + (f" month {month}" if month else "") + ":"]
        for fname in sorted(files):
            meta = FILES.get(fname, {})
            lines.append(f"  {fname}  (month={meta.get('month')}, era={meta.get('era')}, tables={meta.get('table_count', '?')})")
        return "\n".join(lines)
    return "Please specify year, month, or fiscal_year."


@tool(description="Get metadata and table listing for a specific bulletin file.")
def get_file_info(filename: str) -> str:
    meta = FILES.get(filename)
    if not meta:
        matches = [f for f in FILES if filename.lower() in f.lower()]
        if matches:
            return f"File not found: '{filename}'. Did you mean: {', '.join(matches[:5])}"
        return f"File not found: '{filename}'"
    lines = [f"File: {filename}", f"Year: {meta['year']}, Month: {meta['month']}, Era: {meta['era']}", f"Lines: {meta['lines']}, Tables: {meta['table_count']}", ""]
    tables = TABLE_NAMES.get(filename, [])
    if tables:
        lines.append("Tables (coded):")
        for t in sorted(tables, key=lambda x: x[0]):
            line_num, code, name = t
            lines.append(f"  Line {line_num}: [{code}] {name}")
    else:
        lines.append("No coded tables found.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# External Data Tools
# ---------------------------------------------------------------------------

@tool(description="Look up CPI-U (Consumer Price Index, 1982-84=100, NSA) for a given year. Monthly data available for: 1946-1949, 1969, 1979-1981.")
def lookup_cpi(year: int, month: int = 0) -> str:
    if month:
        monthly = CPI_MONTHLY.get(year)
        if monthly and month in monthly:
            return f"CPI-U for {year}-{month:02d}: {monthly[month]}\n(BLS, U.S. City Average, 1982-84=100, NSA)"
        elif year in CPI_ANNUAL:
            return f"No monthly data for {year}-{month:02d}.\nAnnual average CPI-U for {year}: {CPI_ANNUAL[year]}\nMonthly data available for: {sorted(CPI_MONTHLY.keys())}"
        else:
            return f"No CPI data for year {year}. Range: 1939-2025."
    if year in CPI_ANNUAL:
        result = f"Annual average CPI-U for {year}: {CPI_ANNUAL[year]}\n(BLS, U.S. City Average, 1982-84=100, NSA)"
        if year in CPI_MONTHLY:
            monthly = CPI_MONTHLY[year]
            result += f"\nMonthly: {', '.join(f'{m}={v}' for m, v in sorted(monthly.items()))}"
        return result
    return f"No CPI data for year {year}. Range: 1939-2025."


@tool(description="Look up historical exchange rate. Pairs: USD/GBP, USD/DEM, INR/USD, JPY/USD, CAD/USD. Also accepts: GBP, YEN, RUPEE, etc.")
def lookup_exchange_rate(pair: str, year: int = 0) -> str:
    normalized = FX_ALIASES.get(pair.upper().replace(" ", ""), pair.upper().replace(" ", ""))
    rate_info = EXCHANGE_RATES.get(normalized)
    if not rate_info:
        return f"Unknown currency pair: '{pair}'. Available: {list(EXCHANGE_RATES.keys())}"
    data = rate_info["data"]
    if year:
        if year in data:
            return f"{normalized} for {year}: {data[year]}\n({rate_info['description']} — {rate_info['direction']})"
        years = sorted(data.keys())
        before = [y for y in years if y <= year]
        after = [y for y in years if y >= year]
        nearest = []
        if before:
            nearest.append(f"{before[-1]}: {data[before[-1]]}")
        if after:
            nearest.append(f"{after[0]}: {data[after[0]]}")
        return f"No exact rate for {normalized} in {year}.\nNearest: {', '.join(nearest)}\nAll years: {years}"
    lines = [f"{normalized} — {rate_info['description']}:"]
    for y in sorted(data.keys()):
        lines.append(f"  {y}: {data[y]}")
    return "\n".join(lines)


@tool(description="Compute inflation-adjusted value between two years using CPI-U. Formula: value * (CPI_to / CPI_from).")
def inflation_adjust(value: float, from_year: int, to_year: int) -> str:
    if from_year not in CPI_ANNUAL:
        return f"No CPI data for from_year {from_year}. Range: 1939-2025."
    if to_year not in CPI_ANNUAL:
        return f"No CPI data for to_year {to_year}. Range: 1939-2025."
    from_cpi = CPI_ANNUAL[from_year]
    to_cpi = CPI_ANNUAL[to_year]
    adjusted = value * (to_cpi / from_cpi)
    return f"${value:,.2f} in {from_year} dollars = ${adjusted:,.2f} in {to_year} dollars\nFormula: {value} * ({to_cpi} / {from_cpi}) = {adjusted:.2f}"


# ---------------------------------------------------------------------------
# Register all tools and serve
# ---------------------------------------------------------------------------

server.collect(
    search_files_by_topic,
    find_tables,
    get_files_for_period,
    get_file_info,
    lookup_cpi,
    lookup_exchange_rate,
    inflation_adjust,
)

if __name__ == "__main__":
    asyncio.run(server.serve())
