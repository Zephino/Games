#!/usr/bin/env python3
"""
verify_claims.py — Domain-Agnostic Deterministic Claim & [TBD] Verifier
=======================================================================
Decouples neural text/doc generation from symbolic literal verification across
any engineering specialty (mechanical/CAD, electronics/firmware, structured
cabling/BOMs, software, and GitHub/Discord technical writing).

Checks --target against --sources (zero external dependencies):
  1. Dimensioned quantities, percentages, Shore hardnesses, numeric ranges,
     and spelled-out number+unit phrases ("two-meter", "50 to 70 grams").
  2. Engineering designators (metric/imperial fasteners M3x8mm <-> M3x8,
     cabling/fiber Cat6A/OS2/OM4, adhesives Loctite 243, part keys TPN*/BF*).
  3. Backticked file/asset/code/coordinate literals (`*.stl`, `*.xlsx`,
     `*.cfg`, `D33:I34`, `PF7`, `SET_PNEUMA_MODE`).
  4. Explicit `[TBD: ...]` / `[UNVERIFIED ...]` abstention markers (inventoried
     cleanly as Open Offenders rather than hidden) and `[CALC: ...]` AST math.
  5. Source Provenance & Anti-Circularity checks (blocks `--target` == `--sources`
     and flags dirty Git working-tree edits, unreceipted AI prose, or `[TBD]`s
     inside `--sources` so the agent & user choose to Skip vs. Work in Parallel).
  6. Cryptographic SHA-256 Proof-of-Verification Receipt (`VRF-<12hex>`).

Exit codes:
  0 — PASS (0 unbacked claims; open [TBD] markers allowed unless --fail-on-tbd)
  1 — FAIL (1 or more unbacked claims detected, circular source, or missing file)
  2 — TBD_BLOCK (--fail-on-tbd set and >=1 open [TBD] marker remains)
  3 — PROVENANCE_BLOCK (--strict-provenance set and >=1 suspect --sources file)
"""

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Set, Tuple

TEXT_EXTENSIONS = {
    ".md", ".txt", ".cfg", ".conf", ".ini", ".toml", ".yaml", ".yml",
    ".json", ".csv", ".tsv", ".py", ".sh", ".js", ".ts", ".c", ".h",
    ".cpp", ".hpp", ".xml", ".html", ".svg",
}

WORD_NUMBERS: Dict[str, float] = {
    "zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0,
    "five": 5.0, "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0,
    "ten": 10.0, "eleven": 11.0, "twelve": 12.0, "thirteen": 13.0,
    "fourteen": 14.0, "fifteen": 15.0, "sixteen": 16.0, "seventeen": 17.0,
    "eighteen": 18.0, "nineteen": 19.0, "twenty": 20.0, "thirty": 30.0,
    "forty": 40.0, "fifty": 50.0, "sixty": 60.0, "seventy": 70.0,
    "eighty": 80.0, "ninety": 90.0, "hundred": 100.0,
}

UNIT_ALIASES: Dict[str, str] = {
    # Length / Area / Volume / Flow
    "nm_len": "nm_len", "um": "um", "µm": "um", "micrometer": "um", "micrometers": "um", "micron": "um", "microns": "um",
    "mm": "mm", "millimeter": "mm", "millimeters": "mm", "millimetre": "mm", "millimetres": "mm",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm",
    "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "km": "km", "kilometer": "km", "kilometers": "km",
    "mil": "mil", "mils": "mil",
    "in": "in", "inch": "in", "inches": "in",
    "ft": "ft", "foot": "ft", "feet": "ft",
    "yd": "yd", "yard": "yd", "yards": "yd",
    "cm3": "cm3", "cm³": "cm3", "mm3": "mm3", "mm³": "mm3",
    "l": "l", "liter": "l", "liters": "l", "ml": "ml", "milliliter": "ml", "milliliters": "ml",
    "l/min": "l/min", "lpm": "l/min", "cfm": "cfm", "scfm": "scfm",
    # Mass / Force / Torque / Pressure
    "mg": "mg", "milligram": "mg", "milligrams": "mg",
    "g": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "n": "n", "kn": "kn",
    "nm": "nm", "n·m": "nm", "n-m": "nm",
    "in-lb": "in-lb", "in-lbs": "in-lb", "ft-lb": "ft-lb", "ft-lbs": "ft-lb",
    "pa": "pa", "kpa": "kpa", "mpa": "mpa", "gpa": "gpa",
    "bar": "bar", "mbar": "mbar", "psi": "psi",
    # Thermal / Angle
    "°c": "degc", "degc": "degc", "celsius": "degc",
    "°f": "degf", "degf": "degf", "fahrenheit": "degf",
    "°": "deg", "deg": "deg", "degree": "deg", "degrees": "deg",
    # Electrical / Electronic / RF
    "v": "v", "volt": "v", "volts": "v", "vdc": "v", "vac": "v",
    "mv": "mv", "millivolt": "mv", "millivolts": "mv", "kv": "kv",
    "a": "a", "amp": "a", "amps": "a", "ampere": "a", "amperes": "a",
    "ma": "ma", "milliamp": "ma", "milliamps": "ma", "ua": "ua", "µa": "ua",
    "w": "w", "watt": "w", "watts": "w", "mw": "mw", "kw": "kw", "va": "va",
    "wh": "wh", "mah": "mah", "ah": "ah",
    "Ω": "ohm", "ω": "ohm", "ohm": "ohm", "ohms": "ohm",
    "mΩ": "mohm", "mohm": "mohm", "kΩ": "kohm", "kohm": "kohm", "kohms": "kohm", "MΩ": "megohm", "megohm": "megohm",
    "pf": "pf", "nf": "nf", "uf": "uf", "µf": "uf",
    "uh": "uh", "µh": "uh", "mh": "mh",
    "hz": "hz", "khz": "khz", "mhz": "mhz", "ghz": "ghz",
    "db": "db", "dbm": "dbm", "dbi": "dbi",
    "awg": "awg",
    # Percentage / Time / Speed / Data / Procurement UOM
    "%": "%", "percent": "%",
    "ms": "ms", "millisecond": "ms", "milliseconds": "ms",
    "us": "us", "µs": "us", "ns": "ns",
    "mm/s": "mm/s",
    "rpm": "rpm",
    "bps": "bps", "kbps": "kbps", "mbps": "mbps", "gbps": "gbps",
    "kb": "kb", "mb": "mb", "gb": "gb",
    "ea": "ea", "kt": "kt", "bx": "bx", "rl": "rl", "pk": "pk",
    "word": "words", "words": "words", "prose word": "words", "prose words": "words",
}

# Units ordered longest-first for regex alternation
SORTED_UNIT_PATTERNS = sorted(UNIT_ALIASES.keys(), key=len, reverse=True)
UNIT_REGEX_STR = "|".join(re.escape(u) for u in SORTED_UNIT_PATTERNS)

