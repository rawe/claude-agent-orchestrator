#!/usr/bin/env python3
"""
Find and classify "launcher" references in the codebase for the
Agent Launcher → Agent Runner rename.

Usage:
    uv run scripts/find-launcher-refs.py           # Detailed report
    uv run scripts/find-launcher-refs.py --count-only  # Summary only
    uv run scripts/find-launcher-refs.py --json    # JSON output
"""

import os
import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Generator

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent

# Folders to completely skip
EXCLUDED_FOLDERS = {
    "node_modules",
    ".venv",
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    "tickets",  # Historical planning
}

# Files to skip
EXCLUDED_FILES = {
    "package-lock.json",
    "uv.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".DS_Store",
}

# Filename patterns to skip (these are meta-documents about the rename itself)
EXCLUDED_FILENAME_PATTERNS = [
    r"^terminology.*\.md$",
    r"^implementation.*\.md$",
    r"^find-launcher-refs\.py$",  # This script
    r"^RENAMING_STRATEGY\.md$",
]

# File extensions to search
SEARCHABLE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".sh",
    ".bash",
    ".env",
    ".env.example",
    "",  # Files without extension (like shell scripts)
}

# =============================================================================
# Classification
# =============================================================================

# Categories that NEED FIXING
NEEDS_FIXING_CATEGORIES = {
    "AGENT-LAUNCHER-DIR",
    "AGENT-LAUNCHER-SCRIPT",
    "LAUNCHER-API-ENDPOINT",
    "LAUNCHER-CLASS",
    "LAUNCHER-VARIABLE",
    "LAUNCHER-ENV-VAR",
    "LAUNCHER-FUNCTION",
    "LAUNCHER-IMPORT",
    "LAUNCHER-COMMENT",
    "LAUNCHER-UI-TEXT",
    "LAUNCHER-MERMAID",
    "LAUNCHER-DOC-REF",
}

# Categories that are OK TO KEEP
OK_TO_KEEP_CATEGORIES = {
    "EXTERNAL-PACKAGE",
    "BROWSER-API",
    "GENERIC-OTHER",
}


def classify_match(line: str, filepath: str) -> str:
    """Classify a line containing 'launcher' into a category."""
    line_lower = line.lower()
    filepath_lower = filepath.lower()

    # Check for Mermaid diagram participants
    if "participant" in line_lower and "launcher" in line_lower:
        return "LAUNCHER-MERMAID"

    # Check for directory/path references
    if "agent-launcher" in line_lower or "agent_launcher" in line_lower:
        if "/servers/agent-launcher" in filepath_lower:
            return "AGENT-LAUNCHER-DIR"
        return "LAUNCHER-DOC-REF"

    # Check for environment variables (UPPERCASE)
    if re.search(r"LAUNCHER_[A-Z_]+", line):
        return "LAUNCHER-ENV-VAR"

    # Check for class names (PascalCase)
    if re.search(r"Launcher[A-Z][a-zA-Z]*|[A-Z][a-zA-Z]*Launcher", line):
        return "LAUNCHER-CLASS"

    # Check for API endpoints
    if re.search(r'["\'/]launcher[/"\']|["\'/]launchers[/"\']', line_lower):
        return "LAUNCHER-API-ENDPOINT"

    # Check for function names
    if re.search(r"def\s+\w*launcher\w*|get_launcher|is_launcher|register_launcher|remove_launcher", line_lower):
        return "LAUNCHER-FUNCTION"

    # Check for imports
    if re.search(r"from\s+.*launcher|import\s+.*launcher", line_lower):
        return "LAUNCHER-IMPORT"

    # Check for variable names
    if re.search(r"launcher_id|launcher_registry|launcherId|launcherService|launcher\s*=|launcher\s*:", line_lower):
        return "LAUNCHER-VARIABLE"

    # Check for UI text (strings with "Launcher" in them)
    if re.search(r'["\'].*[Ll]auncher.*["\']', line):
        return "LAUNCHER-UI-TEXT"

    # Documentation references
    if filepath.endswith(".md"):
        return "LAUNCHER-DOC-REF"

    # Comments in code
    if re.search(r"#.*launcher|//.*launcher|/\*.*launcher|\*.*launcher", line_lower):
        return "LAUNCHER-COMMENT"

    # Default: treat as needing investigation
    return "LAUNCHER-VARIABLE"


# =============================================================================
# File Discovery
# =============================================================================

def should_skip_folder(folder_name: str) -> bool:
    """Check if a folder should be skipped."""
    return folder_name in EXCLUDED_FOLDERS


def should_skip_file(filename: str) -> bool:
    """Check if a file should be skipped."""
    if filename in EXCLUDED_FILES:
        return True
    for pattern in EXCLUDED_FILENAME_PATTERNS:
        if re.match(pattern, filename, re.IGNORECASE):
            return True
    return False


def is_searchable_file(filepath: Path) -> bool:
    """Check if a file should be searched."""
    ext = filepath.suffix.lower()
    # Handle extensionless files (like shell scripts)
    if ext == "" and filepath.is_file():
        # Check if it's a text file by trying to read first line
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                # Check for shebang indicating a script
                if first_line.startswith("#!"):
                    return True
        except:
            pass
        return False
    return ext in SEARCHABLE_EXTENSIONS


def find_files(root: Path) -> Generator[Path, None, None]:
    """Find all searchable files in the project."""
    for dirpath, dirnames, filenames in os.walk(root):
        # Modify dirnames in-place to skip excluded folders
        dirnames[:] = [d for d in dirnames if not should_skip_folder(d)]

        for filename in filenames:
            if should_skip_file(filename):
                continue
            filepath = Path(dirpath) / filename
            if is_searchable_file(filepath):
                yield filepath


