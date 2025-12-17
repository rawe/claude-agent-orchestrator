#!/usr/bin/env python3
"""
Script to find all "job" references in the codebase for the Jobs → Agent Runs rename.
Excludes known folders and files that should not be changed.

Usage:
    uv run scripts/find-job-refs.py
    uv run scripts/find-job-refs.py --count-only
    uv run scripts/find-job-refs.py --json
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
    r"^implementation.*\.md$",  # Exclude implementation guides
    r"^RENAMING_STRATEGY\.md$",
    r".*\.lock$",
    r".*\.min\.js$",
    r".*\.min\.css$",
    r".*\.map$",
    r".*\.pyc$",
    r"^find-job-refs\.py$",  # Exclude this script itself
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
    match_type: str  # Classification category


# ============================================================================
# CLASSIFICATION LOGIC
# ============================================================================

# Categories that NEED FIXING (related to our Job concept)
NEEDS_FIXING_CATEGORIES = {
    "JOB-QUEUE-SERVICE",      # JobQueue class, job_queue singleton
    "JOB-CLASS",              # Job, JobCreate, JobType, JobStatus classes
    "JOB-ID-FIELD",           # job_id variable/field
    "JOB-API-ENDPOINT",       # /jobs endpoint, /launcher/jobs
    "JOB-METHOD",             # add_job, claim_job, get_job, etc.
    "JOB-CLIENT",             # JobClient class
    "JOB-POLLER",             # JobPoller class
    "JOB-EXECUTOR",           # JobExecutor class
    "JOB-SUPERVISOR",         # JobSupervisor class
    "JOB-REGISTRY",           # RunningJobsRegistry class
    "JOB-REQUEST-RESPONSE",   # JobCompletedRequest, etc.
    "JOB-LOG-MESSAGE",        # Log messages about jobs
    "JOB-DOCUMENTATION",      # Documentation about our Job concept
    "JOB-STOP-COMMAND",       # stop_jobs, stop_job related
    "JOB-TYPESCRIPT",         # TypeScript interfaces for jobs
    "POSSIBLY-OUR-JOB",       # Needs manual review
}

# Categories that are OK TO KEEP (unrelated to our Job concept)
OK_TO_KEEP_CATEGORIES = {
    "CRON-JOB",               # cron job, scheduled job (generic)
    "GITHUB-JOB",             # GitHub Actions job
    "GENERIC-JOB",            # Generic unrelated use of "job"
    "PRINT-JOB",              # Printing jobs
    "BACKGROUND-JOB",         # Generic background job references
}


def classify_match(line: str, file_path: str) -> str:
    """Classify the type of job reference."""
    line_lower = line.lower()
    file_lower = file_path.lower()

    # =========================================================================
    # OK TO KEEP - Check these first
    # =========================================================================

    # Cron jobs
    if "cron" in line_lower and "job" in line_lower:
        return "CRON-JOB"

    # GitHub Actions jobs
    if "github" in line_lower or ".github" in file_lower:
        if "job" in line_lower:
            return "GITHUB-JOB"

    # Print jobs
    if "print" in line_lower and "job" in line_lower:
        return "PRINT-JOB"

    # =========================================================================
    # NEEDS FIXING - Our Job concept
    # =========================================================================

    # Job Queue service
    if "jobqueue" in line_lower or "job_queue" in line_lower:
        return "JOB-QUEUE-SERVICE"

    # Job classes and types
    if re.search(r"\bjobtype\b", line_lower):
        return "JOB-CLASS"
    if re.search(r"\bjobstatus\b", line_lower):
        return "JOB-CLASS"
    if re.search(r"\bjobcreate\b", line_lower):
        return "JOB-CLASS"
    if re.search(r"\bclass\s+job\b", line_lower):
        return "JOB-CLASS"
    if re.search(r":\s*job\b", line_lower):  # Type annotation like : Job
        return "JOB-CLASS"

    # Job ID field
    if "job_id" in line_lower or "jobid" in line_lower:
        return "JOB-ID-FIELD"

    # API endpoints
    if re.search(r'["\'/]jobs["\'/]', line_lower) or re.search(r'["\'/]jobs\b', line_lower):
        return "JOB-API-ENDPOINT"
    if "/launcher/jobs" in line_lower:
        return "JOB-API-ENDPOINT"

    # Job methods
    if re.search(r"\badd_job\b", line_lower):
        return "JOB-METHOD"
    if re.search(r"\bclaim_job\b", line_lower):
        return "JOB-METHOD"
    if re.search(r"\bget_job\b", line_lower):
        return "JOB-METHOD"
    if re.search(r"\bupdate_job", line_lower):
        return "JOB-METHOD"
    if re.search(r"\bpoll_job\b", line_lower):
        return "JOB-METHOD"
    if re.search(r"\bexecute_job\b", line_lower):
        return "JOB-METHOD"
    if re.search(r"\bpending_jobs\b", line_lower):
        return "JOB-METHOD"
    if re.search(r"\ball_jobs\b", line_lower):
        return "JOB-METHOD"

    # Job client/poller/executor/supervisor classes
    if "jobclient" in line_lower:
        return "JOB-CLIENT"
    if "jobpoller" in line_lower:
        return "JOB-POLLER"
    if "jobexecutor" in line_lower:
        return "JOB-EXECUTOR"
    if "jobsupervisor" in line_lower:
        return "JOB-SUPERVISOR"
    if "runningjobsregistry" in line_lower or "running_jobs" in line_lower:
        return "JOB-REGISTRY"

    # Request/Response models
    if re.search(r"job(completed|failed|stopped)request", line_lower):
        return "JOB-REQUEST-RESPONSE"
    if re.search(r"job(completed|failed|stopped)response", line_lower):
        return "JOB-REQUEST-RESPONSE"

    # Stop jobs
    if "stop_jobs" in line_lower or "stop_job" in line_lower:
        return "JOB-STOP-COMMAND"

    # TypeScript interfaces (check file extension)
    if file_path.endswith(('.ts', '.tsx')):
        if re.search(r"\bjob\b", line_lower):
            # Check for interface/type definitions
            if "interface" in line_lower or "type " in line_lower or ": job" in line_lower:
                return "JOB-TYPESCRIPT"

    # Log messages about jobs
    if re.search(r'(log|logger|print|console)\s*[\.\(]', line_lower):
        if "job" in line_lower:
            return "JOB-LOG-MESSAGE"
    if re.search(r'f".*job', line_lower) or re.search(r"f'.*job", line_lower):
        return "JOB-LOG-MESSAGE"

    # Documentation files
    if file_path.endswith('.md'):
        # Check if it's about our Job concept
        if any(term in line_lower for term in [
            "job queue", "job_id", "jobtype", "jobstatus",
            "/jobs", "add_job", "claim_job", "get_job",
            "agent coordinator", "agent launcher", "session"
        ]):
            return "JOB-DOCUMENTATION"

    # Check context for our Job concept
    if "job" in line_lower:
        # Look for patterns suggesting it's about our Job concept
        context_words = ["coordinator", "launcher", "session", "poll", "queue",
                        "pending", "status", "run", "agent", "claim", "execute"]
        if any(word in line_lower for word in context_words):
            return "POSSIBLY-OUR-JOB"

    # =========================================================================
    # DEFAULT - Generic job reference
    # =========================================================================
    return "GENERIC-JOB"


def needs_fixing(match_type: str) -> bool:
    """Check if a match type needs fixing."""
    return match_type in NEEDS_FIXING_CATEGORIES


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


def find_job_references(root_dir: Path) -> Iterator[Match]:
    """Recursively find all job references in the codebase."""
    # Match "job" as a word or in compound words (job_id, JobQueue, etc.)
    pattern = re.compile(r"job", re.IGNORECASE)

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
                            match_type = classify_match(line, str(rel_path))
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

        lines = ["=" * 60, "JOB REFERENCE COUNT BY TYPE", "=" * 60]

        # Show NEEDS FIXING first
        lines.append("\n## NEEDS FIXING:")
        for match_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            if needs_fixing(match_type):
                lines.append(f"  {match_type}: {count}")

        # Then OK TO KEEP
        lines.append("\n## OK TO KEEP:")
        for match_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            if not needs_fixing(match_type):
                lines.append(f"  {match_type}: {count}")

        lines.append("-" * 60)
        total_needs_fixing = sum(c for t, c in by_type.items() if needs_fixing(t))
        total_ok = sum(c for t, c in by_type.items() if not needs_fixing(t))
        lines.append(f"  TOTAL NEEDS FIXING: {total_needs_fixing}")
        lines.append(f"  TOTAL OK TO KEEP: {total_ok}")
        lines.append(f"  TOTAL: {len(matches)}")
        return "\n".join(lines)

    # Default text format - group by category then file
    lines = ["=" * 80, "JOB REFERENCES FOUND", "=" * 80, ""]

    # First show ones that need fixing
    needs_review = [m for m in matches if needs_fixing(m.match_type)]

    if needs_review:
        lines.append("## NEEDS FIXING (Our Job concept → Rename to Run)")
        lines.append("-" * 80)

        # Group by type for better organization
        by_type: dict[str, list[Match]] = {}
        for m in needs_review:
            if m.match_type not in by_type:
                by_type[m.match_type] = []
            by_type[m.match_type].append(m)

        for match_type in sorted(by_type.keys()):
            lines.append(f"\n### {match_type}")
            for m in by_type[match_type]:
                lines.append(f"  {m.file_path}:{m.line_number}")
                lines.append(f"    {m.line_content.strip()[:100]}")
        lines.append("")

    # Then show generic ones
    generic = [m for m in matches if not needs_fixing(m.match_type)]

    if generic:
        lines.append("")
        lines.append("## OK TO KEEP (Unrelated job references)")
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
    lines.append(f"  Needs fixing: {len(needs_review)}")
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
    matches = list(find_job_references(project_root))

    # Output results
    print(format_output(matches, output_format))

    # Exit with non-zero if there are references that need fixing
    needs_review = [m for m in matches if needs_fixing(m.match_type)]

    if needs_review and output_format == "text":
        print(f"\n⚠️  Found {len(needs_review)} references that need fixing.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