# Note: single-letter units like 'a', 'm', 'v', 'w', 'g', 'l', 'n' require careful boundary rules:
# If separated by whitespace (e.g. "2 a"), 'a' or 'in' could be an English word ("2 in the Rear Cover", "1 a day")!
# Therefore:
# - Attached without space ("20AWG", "2m", "60g", "12V", "100%", "0.20mm", "250°C") -> allow all units.
# - Separated by space ("70 kPa", "5,040 FT", "60 grams", "1.2 Nm", "10 L/min") -> disallow ambiguous English words ("a", "in") unless uppercase ("5 A") or full unit word ("inches", "amps")!
AMBIGUOUS_LOWER_SPACED_UNITS = {"a", "in", "m", "l", "n", "v", "w", "g"}
CASE_SENSITIVE_SPACED_OK = {"A", "V", "W", "N", "L"}

NUM_PAT = r"(?<!\w)[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[+-]?\d+(?:\.\d+)?"

RANGE_NUM_UNIT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.])([+-]?\d+(?:,\d{{3}})*(?:\.\d+)?)\s*(?:({UNIT_REGEX_STR})\s*)?(?:to|-|–|—)\s*([+-]?\d+(?:,\d{{3}})*(?:\.\d+)?)\s*({UNIT_REGEX_STR})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

SINGLE_NUM_UNIT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.])([+-]?\d+(?:,\d{{3}})*(?:\.\d+)?)(\s*)({UNIT_REGEX_STR})(?![A-Za-z0-9_/])",
    re.IGNORECASE,
)

WORD_NUM_RE_STR = "|".join(sorted(WORD_NUMBERS.keys(), key=len, reverse=True))
SPELLED_NUM_UNIT_RE = re.compile(
    rf"\b({WORD_NUM_RE_STR})(?:[\s-]+)({UNIT_REGEX_STR})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

# Shore durometer e.g. 95A, 85A, 98A, 60D (2 digits + A/D, excluding 20A/10A current unless Shore context, wait: 95A/85A/98A/70A/60D)
SHORE_RE = re.compile(r"\b(?:Shore\s*)?(75|80|85|90|95|98)[AD]\b|\bShore\s*\d{2}[AD]\b", re.IGNORECASE)

# Metric fasteners: M3x5x4mm, M3 x 65mm, M3x8mm, M5x12, M5x7x0.3mm
METRIC_FASTENER_RE = re.compile(
    r"\b(M\d+(?:\.\d+)?(?:\s*[x×]\s*\d+(?:\.\d+)?)+(?:\s*mm)?)\b", re.IGNORECASE
)

# Standard technical designators (cabling, jackets, polymers/alloys, IC packages, adhesives, connectors, MCU pins, part prefixes, 4-digit COTS fan/extrusion sizes)
DESIGNATOR_RE = re.compile(
    r"\b(Cat(?:5e|6A?|7|8)|OS[12]|OM[1-5]|CMP|CMR|LSZH|OFNP|OFNR|RJ45|SFP\+|QSFP28|"
    r"PTFE|FEP|PEEK|PEI|Ultem|6061(?:-T6)?|7075(?:-T6)?|"
    r"TO-\d+[A-Z]*|SOT-\d+[A-Z0-9-]*|SOIC-\d+|QFN-\d+|DFN-\d+|D2?PAK|PowerPAK|"
    r"Loctite\s+\d+[A-Z]*|TPN\d+|BF\d+|(?:MB\s+)?P/N\s+[A-Za-z0-9-]+|"
    r"GPIO\d+|P[A-K]\d{1,2}|PC4-M\d+|NEMA\s*\d+|1/8[- ]NPT|"
    r"(?:2510|3010|4010|4020|5015|5020|12032|1515|2020|2040|3030|4040)(?=\s*(?:mm\s+)?(?:fan|blower|axial|extrusion|profile|frame)s?\b))\b",
    re.IGNORECASE,
)

# Indefinite/unmeasured metric fastener callout inside a numbered assembly step (e.g. "using M3 screws" dodging missing length)
UNDERSPECIFIED_STEP_FASTENER_RE = re.compile(
    r"\b(?:using|with|install|insert|seat|thread|fasten|secure\s+with)\s+(?:\(\d+\)\s+|\d+x?\s+)?(M\d+\s+(?:screws?|bolts?|shcs|bhcs|fhcs))\b",
    re.IGNORECASE,
)

# Domain-agnostic qualifier nouns that bind a number+unit to a specific physical meaning on the same source line/row
QUALIFIER_GROUPS: List[Tuple[str, Tuple[str, ...]]] = [
    ("id", ("id", "internal diameter", "inner diameter", "inside diameter", "bore")),
    ("od", ("od", "outer diameter", "outside diameter", "external diameter")),
    ("infill", ("infill",)),
    ("pullup", ("pull-up", "pullup")),
    ("pulldown", ("pull-down", "pulldown")),
    ("gate", ("gate resistor", "vgs")),
]

QUALIFIED_NUM_UNIT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.])([+-]?\d+(?:,\d{{3}})*(?:\.\d+)?)(\s*)({UNIT_REGEX_STR})\s+"
    r"(id|od|internal\s+diameter|inner\s+diameter|inside\s+diameter|outer\s+diameter|outside\s+diameter|"
    r"infill|pull-up|pullup|pull-down|pulldown)\b",
    re.IGNORECASE,
)

REVERSE_QUALIFIED_RE = re.compile(
    r"\b(infill|id|od|internal\s+diameter|outer\s+diameter|pull-up|pull-down)\b[^.\n;|]{0,35}?"
    rf"(?<![A-Za-z0-9_.])([+-]?\d+(?:,\d{{3}})*(?:\.\d+)?)(\s*)({UNIT_REGEX_STR})(?![A-Za-z0-9_/])",
    re.IGNORECASE,
)

# Backticked identifiers (1..120 chars so 1-char tokens like `0` or `;` never misalign backtick pairing)
BACKTICK_RE = re.compile(r"`([^`\n]{1,120})`")

# Explicit [TBD...] / [UNVERIFIED...] / [CATALOG ADDITION REQUIRED...] markers
TBD_MARKER_RE = re.compile(
    r"\[(?:TBD|TODO|UNVERIFIED|CATALOG ADDITION REQUIRED)[^\]]*\]",
    re.IGNORECASE,
)
BACKTICKED_OR_RAW_TBD_RE = re.compile(
    r"`\[(?:TBD|TODO|UNVERIFIED|CATALOG ADDITION REQUIRED)[^\]]*\]`|\[(?:TBD|TODO|UNVERIFIED|CATALOG ADDITION REQUIRED)[^\]]*\]",
    re.IGNORECASE,
)
INERT_META_TBD_RE = re.compile(
    r"^\[(?:TBD|TODO|UNVERIFIED|CATALOG ADDITION REQUIRED)(?::\s*(?:CONFLICT\s*[—-]\s*)?(?:\.\.\.|…|<[^>]+>))?\]$",
    re.IGNORECASE,
)

