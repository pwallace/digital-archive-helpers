#!/usr/bin/env python3

# Copyright (C) 2026 Patrick R. Wallace <mail.prw@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Batch-replace one shared Internet Archive metadata value from a text file.

This script is intentionally narrow in scope: it exists to make it easy to
apply one common metadata value, such as a rights statement, to a large batch
of IA items while minimizing shell-quoting problems and accidental edits.

Key safety rules:
- The new metadata value is always read directly from a text file.
- Multi-value fields with multiple existing values require an explicit action:
    either address a single list entry by index or use --append.
- If an indexed replacement refers to a position beyond the current list,
    the script falls back to the last existing value, per the requested behavior.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

from internetarchive import get_item, modify_metadata


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the batch metadata updater."""
    parser = argparse.ArgumentParser(
        description=(
            "Replace or append one shared metadata value across a batch of "
            "Internet Archive items. The replacement text is read verbatim "
            "from a file, so quotes and other special characters are preserved."
        )
    )
    parser.add_argument(
        "identifier_list",
        help="Path to a plaintext file containing one IA identifier per line.",
    )
    parser.add_argument(
        "field",
        help=(
            "Metadata field to update. Use plain field names for scalar fields "
            "or indexed syntax such as subject[0] for list replacement."
        ),
    )
    parser.add_argument(
        "value_file",
        help="Path to a text file whose full contents become the new metadata value.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append the new value to a repeatable field instead of replacing a value.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without sending any metadata updates to IA.",
    )
    return parser.parse_args()


def parse_field_spec(field_spec: str) -> Tuple[str, Optional[int]]:
    """Parse a field name that may optionally include IA list index syntax.

    Examples:
    - rights -> ("rights", None)
    - subject[0] -> ("subject", 0)
    """
    if field_spec.endswith("]") and "[" in field_spec:
        base_field, raw_index = field_spec[:-1].split("[", 1)
        if not base_field:
            raise ValueError(f"Invalid field specification: {field_spec}")
        if not raw_index.isdigit():
            raise ValueError(f"Invalid list index in field specification: {field_spec}")
        return base_field, int(raw_index)
    return field_spec, None


def read_identifier_list(path: Path) -> list[str]:
    """Load non-empty identifiers from a plaintext file.

    Blank lines are ignored so a hand-edited list does not need to be cleaned
    before use.
    """
    identifiers = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            identifier = line.strip()
            if identifier:
                identifiers.append(identifier)
    return identifiers


def normalize_existing_value(raw_value):
    """Return metadata values in their original IA-compatible shape.

    IA metadata fields may be absent, scalar strings, or lists. This helper is
    mostly here to make the downstream intent explicit at the call site.
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        return raw_value
    return raw_value


def choose_index(existing_list: list, requested_index: int) -> int:
    """Choose the index to edit for a repeatable field.

    If the requested index is out of range, default to the last existing value.
    If the field has no existing values, fall back to index 0 so IA can create
    the first entry at that position.
    """
    if not existing_list:
        return 0
    if requested_index < len(existing_list):
        return requested_index
    return len(existing_list) - 1


def compare_scalar(raw_value, new_value: str) -> bool:
    """Return True when a scalar field already matches the requested value."""
    return isinstance(raw_value, str) and raw_value == new_value


def compare_single_list(raw_value, new_value: str) -> bool:
    """Return True when a single-value list already matches the requested value."""
    return isinstance(raw_value, list) and len(raw_value) == 1 and raw_value[0] == new_value


