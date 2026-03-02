# Handover Instructions

## What is a Handover?

A handover is a condensed summary of a session's work, findings, and open questions.
It exists because agent context windows are finite. When a session gets too large to
continue effectively, we create a handover so the next session starts with full
context instead of re-discovering everything from scratch.

## When to Create One

- When the current session is ending but work is not finished
- When context is getting too large and a fresh session would be more effective
- When the user asks for one

## File Naming

```
HANDOVER-YYYY-MM-DD-NNN.md
```

- `YYYY-MM-DD` - the date of the session
- `NNN` - zero-padded increment starting at `001`, in case multiple handovers are created on the same day

Place in the same folder as the related design docs.

## What to Include

### 1. Branch and location
Which git branch, which folder the work is in.

### 2. What was done
Concrete list of changes made, with file paths. Not intentions - actual completed work.

### 3. What was found
Diagnostic output, test results, error messages - the raw evidence. Copy-paste the
actual output, don't paraphrase it. This is the most important part. Without it,
the next session will repeat the same investigations.

### 4. What is still open
The specific question or task that remains. Be precise. Not "fix resume" but
"why does the CLI return a new session_id when called with --resume in streaming mode?"

### 5. File map
List every relevant file with a one-line description. The next agent should not
need to search - they should know exactly where to look.

### 6. How to test
Copy-paste-ready commands to verify the current state and run relevant tests.

### 7. Suggested next steps
What to investigate, what approaches to try, what agent team structure works.

## What NOT to Include

- Full file contents (point to the file instead)
- History of abandoned approaches (unless they inform what NOT to try)
- Generic project documentation (link to it)

## How to Use a Handover

Start the next session with:

> "Continue from the handover at `docs/design/.../HANDOVER-YYYY-MM-DD-NNN.md`"

The agent reads the file and has full context to continue.