# Explicit deterministic arithmetic marker: [CALC: 120W / 24V = 5.0A]
CALC_MARKER_RE = re.compile(r"\[CALC:\s*([^\]]+?)\s*\]", re.IGNORECASE)


def canonicalize_unit(raw_u: str, sep: str) -> Optional[str]:
    """Map raw unit token to canonical unit, filtering English stop-word collisions."""
    u_low = re.sub(r"\s+", " ", raw_u.lower().strip())
    if u_low not in UNIT_ALIASES:
        # Handle special case Ω / MΩ / mΩ
        if raw_u in UNIT_ALIASES:
            return UNIT_ALIASES[raw_u]
        return None
    # Distinguish lowercase 'w' (words in stylometrics, e.g. '19.0w' / '19.0 w') vs. uppercase 'W' (Watts)
    if raw_u == "w":
        return "words"
    if sep:
        # Spaced number + unit: block "2 in", "1 a", "3 m" lowercase prose collisions
        if u_low in AMBIGUOUS_LOWER_SPACED_UNITS and raw_u not in CASE_SENSITIVE_SPACED_OK:
            return None
    # Distinguish MΩ vs mΩ
    if raw_u == "MΩ":
        return "megohm"
    if raw_u == "mΩ":
        return "mohm"
    # Distinguish "Nm" / "N·m" (torque) vs "nm" (nanometers)
    if raw_u == "nm":
        return "nm_len"
    return UNIT_ALIASES[u_low]


def parse_num(raw_n: str) -> float:
    return float(raw_n.replace(",", ""))