# =============================================================================
# Search
# =============================================================================

@dataclass
class Match:
    filepath: str
    line_number: int
    line: str
    category: str


@dataclass
class SearchResults:
    matches: list[Match] = field(default_factory=list)
    files_with_matches: set[str] = field(default_factory=set)

    def add(self, match: Match):
        self.matches.append(match)
        self.files_with_matches.add(match.filepath)

    def by_category(self) -> dict[str, list[Match]]:
        result: dict[str, list[Match]] = {}
        for m in self.matches:
            if m.category not in result:
                result[m.category] = []
            result[m.category].append(m)
        return result

    def needs_fixing(self) -> list[Match]:
        return [m for m in self.matches if m.category in NEEDS_FIXING_CATEGORIES]

    def ok_to_keep(self) -> list[Match]:
        return [m for m in self.matches if m.category in OK_TO_KEEP_CATEGORIES]


def search_file(filepath: Path) -> list[Match]:
    """Search a file for launcher references."""
    matches = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                if re.search(r"launcher", line, re.IGNORECASE):
                    category = classify_match(line, str(filepath))
                    matches.append(Match(
                        filepath=str(filepath.relative_to(PROJECT_ROOT)),
                        line_number=line_num,
                        line=line.rstrip(),
                        category=category,
                    ))
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
    return matches


def search_all() -> SearchResults:
    """Search all files in the project."""
    results = SearchResults()
    for filepath in find_files(PROJECT_ROOT):
        for match in search_file(filepath):
            results.add(match)
    return results


# =============================================================================
# Output
# =============================================================================

def print_detailed_report(results: SearchResults):
    """Print a detailed report of all matches."""
    by_category = results.by_category()

    print("=" * 80)
    print("LAUNCHER REFERENCES REPORT")
    print("=" * 80)
    print()

    # Summary
    print("SUMMARY")
    print("-" * 40)
    print(f"Total matches: {len(results.matches)}")
    print(f"Files with matches: {len(results.files_with_matches)}")
    print(f"Needs fixing: {len(results.needs_fixing())}")
    print(f"OK to keep: {len(results.ok_to_keep())}")
    print()

    # By category
    print("BY CATEGORY")
    print("-" * 40)

    # Needs fixing first
    print("\n### NEEDS FIXING ###\n")
    for cat in sorted(NEEDS_FIXING_CATEGORIES):
        if cat in by_category:
            print(f"  {cat}: {len(by_category[cat])}")

    # OK to keep
    print("\n### OK TO KEEP ###\n")
    for cat in sorted(OK_TO_KEEP_CATEGORIES):
        if cat in by_category:
            print(f"  {cat}: {len(by_category[cat])}")

    # Unknown categories
    unknown = set(by_category.keys()) - NEEDS_FIXING_CATEGORIES - OK_TO_KEEP_CATEGORIES
    if unknown:
        print("\n### UNCATEGORIZED ###\n")
        for cat in sorted(unknown):
            print(f"  {cat}: {len(by_category[cat])}")

    print()

    # Detailed matches by file
    print("DETAILED MATCHES BY FILE")
    print("-" * 40)

    # Group by file
    by_file: dict[str, list[Match]] = {}
    for m in results.matches:
        if m.filepath not in by_file:
            by_file[m.filepath] = []
        by_file[m.filepath].append(m)

    for filepath in sorted(by_file.keys()):
        matches = by_file[filepath]
        print(f"\n{filepath} ({len(matches)} matches)")
        for m in matches:
            # Truncate long lines
            line_preview = m.line[:80] + "..." if len(m.line) > 80 else m.line
            print(f"  L{m.line_number}: [{m.category}] {line_preview}")


def print_count_only(results: SearchResults):
    """Print just the summary counts."""
    by_category = results.by_category()

    print("LAUNCHER REFERENCES SUMMARY")
    print("=" * 40)
    print(f"Total matches: {len(results.matches)}")
    print(f"Files with matches: {len(results.files_with_matches)}")
    print()

    print("NEEDS FIXING:")
    total_fixing = 0
    for cat in sorted(NEEDS_FIXING_CATEGORIES):
        if cat in by_category:
            count = len(by_category[cat])
            total_fixing += count
            print(f"  {cat}: {count}")
    print(f"  TOTAL: {total_fixing}")
    print()

    print("OK TO KEEP:")
    total_ok = 0
    for cat in sorted(OK_TO_KEEP_CATEGORIES):
        if cat in by_category:
            count = len(by_category[cat])
            total_ok += count
            print(f"  {cat}: {count}")
    print(f"  TOTAL: {total_ok}")


def print_json(results: SearchResults):
    """Print results as JSON."""
    output = {
        "summary": {
            "total_matches": len(results.matches),
            "files_with_matches": len(results.files_with_matches),
            "needs_fixing": len(results.needs_fixing()),
            "ok_to_keep": len(results.ok_to_keep()),
        },
        "by_category": {
            cat: len(matches)
            for cat, matches in results.by_category().items()
        },
        "matches": [
            {
                "filepath": m.filepath,
                "line_number": m.line_number,
                "line": m.line,
                "category": m.category,
            }
            for m in results.matches
        ],
    }
    print(json.dumps(output, indent=2))


# =============================================================================
# Main
# =============================================================================

def main():
    args = sys.argv[1:]

    print("Searching for launcher references...", file=sys.stderr)
    results = search_all()
    print(f"Found {len(results.matches)} matches in {len(results.files_with_matches)} files", file=sys.stderr)
    print(file=sys.stderr)

    if "--json" in args:
        print_json(results)
    elif "--count-only" in args:
        print_count_only(results)
    else:
        print_detailed_report(results)


if __name__ == "__main__":
    main()
