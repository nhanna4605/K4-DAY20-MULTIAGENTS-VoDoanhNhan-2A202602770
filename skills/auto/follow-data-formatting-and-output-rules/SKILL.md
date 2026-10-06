---
name: follow-data-formatting-and-output-rules
description: Use when preparing output files or data to meet strict formatting, naming, and content rules.
---
1. Carefully read and understand all formatting rules and conventions for the output (e.g., JSON keys, CSV headers, date/time formats).
2. Normalize data values as required (e.g., region names canonicalized, timestamps converted to UTC and formatted exactly).
3. Convert monetary values to the required units and types (e.g., integer cents instead of floats).
4. Remove duplicates or filter data according to the rules before writing output.
5. Write output files with exact required filenames and structures.
6. Validate output files with schema checks or by loading them back to confirm correctness.
7. Include all required metadata fields with accurate counts and source references.
8. Test the output with the review bot or validator before submission.
Self-check:
- Are all output files named exactly as specified?
- Do all data fields conform to the required formats and types?
- Are metadata and summary fields accurate and complete?