def strip_non_claim_regions(text: str) -> List[Tuple[int, str, List[str]]]:
    """
    Returns list of (line_no, cleaned_line, tbd_hits_on_line).
    Strips YAML frontmatter, Mermaid styling directives, HTML <img> layout tags,
    and external URLs while preserving 1-based line numbers.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    is_standard_doc = bool(
        re.search(r"^type:\s*(?:standard|command-reference)\b", text[:500], re.IGNORECASE | re.MULTILINE)
    )
    in_frontmatter = False
    in_mermaid = False
    results: List[Tuple[int, str, List[str]]] = []

    for idx, raw_ln in enumerate(lines):
        line_no = idx + 1
        s = raw_ln.strip()

        if idx == 0 and s == "---":
            in_frontmatter = True
            results.append((line_no, "", []))
            continue
        if in_frontmatter:
            if s == "---":
                in_frontmatter = False
            results.append((line_no, "", []))
            continue

        if s.startswith("```mermaid"):
            in_mermaid = True
            results.append((line_no, "", []))
            continue
        if in_mermaid:
            if s.startswith("```"):
                in_mermaid = False
                results.append((line_no, "", []))
                continue
            if s.startswith("%%{init:") or s.startswith("classDef ") or s.startswith("class ") or s.startswith("style ") or s.startswith("linkStyle "):
                results.append((line_no, "", []))
                continue

        # Extract [TBD...] markers first before masking them (and consume optional surrounding backticks
        # so `` `[TBD: ...]` `` never leaves orphaned `` ` ` `` backticks that misalign the rest of the line).
        tbds = [
            m.group(0)
            for m in TBD_MARKER_RE.finditer(raw_ln)
            if not (is_standard_doc and INERT_META_TBD_RE.match(m.group(0).strip()))
        ]
        cleaned = BACKTICKED_OR_RAW_TBD_RE.sub(" ", raw_ln)

        # Mask URLs so shield badges / query params (?affp=6182) aren't parsed as units (preserve closing backticks)
        cleaned = re.sub(r"https?://[^\s)>\"'`]+", " ", cleaned)
        # Mask HTML <img ...> tags (e.g., width="45%" layout attributes)
        cleaned = re.sub(r"<img\b[^>]*>", " ", cleaned, flags=re.IGNORECASE)
        # Mask Markdown image paths ![alt](path) while keeping alt text out of backtick checks
        cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)

        results.append((line_no, cleaned, tbds))

    return results


def normalize_fastener(raw_f: str) -> str:
    s = re.sub(r"\s+", "", raw_f.lower().replace("×", "x"))
    if s.endswith("mm"):
        s = s[:-2]
    return s


def normalize_designator(raw_d: str) -> str:
    return re.sub(r"[\s-]+", "-", raw_d.lower().strip())


AI_PROVENANCE_RE = re.compile(
    r"\b(?:ai[- ]assisted|ai assistance|generated (?:by|with) ai|ai transparency|written with ai|llm[- ]generated)\b",
    re.IGNORECASE,
)
PLACEHOLDER_STUB_RE = re.compile(
    r"\b(?:currently a placeholder|placeholder (?:for|document|file|page)|coming soon|under construction)\b",
    re.IGNORECASE,
)
EXEMPT_PROVENANCE_FRONTMATTER_RE = re.compile(
    r"^(?:type:\s*(?:standard|hardware-manifest|moc-hub|engineering-log|task-landing-pad|task-umbrella|command-reference)|project:\s+\S+)\b",
    re.IGNORECASE | re.MULTILINE,
)
QUARANTINE_HEADING_RE = re.compile(
    r"^(#{2,4})\s+.*(?:Open\s+\[TBD\]|\[CONFLICT\]\s+Ledger|Unverified\s+Claims|Quarantined\s+Claims)",
    re.IGNORECASE,
)
HEADING_LEVEL_RE = re.compile(r"^(#{1,6})\s+")
VRF_RECEIPT_RE = re.compile(r"\bVRF-[0-9a-f]{12}\b", re.IGNORECASE)


def quarantine_unverified_source_zones(text: str) -> str:
    """
    Strip inline `[TBD: ...]` / `[UNVERIFIED ...]` spans and quarantine Markdown
    sections explicitly dedicated to Open [TBD] / [CONFLICT] / Unverified ledgers
    so unverified or conflicting figures recorded in memory notes are never
    whitelisted as authoritative ground truth during `--sources` indexing.
    """
    kept_lines: List[str] = []
    quarantine_level: Optional[int] = None
    for raw_ln in text.replace("\r\n", "\n").split("\n"):
        hm = HEADING_LEVEL_RE.match(raw_ln.strip())
        if hm:
            lvl = len(hm.group(1))
            if quarantine_level is not None and lvl <= quarantine_level:
                quarantine_level = None
            if QUARANTINE_HEADING_RE.match(raw_ln.strip()):
                quarantine_level = lvl
                continue
        if quarantine_level is not None:
            continue
        kept_lines.append(BACKTICKED_OR_RAW_TBD_RE.sub(" ", raw_ln))
    return "\n".join(kept_lines)


def inspect_source_provenance(fp: str, text: str) -> List[str]:
    """
    Detect suspect or mixed-provenance signals on a candidate `--sources` file:
      - DIRTY_GIT_WORKTREE: uncommitted or untracked changes inside a Git repo
      - AI_AUTHORED_UNRECEIPTED: AI-authored/assisted marker without a VRF receipt
      - CONTAINS_OPEN_TBD: source file itself contains unresolved [TBD]/[UNVERIFIED]
      - PLACEHOLDER_STUB_SOURCE: source explicitly marks itself as a placeholder stub
    Governing standards (`type: standard`) and deterministic manifests (`type: hardware-manifest`)
    are exempt from AI/TBD prose triggers.
    """
    reasons: List[str] = []
    abs_fp = os.path.abspath(fp)
    parent_dir = os.path.dirname(abs_fp) or "."

    try:
        proc = subprocess.run(
            ["git", "-C", parent_dir, "status", "--porcelain", "--", abs_fp],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            code = proc.stdout.strip().split()[0]
            reasons.append(f"DIRTY_GIT_WORKTREE({code})")
    except Exception:
        pass

    is_exempt_spec = bool(EXEMPT_PROVENANCE_FRONTMATTER_RE.search(text[:500])) or (
        os.path.basename(abs_fp) == "SKILL.md"
    )
    if not is_exempt_spec:
        if PLACEHOLDER_STUB_RE.search(text):
            reasons.append("PLACEHOLDER_STUB_SOURCE")
        if AI_PROVENANCE_RE.search(text) and not VRF_RECEIPT_RE.search(text):
            reasons.append("AI_AUTHORED_UNRECEIPTED")
        if TBD_MARKER_RE.search(text):
            reasons.append("CONTAINS_OPEN_TBD")

    return reasons


def collect_source_files(
    paths: List[str], target_path: Optional[str] = None
) -> Tuple[List[str], List[str]]:
    collected: List[str] = []
    excluded_circular: List[str] = []
    seen: Set[str] = set()
    target_rp: Optional[str] = None
    if target_path and target_path != "-" and os.path.exists(target_path):
        target_rp = os.path.realpath(target_path)

    for p in paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Authoritative source path does not exist: {p}")
        if os.path.isfile(p):
            rp = os.path.realpath(p)
            if target_rp and rp == target_rp:
                raise ValueError(
                    f"Self-referential circular validation blocked: --target '{p}' cannot be passed in --sources."
                )
            if rp not in seen:
                seen.add(rp)
                collected.append(p)
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__")
                for fn in sorted(files):
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in TEXT_EXTENSIONS or fn in ("LICENSE", "CNAME"):
                        fp = os.path.join(root, fn)
                        rp = os.path.realpath(fp)
                        if target_rp and rp == target_rp:
                            excluded_circular.append(fp)
                            continue
                        if rp not in seen:
                            seen.add(rp)
                            collected.append(fp)
    return collected, excluded_circular


def map_qualifier_group(raw_q: str) -> Optional[str]:
    ql = re.sub(r"\s+", " ", raw_q.lower().strip())
    for grp, syns in QUALIFIER_GROUPS:
        if ql in syns:
            return grp
    return None


class SourceIndex:
    def __init__(
        self,
        source_files: List[str],
        excluded_circular: Optional[List[str]] = None,
    ) -> None:
        self.file_hashes: List[Tuple[str, str]] = []
        self.provenance_warnings: List[Dict[str, object]] = []
        self.excluded_circular: List[str] = excluded_circular or []
        self.num_units: Set[Tuple[float, str]] = set()
        self.qualified_num_units: Set[Tuple[float, str, str]] = set()
        self.numbers_all: Set[float] = set()
        self.fasteners: Set[str] = set()
        self.designators: Set[str] = set()
        self.source_basenames: Set[str] = set()
        self.source_dirs: Set[str] = set()
        self.raw_lower_chunks: List[str] = []

        for fp in source_files:
            raw_bytes = open(fp, "rb").read()
            h10 = hashlib.sha256(raw_bytes).hexdigest()[:10]
            self.file_hashes.append((fp, h10))
            bname_low = os.path.basename(fp).lower()
            self.source_basenames.add(bname_low)
            self.source_dirs.add(os.path.dirname(os.path.abspath(fp)))
            self.raw_lower_chunks.append(bname_low)
            text = raw_bytes.decode("utf-8", errors="replace")
            prov_reasons = inspect_source_provenance(fp, text)
            if prov_reasons:
                self.provenance_warnings.append({"file": fp, "reasons": prov_reasons})
            self._index_text(text)

        self.raw_blob = "\n".join(self.raw_lower_chunks)
        self.raw_blob_nocomma = re.sub(r"(?<=\d),(?=\d{3}\b)", "", self.raw_blob)

        # Compute deterministic 12-hex Proof-of-Verification Receipt
        receipt_seed = "|".join(
            f"{os.path.basename(fp)}:{h}" for fp, h in sorted(self.file_hashes)
        )
        self.vrf_token = "VRF-" + hashlib.sha256(receipt_seed.encode("utf-8")).hexdigest()[:12]

    def _index_text(self, text: str) -> None:
        text = quarantine_unverified_source_zones(text)
        low = text.lower()
        self.raw_lower_chunks.append(low)

        # Line-scoped indexing for qualified quantities (e.g., "Infill: 40%", "6mm OD")
        for raw_ln in text.splitlines():
            ln_low = re.sub(r"\s+", " ", raw_ln.lower())
            active_grps = [
                grp for grp, syns in QUALIFIER_GROUPS
                if any(re.search(rf"\b{re.escape(syn)}\b", ln_low) for syn in syns)
            ]
            if active_grps:
                for m in SINGLE_NUM_UNIT_RE.finditer(raw_ln):
                    cu = canonicalize_unit(m.group(3), m.group(2))
                    if cu:
                        v = round(parse_num(m.group(1)), 6)
                        for g in active_grps:
                            self.qualified_num_units.add((v, cu, g))

        # Index metric fasteners BEFORE stripping 'mm' units so M3x5x4mm indexes both fastener and mm
        for m in METRIC_FASTENER_RE.finditer(text):
            self.fasteners.add(normalize_fastener(m.group(1)))

        for m in DESIGNATOR_RE.finditer(text):
            self.designators.add(normalize_designator(m.group(1)))

        for m in SHORE_RE.finditer(text):
            shore_tok = re.sub(r"^shore\s*", "", m.group(0).lower()).strip()
            self.designators.add(f"shore:{shore_tok}")

        # Unquote backticked bare numbers/ranges (e.g. "`19.0` w" or "`13–26` w") for unit indexing
        num_scan_text = re.sub(r"`([+-]?\d[\d,.–—-]*)`", r"\1", text)

        # Index ranges e.g. "1.0 to 1.5 Nm" or "`13–26` w"
        for m in RANGE_NUM_UNIT_RE.finditer(num_scan_text):
            n1, u1, n2, u2 = m.group(1), m.group(2), m.group(3), m.group(4)
            cu2 = canonicalize_unit(u2, " ") or ("words" if u2 == "w" else UNIT_ALIASES.get(u2.lower()))
            cu1 = (
                (canonicalize_unit(u1, " ") or ("words" if u1 == "w" else UNIT_ALIASES.get(u1.lower())))
                if u1
                else cu2
            )
            if cu1:
                self.num_units.add((round(parse_num(n1), 6), cu1))
            if cu2:
                self.num_units.add((round(parse_num(n2), 6), cu2))

        # Index single num+unit
        for m in SINGLE_NUM_UNIT_RE.finditer(num_scan_text):
            n_str, sep, u_str = m.group(1), m.group(2), m.group(3)
            cu = canonicalize_unit(u_str, sep)
            if cu:
                val = round(parse_num(n_str), 6)
                self.num_units.add((val, cu))
                if val < 0:
                    self.num_units.add((abs(val), cu))

        # Index spelled-out num+unit
        for m in SPELLED_NUM_UNIT_RE.finditer(text):
            w_str, u_str = m.group(1).lower(), m.group(2)
            cu = canonicalize_unit(u_str, "")
            if cu and w_str in WORD_NUMBERS:
                self.num_units.add((round(WORD_NUMBERS[w_str], 6), cu))

        # Index CAD manifest `X × Y × Z (mm)` and `Volume (cm³)` table cells when header declares units
        if "x × y × z (mm)" in low:
            for m_env in re.finditer(r"(\d+\.\d+)\s*×\s*(\d+\.\d+)\s*×\s*(\d+\.\d+)", text):
                for grp_i in (1, 2, 3):
                    self.num_units.add((round(parse_num(m_env.group(grp_i)), 6), "mm"))
            for m_vol in re.finditer(r"`\d+\.\d+\s*×\s*\d+\.\d+\s*×\s*\d+\.\d+`\s*\|\s*`(\d+\.\d+)`", text):
                self.num_units.add((round(parse_num(m_vol.group(1)), 6), "cm3"))

        # Index all standalone numbers (for table quantities / part IDs if needed)
        for m in re.finditer(r"(?<![A-Za-z0-9_.])[+-]?\d+(?:,\d{3})*(?:\.\d+)?(?![A-Za-z0-9_.])", text):
            try:
                self.numbers_all.add(round(parse_num(m.group(0)), 6))
            except ValueError:
                pass

    def has_num_unit(self, val: float, cu: str) -> bool:
        rval = round(val, 6)
        return (rval, cu) in self.num_units

    def has_qualified_num_unit(self, val: float, cu: str, grp: str) -> bool:
        rval = round(val, 6)
        return (rval, cu, grp) in self.qualified_num_units

    def has_fastener(self, raw_f: str) -> bool:
        nf = normalize_fastener(raw_f)
        if nf in self.fasteners:
            return True
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(nf)}(?![a-z0-9])", self.raw_blob))

    def has_designator(self, raw_d: str) -> bool:
        nd = normalize_designator(raw_d)
        if nd in self.designators:
            return True
        alt_space = nd.replace("-", r"[\s-]+")
        return bool(re.search(rf"(?<![a-z0-9]){alt_space}(?![a-z0-9])", self.raw_blob))

    def has_shore(self, raw_s: str) -> bool:
        shore_tok = re.sub(r"^shore\s*", "", raw_s.lower()).strip()
        return (f"shore:{shore_tok}" in self.designators) or (shore_tok in self.raw_blob)

    def has_backtick_literal(self, tok: str) -> bool:
        t = tok.strip()
        t_low = t.lower()
        # Ignore generic Markdown/CLI example placeholders or multi-word prose commands > 4 words without file extensions
        if " " in t and not re.search(r"\.(?:stl|step|stp|xlsx|cfg|py|md|json|csv)\b|![A-Z]+\d+", t_low):
            # Check if it's a macro assignment like MODE=COOL or SET_PNEUMA_MODE MODE=WARM
            parts = [p.strip("(),") for p in t.split() if p.strip("(),")]
            return all(self._single_token_in_source(p) for p in parts)
        return self._single_token_in_source(t)

    def _single_token_in_source(self, tok: str) -> bool:
        tl = tok.strip("`'\"()[]{}").lower().strip()
        if not tl:
            return True
        if "=" in tl and not tl.startswith("="):
            if self._exact_token_match(tl):
                return True
            lhs, rhs = tl.split("=", 1)
            return self._exact_token_match(lhs) and self._exact_token_match(rhs)
        return self._exact_token_match(tl)

    def _exact_token_match(self, tl: str) -> bool:
        tl_nocomma = re.sub(r"(?<=\d),(?=\d{3}\b)", "", tl)
        pat1 = rf"(?<![a-z0-9]){re.escape(tl)}(?![a-z0-9])"
        pat2 = rf"(?<![a-z0-9]){re.escape(tl_nocomma)}(?![a-z0-9])"
        return bool(re.search(pat1, self.raw_blob)) or bool(re.search(pat2, self.raw_blob_nocomma))


def _safe_eval_arith(expr: str) -> float:
    """Safely evaluate pure numeric arithmetic (+, -, *, /, **) via AST."""
    tree = ast.parse(expr, mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = _eval(node.operand)
            return v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right
        raise ValueError(f"Unsupported arithmetic node: {type(node).__name__}")

    return _eval(tree)


def verify_calc_marker(
    calc_body: str, idx: SourceIndex
) -> Tuple[bool, str, Optional[Tuple[float, str]], Optional[float]]:
    """
    Verify `[CALC: <lhs_expr> = <rhs_val><unit>]`:
      1. Every `<num><unit>` operand in `<lhs_expr>` must exist in `idx.num_units`.
      2. Every bare number in `<lhs_expr>` (excluding `** 2` / `** 3` formula exponents)
         must exist in `idx.numbers_all`.
      3. Pure arithmetic `<lhs_expr>` must equal `<rhs_val>` within rounding tolerance.
    Returns `(ok, tag, derived_num_unit_pair, derived_rhs_number)`.
    """
    if "=" not in calc_body:
        return False, "CALC_SYNTAX_ERROR", None, None
    lhs_raw, rhs_raw = calc_body.split("=", 1)

    # 1. Check and strip `<num><unit>` operands in LHS
    lhs_bare_scan = lhs_raw
    unit_spans: List[Tuple[int, int, str]] = []
    for m in SINGLE_NUM_UNIT_RE.finditer(lhs_raw):
        n_str, sep, u_str = m.group(1), m.group(2), m.group(3)
        cu = canonicalize_unit(u_str, sep) or UNIT_ALIASES.get(re.sub(r"\s+", " ", u_str.lower().strip()))
        if not cu:
            continue
        val = parse_num(n_str)
        if not idx.has_num_unit(val, cu):
            return False, f"CALC_UNBACKED_OPERAND({m.group(0).strip()})", None, None
        unit_spans.append((m.start(), m.end(), str(val)))

    # Mask unit spans in lhs_bare_scan so we can check any remaining bare numbers
    if unit_spans:
        bare_chars = list(lhs_bare_scan)
        for st, en, _ in unit_spans:
            for i in range(st, en):
                bare_chars[i] = " "
        lhs_bare_scan = "".join(bare_chars)

    # Allow mathematical power exponents (** 2, ** 3, ^2, ^3) without requiring '2' in source
    lhs_bare_no_exp = re.sub(r"(?:\*\*|\^)\s*[23]\b", " ", lhs_bare_scan)
    for m_bare in re.finditer(r"(?<![A-Za-z0-9_.])[+-]?\d+(?:,\d{3})*(?:\.\d+)?(?![A-Za-z0-9_.])", lhs_bare_no_exp):
        bval = round(parse_num(m_bare.group(0)), 6)
        if bval not in idx.numbers_all:
            return False, f"CALC_UNBACKED_NUMBER({m_bare.group(0)})", None, None

    # Build pure numeric expression from right-to-left span replacements
    lhs_expr = lhs_raw
    for st, en, val_s in reversed(unit_spans):
        lhs_expr = lhs_expr[:st] + val_s + lhs_expr[en:]
    lhs_expr = re.sub(r"(?<=\d),(?=\d{3}\b)", "", lhs_expr)
    lhs_expr = lhs_expr.replace("×", "*").replace("^", "**")

    derived_pair: Optional[Tuple[float, str]] = None
    m_rhs_unit = SINGLE_NUM_UNIT_RE.search(rhs_raw)
    if m_rhs_unit:
        rhs_val = parse_num(m_rhs_unit.group(1))
        rhs_cu = canonicalize_unit(m_rhs_unit.group(3), m_rhs_unit.group(2)) or UNIT_ALIASES.get(
            re.sub(r"\s+", " ", m_rhs_unit.group(3).lower().strip())
        )
        if rhs_cu:
            derived_pair = (round(rhs_val, 6), rhs_cu)
    else:
        m_rhs = re.search(r"[+-]?\d+(?:,\d{3})*(?:\.\d+)?", rhs_raw)
        if not m_rhs:
            return False, "CALC_MISSING_RHS_VALUE", None, None
        rhs_val = parse_num(m_rhs.group(0))

    try:
        calc_val = _safe_eval_arith(lhs_expr.strip())
    except Exception:
        return False, "CALC_INVALID_EXPR", None, None

    tol = max(0.015, abs(calc_val) * 0.005)
    if abs(calc_val - rhs_val) > tol:
        return False, f"CALC_MATH_MISMATCH(expected={calc_val:.4g},got={rhs_val})", None, None
    return True, "VERIFIED_CALC", derived_pair, round(rhs_val, 6)


def audit_target(target_text: str, idx: SourceIndex) -> Dict[str, object]:
    cleaned_lines = strip_non_claim_regions(target_text)
    supported: List[Dict[str, object]] = []
    unbacked: List[Dict[str, object]] = []
    tbd_offenders: List[Dict[str, object]] = []
    derived_num_units: Set[Tuple[float, str]] = set()
    derived_numbers: Set[float] = set()

    for line_no, ln, tbds in cleaned_lines:
        for t in tbds:
            tbd_offenders.append({"line": line_no, "marker": t})
        if not ln.strip():
            continue

        # 0. Deterministic Arithmetic Calculations (`[CALC: 120W / 24V = 5.0A]`)
        calc_spans: List[Tuple[int, int]] = []
        for m in CALC_MARKER_RE.finditer(ln):
            calc_spans.append(m.span())
            ok, tag, d_pair, d_num = verify_calc_marker(m.group(1), idx)
            if ok:
                if d_pair is not None:
                    derived_num_units.add(d_pair)
                if d_num is not None:
                    derived_numbers.add(d_num)
            rec = {"line": line_no, "type": tag, "claim": m.group(0)}
            (supported if ok else unbacked).append(rec)
        if calc_spans:
            chars = list(ln)
            for st, en in calc_spans:
                for i in range(st, en):
                    chars[i] = " "
            ln = "".join(chars)

        # 1. Backticked Identifiers (`*.stl`, `*.cfg`, `PF7`, `D33:I34`, etc.)
        #    Note: backticked measurements/inequalities like `<3mm` or `6mm OD x 4mm ID`
        #    are unquoted into prose_ln so their quantities are checked as QUANTITY_UNIT rather than LITERAL_ID.
        id_backtick_spans: List[Tuple[int, int]] = []
        unquoted_chars = list(ln)
        for m in BACKTICK_RE.finditer(ln):
            lit = m.group(1).strip()
            if not lit or lit.startswith("[TBD") or not re.search(r"[A-Za-z0-9]", lit):
                id_backtick_spans.append(m.span())
                continue
            # Quoted prose examples inside backticks (e.g. `"Print in TPU"`) are stylistic strings, not IDs
            if (lit.startswith('"') and lit.endswith('"')) or (lit.startswith("'") and lit.endswith("'")):
                id_backtick_spans.append(m.span())
                continue
            # Backticked bare counts (`578x`, `437`, `73,893`) -> check directly against idx.numbers_all / derived_numbers
            m_cnt = re.match(r"^([+-]?\d+(?:,\d{3})*(?:\.\d+)?)x?$", lit, re.IGNORECASE)
            if m_cnt:
                id_backtick_spans.append(m.span())
                cval = round(parse_num(m_cnt.group(1)), 6)
                ok_cnt = (cval in idx.numbers_all) or (cval in derived_numbers)
                rec_cnt = {"line": line_no, "type": "NUMERIC_COUNT", "claim": f"`{lit}`"}
                (supported if ok_cnt else unbacked).append(rec_cnt)
                continue
            # Backticked bare numeric ranges (`13–26`, `3–17`, `1–2`) -> check both endpoints
            m_brng = re.match(
                r"^([+-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:to|-|–|—)\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)$",
                lit,
                re.IGNORECASE,
            )
            if m_brng:
                id_backtick_spans.append(m.span())
                v1 = round(parse_num(m_brng.group(1)), 6)
                v2 = round(parse_num(m_brng.group(2)), 6)
                ok_br = ((v1 in idx.numbers_all) or (v1 in derived_numbers)) and (
                    (v2 in idx.numbers_all) or (v2 in derived_numbers)
                )
                rec_br = {"line": line_no, "type": "NUMERIC_RANGE", "claim": f"`{lit}`"}
                (supported if ok_br else unbacked).append(rec_br)
                continue
            # Backticked file/line provenance citations (`README.md:10-14`, `HEAD:BOM.md`, `docs/CNAME:1`) -> verify cited file is in --sources
            m_prov = re.match(
                r"^(?:HEAD:)?([A-Za-z0-9_./-]+(?:\.[A-Za-z0-9]+|/)|(?:[A-Za-z0-9_./-]+/)?(?:LICENSE|CNAME))(?::\d[\d,-]*)?$",
                lit,
            )
            if m_prov:
                cited_rel = m_prov.group(1)
                if cited_rel.endswith("/"):
                    ok_dir = any(
                        os.path.isdir(os.path.join(sd, cited_rel.rstrip("/")))
                        or os.path.isdir(os.path.join(os.path.dirname(sd), cited_rel.rstrip("/")))
                        for sd in idx.source_dirs
                    ) or idx.has_backtick_literal(lit)
                    if ok_dir:
                        id_backtick_spans.append(m.span())
                        supported.append({"line": line_no, "type": "PROVENANCE_DIR", "claim": f"`{lit}`"})
                        continue
                elif ":" in lit or lit.startswith("HEAD:") or "/" in cited_rel or cited_rel in ("LICENSE", "CNAME"):
                    ok_cit = (os.path.basename(cited_rel).lower() in idx.source_basenames) or any(
                        os.path.exists(os.path.join(sd, cited_rel))
                        or os.path.exists(os.path.join(os.path.dirname(sd), cited_rel))
                        for sd in idx.source_dirs
                    )
                    if ok_cit:
                        id_backtick_spans.append(m.span())
                        supported.append({"line": line_no, "type": "PROVENANCE_REF", "claim": f"`{lit}`"})
                        continue
            # Backticked local filesystem paths (`/home/...`) -> verify path exists on disk or in sources
            if lit.startswith("/") and lit.count("/") >= 2 and " " not in lit:
                id_backtick_spans.append(m.span())
                ok_fp = os.path.exists(lit.rstrip("/")) or idx.has_backtick_literal(lit)
                rec_fp = {"line": line_no, "type": "FILESYSTEM_PATH", "claim": f"`{lit}`"}
                (supported if ok_fp else unbacked).append(rec_fp)
                continue
            if re.match(r"^[<>≤≥~≈±]?\s*\d", lit) and (SINGLE_NUM_UNIT_RE.search(lit) or RANGE_NUM_UNIT_RE.search(lit)):
                # Strip only the surrounding backtick characters so prose_ln checks the quantity(s) inside!
                unquoted_chars[m.start()] = " "
                unquoted_chars[m.end() - 1] = " "
                continue
            id_backtick_spans.append(m.span())
            ok = idx.has_backtick_literal(lit)
            rec = {"line": line_no, "type": "LITERAL_ID", "claim": f"`{lit}`"}
            (supported if ok else unbacked).append(rec)

        for st, en in id_backtick_spans:
            for i in range(st, en):
                unquoted_chars[i] = " "
        prose_ln = "".join(unquoted_chars)

        # 2. Metric Fasteners (M3x5x4mm, M3x8mm, M5x12) — mask after checking so "4mm" tail isn't double-checked as standalone length!
        fastener_spans: List[Tuple[int, int]] = []
        for m in METRIC_FASTENER_RE.finditer(prose_ln):
            f_tok = m.group(1)
            fastener_spans.append(m.span())
            ok = idx.has_fastener(f_tok)
            rec = {"line": line_no, "type": "FASTENER_SPEC", "claim": f_tok}
            (supported if ok else unbacked).append(rec)

        # Mask matched metric fasteners so `M3x8mm` doesn't also fire `8mm` standalone
        if fastener_spans:
            chars = list(prose_ln)
            for st, en in fastener_spans:
                for i in range(st, en):
                    chars[i] = " "
            prose_ln = "".join(chars)

        # 2b. Underspecified Fastener Callouts in Numbered Assembly Steps (e.g. "using M3 screws" dodging missing length)
        if re.match(r"^\s*\d+\.\s+", ln) and not tbds:
            for m_uf in UNDERSPECIFIED_STEP_FASTENER_RE.finditer(prose_ln):
                unbacked.append(
                    {
                        "line": line_no,
                        "type": "UNDERSPECIFIED_FASTENER_DODGE",
                        "claim": m_uf.group(0).strip(),
                    }
                )

        # 3. Shore Durometer (95A, 85A, 60D)
        shore_spans: List[Tuple[int, int]] = []
        for m in SHORE_RE.finditer(prose_ln):
            s_tok = m.group(0)
            shore_spans.append(m.span())
            ok = idx.has_shore(s_tok)
            rec = {"line": line_no, "type": "SHORE_HARDNESS", "claim": s_tok}
            (supported if ok else unbacked).append(rec)
        if shore_spans:
            chars = list(prose_ln)
            for st, en in shore_spans:
                for i in range(st, en):
                    chars[i] = " "
            prose_ln = "".join(chars)

        # 4. Technical Designators (Cat6A, OS2, Loctite 243, 1/8 NPT, TPN##, etc.)
        desig_spans: List[Tuple[int, int]] = []
        for m in DESIGNATOR_RE.finditer(prose_ln):
            d_tok = m.group(1)
            desig_spans.append(m.span())
            ok = idx.has_designator(d_tok)
            rec = {"line": line_no, "type": "DESIGNATOR", "claim": d_tok}
            (supported if ok else unbacked).append(rec)
        if desig_spans:
            chars = list(prose_ln)
            for st, en in desig_spans:
                for i in range(st, en):
                    chars[i] = " "
            prose_ln = "".join(chars)

        # 5. Numeric Ranges + Units ("50 to 70 grams", "1.0 to 1.5 Nm")
        range_spans: List[Tuple[int, int]] = []
        for m in RANGE_NUM_UNIT_RE.finditer(prose_ln):
            n1, u1, n2, u2 = m.group(1), m.group(2), m.group(3), m.group(4)
            cu2 = canonicalize_unit(u2, " ") or UNIT_ALIASES.get(re.sub(r"\s+", " ", u2.lower().strip()))
            cu1 = (
                canonicalize_unit(u1, " ") or UNIT_ALIASES.get(re.sub(r"\s+", " ", u1.lower().strip()))
            ) if u1 else cu2
            if cu1 and cu2:
                range_spans.append(m.span())
                v1, v2 = parse_num(n1), parse_num(n2)
                ok1 = idx.has_num_unit(v1, cu1) or ((round(v1, 6), cu1) in derived_num_units)
                ok2 = idx.has_num_unit(v2, cu2) or ((round(v2, 6), cu2) in derived_num_units)
                rec = {"line": line_no, "type": "RANGE_QUANTITY", "claim": m.group(0).strip()}
                (supported if (ok1 and ok2) else unbacked).append(rec)
        if range_spans:
            chars = list(prose_ln)
            for st, en in range_spans:
                for i in range(st, en):
                    chars[i] = " "
            prose_ln = "".join(chars)

        # 6. Spelled-Out Number + Unit ("two-meter", "sixty grams")
        for m in SPELLED_NUM_UNIT_RE.finditer(prose_ln):
            w_str, u_str = m.group(1).lower(), m.group(2)
            cu = canonicalize_unit(u_str, "")
            if cu and w_str in WORD_NUMBERS:
                v_w = WORD_NUMBERS[w_str]
                ok = idx.has_num_unit(v_w, cu) or ((round(v_w, 6), cu) in derived_num_units)
                rec = {"line": line_no, "type": "SPELLED_QUANTITY", "claim": m.group(0).strip()}
                (supported if ok else unbacked).append(rec)

        # 6b. Qualified Number + Unit ("100% infill", "4mm internal diameter", "Infill: 40%")
        qual_spans: List[Tuple[int, int]] = []
        for m in QUALIFIED_NUM_UNIT_RE.finditer(prose_ln):
            n_str, sep, u_str, q_str = m.group(1), m.group(2), m.group(3), m.group(4)
            cu = canonicalize_unit(u_str, sep)
            grp = map_qualifier_group(q_str)
            if cu and grp:
                qual_spans.append(m.span())
                ok = idx.has_qualified_num_unit(parse_num(n_str), cu, grp)
                rec = {"line": line_no, "type": f"QUALIFIED_QUANTITY({grp.upper()})", "claim": m.group(0).strip()}
                (supported if ok else unbacked).append(rec)

        if qual_spans:
            chars = list(prose_ln)
            for st, en in qual_spans:
                for i in range(st, en):
                    chars[i] = " "
            prose_ln = "".join(chars)

        rev_spans: List[Tuple[int, int]] = []
        for m in REVERSE_QUALIFIED_RE.finditer(prose_ln):
            q_str, n_str, sep, u_str = m.group(1), m.group(2), m.group(3), m.group(4)
            cu = canonicalize_unit(u_str, sep)
            grp = map_qualifier_group(q_str)
            if cu and grp:
                rev_spans.append(m.span())
                ok = idx.has_qualified_num_unit(parse_num(n_str), cu, grp)
                rec = {"line": line_no, "type": f"QUALIFIED_QUANTITY({grp.upper()})", "claim": m.group(0).strip()}
                (supported if ok else unbacked).append(rec)

        if rev_spans:
            chars = list(prose_ln)
            for st, en in rev_spans:
                for i in range(st, en):
                    chars[i] = " "
            prose_ln = "".join(chars)

        # 7. Single Number + Unit ("70 kPa", "0.20mm", "250°C", "5,040 FT", "20AWG")
        for m in SINGLE_NUM_UNIT_RE.finditer(prose_ln):
            n_str, sep, u_str = m.group(1), m.group(2), m.group(3)
            cu = canonicalize_unit(u_str, sep)
            if not cu:
                continue
            val = parse_num(n_str)
            ok = idx.has_num_unit(val, cu) or ((round(val, 6), cu) in derived_num_units)
            rec = {"line": line_no, "type": "QUANTITY_UNIT", "claim": m.group(0).strip()}
            (supported if ok else unbacked).append(rec)

    return {
        "vrf_token": idx.vrf_token,
        "sources_checked": len(idx.file_hashes),
        "source_hashes": [{"file": fp, "sha256_10": h} for fp, h in idx.file_hashes],
        "excluded_circular_sources": idx.excluded_circular,
        "provenance_warning_count": len(idx.provenance_warnings),
        "provenance_warnings": idx.provenance_warnings,
        "supported_count": len(supported),
        "unbacked_count": len(unbacked),
        "tbd_count": len(tbd_offenders),
        "unbacked_claims": unbacked,
        "tbd_offenders": tbd_offenders,
        "supported_claims": supported,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic domain-agnostic engineering claim & [TBD] verifier."
    )
    parser.add_argument(
        "--target", required=True, help="Draft/output file to verify (or '-' for stdin)."
    )
    parser.add_argument(
        "--sources", nargs="+", required=True, help="Authoritative source files or directories."
    )
    parser.add_argument(
        "--fail-on-tbd",
        action="store_true",
        help="Return exit code 2 if any open [TBD: ...] markers exist.",
    )
    parser.add_argument(
        "--strict-provenance",
        action="store_true",
        help="Return exit code 3 if any --sources file has suspect provenance (dirty Git, unreceipted AI prose, or [TBD]).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON output."
    )
    args = parser.parse_args()

    try:
        if args.target == "-":
            target_text = sys.stdin.read()
            target_label = "<stdin>"
        else:
            if not os.path.isfile(args.target):
                print(f"[EXTRACTION BLOCKED — ABORTED] Target file not found: {args.target}", file=sys.stderr)
                return 1
            with open(args.target, "r", encoding="utf-8", errors="replace") as f:
                target_text = f.read()
            target_label = args.target

        source_files, excluded_circular = collect_source_files(args.sources, args.target)
        if not source_files:
            print("[EXTRACTION BLOCKED — ABORTED] Zero readable non-circular source files found.", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[EXTRACTION BLOCKED — ABORTED] {exc}", file=sys.stderr)
        return 1

    idx = SourceIndex(source_files, excluded_circular=excluded_circular)
    report = audit_target(target_text, idx)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = "PASS" if report["unbacked_count"] == 0 else "FAIL — UNBACKED CLAIMS DETECTED"
        if report["unbacked_count"] == 0 and args.strict_provenance and report["provenance_warning_count"] > 0:
            status = "BLOCKED — UNVETTED SOURCE PROVENANCE"
        elif report["unbacked_count"] == 0 and args.fail_on_tbd and report["tbd_count"] > 0:
            status = "BLOCKED — UNRESOLVED [TBD] OFFENDERS"
        print(f"=== Claim Verification Audit: {target_label} ===")
        print(f"Status: {status} | Receipt: {report['vrf_token']} | Sources: {report['sources_checked']}")
        print(
            f"Supported Claims: {report['supported_count']} | "
            f"Unbacked Claims: {report['unbacked_count']} | "
            f"Open [TBD] Offenders: {report['tbd_count']} | "
            f"Provenance Advisories: {report['provenance_warning_count']}"
        )
        src_summary = ", ".join(
            f"{os.path.basename(s['file'])}({s['sha256_10']})" for s in report["source_hashes"][:8]
        )
        if len(report["source_hashes"]) > 8:
            src_summary += f", +{len(report['source_hashes']) - 8} more"
        print(f"Source Hashes: {src_summary}")

        if report["excluded_circular_sources"]:
            print(
                f"Auto-Excluded Self-Target from Directory Scan: "
                f"{', '.join(report['excluded_circular_sources'])}"
            )

        if report["provenance_warnings"]:
            print(
                "\n[~] SOURCE PROVENANCE ADVISORIES "
                "(Alert user -> decide to SKIP source OR WORK IN PARALLEL to separate core truth):"
            )
            for pw in report["provenance_warnings"]:
                print(f"  - {pw['file']}: {', '.join(pw['reasons'])}")

        if report["unbacked_claims"]:
            print("\n[!] UNBACKED CLAIMS (Must bind to source, replace with [TBD: ...], or remove):")
            for item in report["unbacked_claims"]:
                print(f"  - Line {item['line']} [{item['type']}]: {item['claim']}")

        if report["tbd_offenders"]:
            print("\n[?] OPEN [TBD] OFFENDERS (Tracked explicitly for user resolution):")
            for item in report["tbd_offenders"]:
                print(f"  - Line {item['line']}: {item['marker']}")

    if report["unbacked_count"] > 0:
        return 1
    if args.strict_provenance and report["provenance_warning_count"] > 0:
        return 3
    if args.fail_on_tbd and report["tbd_count"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