def process_item(
    identifier: str,
    field_name: str,
    requested_index: Optional[int],
    new_value: str,
    dry_run: bool,
    append_mode: bool,
) -> str:
    """Process one IA item and return a human-readable outcome string.

    The function intentionally branches by field shape and requested behavior:
    - append mode for repeatable fields
    - indexed replacement for explicit list edits
    - plain replacement for scalar fields

    This keeps the tool conservative. When a field already contains multiple
    values, the script refuses to guess which one should be replaced.
    """
    item = get_item(identifier)

    try:
        metadata = item.item_metadata["metadata"]
    except KeyError as exc:
        raise RuntimeError("item metadata unavailable") from exc

    current_value = normalize_existing_value(metadata.get(field_name))

    if append_mode and requested_index is not None:
        raise ValueError("Cannot use indexed field syntax together with --append.")

    if append_mode:
        # Avoid redundant writes when the batch value is already present.
        if isinstance(current_value, list) and new_value in current_value:
            return "unchanged: value already present in list"
        if compare_scalar(current_value, new_value):
            return "unchanged: value already matches field"
        if dry_run:
            return "would append"
        # append_list=True tells the IA client to add to an existing repeatable
        # field rather than replacing the whole field value.
        response = modify_metadata(identifier, metadata={field_name: new_value}, append_list=True)
        return format_response(response, "appended")

    if requested_index is not None:
        # Treat an existing scalar as a one-item list so callers can still use
        # indexed syntax against fields that only currently have one value.
        existing_list = current_value if isinstance(current_value, list) else ([] if current_value is None else [current_value])
        target_index = choose_index(existing_list, requested_index)
        if existing_list and existing_list[target_index] == new_value:
            return f"unchanged: {field_name}[{target_index}] already matches"
        if dry_run:
            return f"would replace {field_name}[{target_index}]"
        # The IA Python client supports indexed keys such as subject[0], which
        # allows targeted replacement within list metadata without rebuilding
        # the entire field manually.
        response = modify_metadata(
            identifier,
            metadata={f"{field_name}[{target_index}]": new_value},
        )
        return format_response(response, f"replaced {field_name}[{target_index}]")

    if isinstance(current_value, list):
        if len(current_value) > 1:
            raise ValueError(
                f"Field '{field_name}' has {len(current_value)} values. "
                "Use indexed syntax like field[0] to replace one value or use --append."
            )
        # A one-value list is safe to replace without forcing the user to write
        # explicit index syntax on the command line.
        if compare_single_list(current_value, new_value):
            return "unchanged: single list value already matches"
        if dry_run:
            return f"would replace {field_name}[0]"
        response = modify_metadata(
            identifier,
            metadata={f"{field_name}[0]": new_value},
        )
        return format_response(response, f"replaced {field_name}[0]")

    if compare_scalar(current_value, new_value):
        return "unchanged: value already matches field"

    if dry_run:
        return f"would replace {field_name}"

    response = modify_metadata(identifier, metadata={field_name: new_value})
    return format_response(response, f"replaced {field_name}")


def format_response(response, success_message: str) -> str:
    """Normalize IA API responses into a short status line for batch output."""
    status_code = getattr(response, "status_code", None)
    if status_code == 200:
        return success_message
    return f"error: IA returned status {status_code}"


def main() -> int:
    """Run the batch metadata update workflow and print a compact summary."""
    args = parse_args()

    identifier_list_path = Path(args.identifier_list)
    value_file_path = Path(args.value_file)

    if not identifier_list_path.exists():
        print(f"Error: identifier list not found: {identifier_list_path}", file=sys.stderr)
        return 1
    if not value_file_path.exists():
        print(f"Error: value file not found: {value_file_path}", file=sys.stderr)
        return 1

    try:
        field_name, requested_index = parse_field_spec(args.field)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not field_name:
        print("Error: field name cannot be empty.", file=sys.stderr)
        return 1

    # Read the replacement text exactly as stored on disk. This avoids shell
    # quoting problems and preserves embedded quotes or other special
    # characters in the metadata value.
    new_value = value_file_path.read_text(encoding="utf-8")
    identifiers = read_identifier_list(identifier_list_path)

    if not identifiers:
        print("Error: identifier list is empty.", file=sys.stderr)
        return 1

    changed_count = 0
    unchanged_count = 0
    error_count = 0

    for identifier in identifiers:
        try:
            # Each item is handled independently so one failure does not abort
            # the whole batch.
            result = process_item(
                identifier=identifier,
                field_name=field_name,
                requested_index=requested_index,
                new_value=new_value,
                dry_run=args.dry_run,
                append_mode=args.append,
            )
        except Exception as exc:
            error_count += 1
            print(f"{identifier}: error: {exc}")
            continue

        print(f"{identifier}: {result}")
        if result.startswith("unchanged"):
            unchanged_count += 1
        elif result.startswith("error"):
            error_count += 1
        else:
            changed_count += 1

    print(
        f"Summary: changed={changed_count} unchanged={unchanged_count} errors={error_count}"
    )
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())