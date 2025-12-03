# Local Codebase Researcher Agent

Research agent for searching, analyzing, and understanding code in a specific codebase using iterative searches and content analysis.

**MCP Server:** None required (uses built-in file tools)

## How It Works

The agent follows an iterative research pattern optimized for codebase exploration:

1. **Initial Search** - Uses glob patterns to discover relevant files and grep to search code
2. **Fetch & Evaluate** - Reads file contents to understand code context and relevance
3. **Iterate** - Refines search queries if information is insufficient
4. **Generate Output** - Creates result markdown and sources JSON with absolute file paths and line numbers

## Setup

**No setup required.** This agent uses built-in file search and read capabilities.

Unlike web research agents, this agent operates on a local codebase directory that must be specified.

## Required Input

- **project_dir** (required): Absolute path to the codebase directory to search
- **question**: The research question about the codebase (e.g., "Where is authentication implemented?")
- **working_folder** (optional): Where to save results. Auto-generates to `research-results/[yyyy-mm-dd]-[topic]/` if not provided

## Output

Results are saved to `research-results/[yyyy-mm-dd]-[topic]/` by default:
- `research-sources.json` - Documented code locations with absolute paths and line numbers
- `research-result.md` - Research findings summary

## Key Features

- **Absolute Paths**: All file references are absolute paths for easy navigation
- **Line Numbers**: Includes specific line ranges for relevant code sections
- **Context-Aware**: Understands code relationships and interdependencies
- **Iterative Refinement**: Automatically refines searches when initial results are insufficient
- **Multi-Format Support**: Works with any code file type (JavaScript, Python, Go, etc.)

## Example Usage

```
project_dir: /path/to/myapp
question: "Where is the database connection initialized?"
```

Returns sources pointing to exact files and lines containing database initialization code.
