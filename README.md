# digital-archive-helpers

A collection of small Python utilities for tasks related to building and maintaining [Internet Archive](https://archive.org) collections, batch processing files and metadata, verifying data integrity, and automating other repetitive work in a digital archives context.

Each tool lives in its own subdirectory with a detailed README.

---

## Internet Archive tools

### [ia-metadata-value-replacer](ia-metadata-value-replacer)
Using a plaintext list of IA identifiers, reads a single replacement value from a text file and applies that same value across the batch to one chosen metadata field. This makes it especially useful for cases like replacing a shared rights statement, note, source statement, or other repeated field content across many items. The script is designed to avoid the main failure mode of shell-based metadata updates: quoting and escaping issues. Because the new metadata value is read directly from a file, quotes, apostrophes, punctuation, line breaks, and other special characters are preserved exactly as stored.

### [ia-missing-item-checker](ia-missing-item-checker/)
Finds Internet Archive identifiers present in a local metadata corpus (one or more CSVs exported via IA's Advanced Search) that are absent from a source list. Useful for identifying items that exist in a local metadata export but have not yet been uploaded to, or confirmed in, an IA collection.

### [ia-item-metadata-to-csv](ia-item-metadata-to-csv/)
Searches Internet Archive using a Lucene query and exports the metadata of all matching items to a CSV. Configurable fields; defaults to `identifier`, `title`, `creator`, `date`, and `description`. Useful for retrieving custom metadata fields not returned via normal Advanced Search.

### [ia-item-csv-lister](ia-item-csv-lister/)
Reads a plain-text list of IA identifiers, fetches the file listing for each item via the IA API, and writes results to a CSV where each row is an item and each column is a file extension. Standard IA-generated files are automatically excluded.

### [ia-file-metadata-tool](ia-file-metadata-tool/)
List, set metadata, download, or export `files.xml` for individual files within specific IA items. Supports filtering by filename pattern (regex) or file format. Operates on a single item or a batch list. Only files with `source="original"` are processed.

### [ia-to-iiif-manifest-creator](ia-to-iiif-manifest-creator/)
Generates a IIIF Presentation API 2.x Collection manifest JSON from a CSV of IA identifiers and item labels. Intended for uploading to GitHub and ingesting into a transcription platform such as [FromThePage](https://fromthepage.com).

---

## Archive deduplication & integrity

These tools form a workflow for comparing files on a local filesystem (DarkArchive) against a checksum export from Archive-It Vault. A higher-level overview and recommended workflow are in [archive-deduping/README.md](archive-deduping/README.md).

### [csv-checksum-lister](archive-deduping/csv-checksum-lister/)
Recursively walks a directory tree, computes checksums for all files, and writes results to a CSV (`checksum`, `path`, `filename`). Read-only; does not modify the source filesystem.

### [vault-checksum-csv-converter](archive-deduping/vault-checksum-csv-converter/)
Converts a plain-text checksum export (as downloaded from Archive-It Vault) into the same three-column CSV format used by `csv-checksum-lister` and `csv-checksum-comparator`.

### [csv-checksum-comparator](archive-deduping/csv-checksum-comparator/)
Compares two checksum CSVs (e.g., local vs. Vault) and produces a differences CSV listing files missing from one side or the other. Useful for verifying filesystem migrations and validating backups.

### [local-to-vault-comparator](archive-deduping/local-to-vault-comparator/)
Compares two plain-text path lists (local storage and vault storage) and produces a CSV showing which files appear in both and which appear in only one. Top-level directory names are ignored; matching is based on remaining path segments.

---

## File discovery & matching

### [file-finder](file-finder/)
Locates files or directories from a path list within a large directory tree. Extracts the lowest-level element from each path, searches recursively, and writes matches to `files-output.csv` (filename matches) and `dir-output.csv` (directory matches).

### [fuzzy-file-finder](fuzzy-file-finder/)
Matches a target list of files or directories against a recursive directory listing using a cascade of strategies: name-only, case-sensitive, case-insensitive, and fuzzy (via `fuzzywuzzy`, threshold ≥ 60). Outputs results to CSV. Useful when file paths don't match exactly.

---

## Metadata extraction

### [tiff-metadata-extractor](tiff-metadata-extractor/)
Recursively scans a directory for TIFF files and writes their embedded metadata to a CSV. Case-insensitive extension matching (`.tif`, `.tiff`). Does not modify source files.

### [doc-scanner](doc-scanner/)
Recursively scans a directory for `.txt`, `.docx`, and `.doc` files, performs a case-insensitive substring search, and reports matches with line numbers or paragraph indices. Optionally writes results to a file and copies matched files to a folder.

---

## Data cleaning & transformation

### [list-cleaner](list-cleaner/)
Two utilities for preparing file path lists:
- **`list-cleaner.py`** — strips leading file sizes from a recursive directory listing (e.g., `rclone ls` output) and sorts the result; optionally filters to files or directories only.
- **`convert-dos-to-linux-paths.py`** — converts DOS-style backslash paths to Linux-style forward-slash paths.

### [text-collapser](text-collapser/)
Removes all empty lines from a text file and writes the result to a new file. The original file is not modified.

---

## Audio & video processing

### [audio-track-concatenator](audio-track-concatenator/)
Discovers audio files in a directory (sorted alphabetically), concatenates them into a single output file using `pydub`. Requires `ffmpeg`.

### [video-tools](video-tools/)
Two scripts for video processing. See [video-tools/README.md](video-tools/) for details.
- **`video-concatenator`** — transcodes all video files in a directory to a standard format and concatenates them into a single output file.
- **`video-keyframe-splitter`** — transcodes a video file to insert periodic keyframes, then splits it into segments at those boundaries.

### [whisper-transcriber](whisper-transcriber/)
Transcribes an audio file to text using OpenAI's Whisper model. Automatically splits files larger than 25 MB into chunks and joins the results. Supports all Whisper model sizes (`tiny` through `large`).

---

## Requirements

Most tools require only Python 3.x and the standard library. Exceptions:

| Tool | Additional requirements |
|---|---|
| `doc-scanner` | `python-docx` |
| `fuzzy-file-finder` | `fuzzywuzzy`, `python-Levenshtein` |
| `audio-track-concatenator` | `pydub`, `ffmpeg` |
| `video-concatenator`, `video-keyframe-splitter` | `ffmpeg` |
| `whisper-transcriber` | `openai-whisper`, `pydub`, `ffmpeg` |
| `ia-*` tools | `internetarchive` |
