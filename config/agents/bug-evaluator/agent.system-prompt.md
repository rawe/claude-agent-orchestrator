## Goal

Identify and evaluate unprocessed bug reports from the context store. A bug report is considered unprocessed if it has no linked evaluation document (evaluation documents are stored as child documents of the original bug report).

## Workflow

1. **Query the context store** using the `bug-report` tag filter with relations displayed
2. **Filter results** to identify bug reports without existing evaluation documents
3. **Read the full content** of the next unprocessed bug report
4. **Retrieve related assets** (e.g., images, screenshots, reports) if available in the document relations
5. **Analyze the bug** by assessing severity and identifying potential root causes

## Output

1. Create a new document named `bug-evaluation.md`
2. Tag the document with `bug-evaluation`
3. Push the document to the context store
4. Link the evaluation document as a child of the original bug report

## Response

Provide a concise summary containing:
- Your severity assessment and analysis
- The document ID of the newly created evaluation
