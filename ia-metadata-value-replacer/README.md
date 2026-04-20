# IA Metadata Value Replacer

`ia_metadata_value_replacer.py` is a dedicated-purpose batch updater for Internet Archive item metadata.

Its job is narrow by design: take a plaintext list of IA identifiers, read a single replacement value from a text file, and apply that same value across the batch to one chosen metadata field. This makes it especially useful for cases like replacing a shared rights statement, note, source statement, or other repeated field content across many items.

The script is designed to avoid the main failure mode of shell-based metadata updates: quoting and escaping issues. Because the new metadata value is read directly from a file, quotes, apostrophes, punctuation, line breaks, and other special characters are preserved exactly as stored.

## What It Does

- Reads one IA identifier per line from a plaintext file.
- Reads the full contents of a text file as the new metadata value.
- Fetches the existing metadata for each item.
- Compares the current value with the new one.
- Skips unchanged items.
- Replaces scalar fields directly.
- Replaces a specific element of a repeatable field when you provide indexed syntax like `subject[0]`.
- Appends to a repeatable field when you explicitly pass `--append`.

## Safety Rules

- If a field has multiple existing values, the script will not guess which one to replace.
- For multi-value fields, you must either specify an index such as `notes[2]` or use `--append`.
- If you specify an index that does not exist, the script defaults to the last existing value in that field.
- If the field has no existing values and you use indexed syntax, the script writes to index `0`.
- Use `--dry-run` before making live changes.

## Requirements

- Python 3
- The `internetarchive` Python package
- Internet Archive credentials configured in the environment expected by the `internetarchive` package

If needed, install the package with:

```bash
pip install internetarchive
```

## Files

- Script: `ia_metadata_value_replacer.py`
- This README: `README.md`

## Usage

```bash
python ia_metadata_value_replacer.py IDENTIFIER_LIST FIELD VALUE_FILE [--append] [--dry-run]
```

Run the command from the `ia-rights-replacer` directory, or provide a relative path to the script from your current working directory.

## Arguments

- `IDENTIFIER_LIST`: Plaintext file containing one IA identifier per line.
- `FIELD`: The metadata field to update.
- `VALUE_FILE`: Text file whose full contents become the new metadata value.
- `--append`: Append the new value to an existing repeatable field.
- `--dry-run`: Report what would change without sending updates to IA.

## Field Syntax

### Scalar Field

Use a plain field name when the target field is single-value or when you want ordinary replacement:

```bash
rights
```

### Indexed Repeatable Field

Use bracket notation to target one element in a repeatable field:

```bash
subject[0]
notes[2]
```

If the requested index does not exist, the script falls back to the last existing value in that field.

### Append to a Repeatable Field

Use the plain field name together with `--append`:

```bash
notes --append
```

## Basic Workflow

1. Create a file containing one IA identifier per line.
2. Create a text file containing the replacement metadata value.
3. Run the script with `--dry-run`.
4. Review the output carefully.
5. Run the same command again without `--dry-run` to apply the update.

## Examples

### Replace a Shared Rights Statement

```bash
python ia_metadata_value_replacer.py list.txt rights rights.txt --dry-run
```

Apply the update for real:

```bash
python ia_metadata_value_replacer.py list.txt rights rights.txt
```

### Replace the First Subject Value Only

```bash
python ia_metadata_value_replacer.py list.txt subject[0] subject.txt --dry-run
```

### Replace the Third Notes Value, or the Last One if There Are Fewer Than Three

```bash
python ia_metadata_value_replacer.py list.txt notes[2] note.txt --dry-run
```

### Append a New Note to Every Item

```bash
python ia_metadata_value_replacer.py list.txt notes note.txt --append --dry-run
```

## Why This Avoids Quoting Problems

The replacement value is not passed inline on the shell command line. Instead, it is loaded from `VALUE_FILE` using Python file I/O.

That means content like this is handled safely:

```text
This item is provided "as is," subject to review.
Contact: archives@example.org
```

You do not need to escape embedded quotes, apostrophes, or most punctuation for shell parsing because the shell never sees the replacement value as a command argument.

## Output Behavior

For each identifier, the script prints one result line. Typical outcomes include:

- `unchanged: value already matches field`
- `unchanged: value already present in list`
- `would replace rights`
- `would replace subject[0]`
- `would append`
- `replaced rights`
- `appended`
- `error: ...`

At the end, the script prints a summary line:

```text
Summary: changed=12 unchanged=48 errors=0
```

## Limitations and Notes

- The script updates only one field per run.
- It is intentionally conservative around multi-value fields.
- It does not currently write a CSV or log file.
- It does not attempt rollback if some items fail partway through a batch.
- It relies on the behavior of the `internetarchive` Python package for metadata writes.

## AI Content Disclaimer

This script and its documentation were prepared with AI assistance and then reviewed and adapted for this codebase. Any automated or AI-assisted output should be reviewed by a human before use, especially when making batch metadata changes to production records.

## License

Assuming the intended request was for a GPL 3.0 statement rather than a "GPT 3.0" license, this script is released under the GNU General Public License, version 3.0 or later.

Copyright (C) 2026 Patrick R. Wallace <mail.prw@gmail.com>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or, at your option, any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
