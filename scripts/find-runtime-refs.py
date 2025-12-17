#!/usr/bin/env python3
"""
Script to find all "runtime" references in the codebase.
Excludes known folders and files that should not be changed.

Usage:
    uv run scripts/find-runtime-refs.py
    uv run scripts/find-runtime-refs.py --count-only
    uv run scripts/find-runtime-refs.py --json
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import Iterator, NamedTuple

# ============================================================================
# CONFIGURATION - Exclusions
# ============================================================================

EXCLUDED_FOLDERS = {
    "node_modules",
    ".venv",
    ".git",
    "tickets",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "htmlcov",
    ".next",
    ".nuxt",
}

EXCLUDED_FILES = {
    "package-lock.json",
    "uv.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    ".DS_Store",
}

EXCLUDED_PATTERNS = [
    r"^terminology.*\.md$",
    r"^implementation.*\.md$",
    r".*\.lock$",
    r".*\.min\.js$",
    r".*\.min\.css$",
    r".*\.map$",
    r".*\.pyc$",
]

# File extensions to search
SEARCHABLE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".sh",
    ".bash",
    ".yml",
    ".yaml",
    ".md",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".example",
    ".template",
    "",  # Files without extension (like Makefile, Dockerfile)
}

# Files without extension to include
SEARCHABLE_FILENAMES = {
    "Makefile",
    "Dockerfile",
    "Containerfile",
    ".env",
    ".env.example",
    ".env.template",
    ".env.local",
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class Match(NamedTuple):
    file_path: str
    line_number: int
    line_content: str
    match_type: str  # 'agent-runtime', 'runtime-url', 'generic', etc.


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def should_exclude_folder(folder_name: str) -> bool:
    """Check if a folder should be excluded."""
    return folder_name in EXCLUDED_FOLDERS


def should_exclude_file(file_name: str) -> bool:
    """Check if a file should be excluded."""
    if file_name in EXCLUDED_FILES:
        return True

    for pattern in EXCLUDED_PATTERNS:
        if re.match(pattern, file_name, re.IGNORECASE):
            return True

    return False


def is_searchable_file(file_path: Path) -> bool:
    """Check if a file should be searched."""
    file_name = file_path.name

    # Check if it's a known searchable filename
    if file_name in SEARCHABLE_FILENAMES:
        return True

    # Check extension
    suffix = file_path.suffix.lower()
    return suffix in SEARCHABLE_EXTENSIONS


def classify_match(line: str) -> str:
    """Classify the type of runtime reference."""
    line_lower = line.lower()

    # Agent Runtime service references (NEED FIXING)
    if "agent-runtime" in line_lower or "agent_runtime" in line_lower:
        return "AGENT-RUNTIME-SERVICE"
    if "agentruntime" in line_lower:
        return "AGENT-RUNTIME-SERVICE"
    if "--runtime-url" in line_lower or "runtime-url" in line_lower:
        return "RUNTIME-URL-FLAG"
    if "runtime_url" in line_lower:
        return "RUNTIME-URL-VAR"
    if "runtimeapiclient" in line_lower:
        return "RUNTIME-API-CLIENT"
    if "logs-runtime" in line_lower or "restart-runtime" in line_lower:
        return "RUNTIME-MAKE-TARGET"
    if "runtime-data" in line_lower:
        return "RUNTIME-DATA-VOLUME"

    # Check context for Agent Runtime references
    if "runtime" in line_lower:
        # Look for patterns suggesting it's about the Agent Runtime service
        if any(word in line_lower for word in ["coordinator", "launcher", "agent", "session", "run", "poll"]):
            if "at runtime" not in line_lower and "runtime environment" not in line_lower:
                return "POSSIBLY-AGENT-RUNTIME"

    # Generic runtime (OK to keep)
    if "at runtime" in line_lower:
        return "GENERIC-AT-RUNTIME"
    if "@babel/runtime" in line_lower or "runtime-" in line_lower:
        return "NPM-PACKAGE"
    if "runtime environment" in line_lower:
        return "GENERIC-ENVIRONMENT"
    if "runtime config" in line_lower:
        return "GENERIC-CONFIG"
    if "about:debugging" in line_lower:
        return "BROWSER-URL"

    return "GENERIC-OTHER"


def find_runtime_references(root_dir: Path) -> Iterator[Match]:
    """Recursively find all runtime references in the codebase."""
    pattern = re.compile(r"runtime", re.IGNORECASE)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out excluded directories (modifies in-place to prevent descending)
        dirnames[:] = [d for d in dirnames if not should_exclude_folder(d)]

        for filename in filenames:
            if should_exclude_file(filename):
                continue

            file_path = Path(dirpath) / filename

            if not is_searchable_file(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        if pattern.search(line):
                            rel_path = file_path.relative_to(root_dir)
                            match_type = classify_match(line)
                            yield Match(
                                file_path=str(rel_path),
                                line_number=line_num,
                                line_content=line.rstrip(),
                                match_type=match_type,
                            )
            except (IOError, OSError) as e:
                print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)


def format_output(matches: list[Match], output_format: str = "text") -> str:
    """Format the matches for output."""
    if output_format == "json":
        return json.dumps([m._asdict() for m in matches], indent=2)

    if output_format == "count":
        # Group by match type
        by_type: dict[str, int] = {}
        for m in matches:
            by_type[m.match_type] = by_type.get(m.match_type, 0) + 1

        lines = ["=" * 60, "RUNTIME REFERENCE COUNT BY TYPE", "=" * 60]
        for match_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {match_type}: {count}")
        lines.append("-" * 60)
        lines.append(f"  TOTAL: {len(matches)}")
        return "\n".join(lines)

    # Default text format - group by file
    by_file: dict[str, list[Match]] = {}
    for m in matches:
        if m.file_path not in by_file:
            by_file[m.file_path] = []
        by_file[m.file_path].append(m)

    lines = ["=" * 80, "RUNTIME REFERENCES FOUND", "=" * 80, ""]

    # First show potentially problematic ones
    needs_review = [m for m in matches if m.match_type not in (
        "GENERIC-AT-RUNTIME", "NPM-PACKAGE", "GENERIC-ENVIRONMENT",
        "GENERIC-CONFIG", "BROWSER-URL", "GENERIC-OTHER"
    )]

    if needs_review:
        lines.append("## NEEDS REVIEW (Possibly Agent Runtime references)")
        lines.append("-" * 80)
        for m in needs_review:
            lines.append(f"[{m.match_type}] {m.file_path}:{m.line_number}")
            lines.append(f"    {m.line_content.strip()[:100]}")
            lines.append("")

    # Then show generic ones
    generic = [m for m in matches if m.match_type in (
        "GENERIC-AT-RUNTIME", "NPM-PACKAGE", "GENERIC-ENVIRONMENT",
        "GENERIC-CONFIG", "BROWSER-URL", "GENERIC-OTHER"
    )]

    if generic:
        lines.append("")
        lines.append("## OK TO KEEP (Generic runtime references)")
        lines.append("-" * 80)
        for m in generic:
            lines.append(f"[{m.match_type}] {m.file_path}:{m.line_number}")
            lines.append(f"    {m.line_content.strip()[:100]}")
            lines.append("")

    # Summary
    lines.append("")
    lines.append("=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"  Total references: {len(matches)}")
    lines.append(f"  Needs review: {len(needs_review)}")
    lines.append(f"  OK to keep: {len(generic)}")

    return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Determine output format
    output_format = "text"
    if "--json" in sys.argv:
        output_format = "json"
    elif "--count-only" in sys.argv or "--count" in sys.argv:
        output_format = "count"

    # Find project root (where this script is located)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Collect all matches
    matches = list(find_runtime_references(project_root))

    # Output results
    print(format_output(matches, output_format))

    # Exit with non-zero if there are references that need review
    needs_review = [m for m in matches if m.match_type not in (
        "GENERIC-AT-RUNTIME", "NPM-PACKAGE", "GENERIC-ENVIRONMENT",
        "GENERIC-CONFIG", "BROWSER-URL", "GENERIC-OTHER"
    )]

    if needs_review and output_format == "text":
        print(f"\n⚠️  Found {len(needs_review)} references that may need review.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
