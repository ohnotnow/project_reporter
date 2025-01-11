# Project Reporter

A Python tool that generates a consolidated report by merging dynamic project data with manual input from a CSV file. The report provides insights into project details, Laravel/PHP versions, and upgrade statuses.

## Repository

GitHub: [ohnotnow/project_reporter](https://github.com/ohnotnow/project_reporter)

## Features

- Scans project directories for Laravel and PHP versions.
- Identifies available upgrade branches.
- Merges dynamic project data with manual CSV input.
- Outputs reports in both CSV and Markdown formats.

## Installation

Ensure Python is installed on your system. Install dependencies using [uv](https://docs.astral.sh/uv/):

### MacOS, Ubuntu, Windows (via CLI)

```bash
git clone https://github.com/ohnotnow/project_reporter.git
cd project_reporter
uv sync
```

## Usage

1. **Prepare Input CSV**
   - Navigate to the `inputs` folder.
   - Rename `project_details_example.csv` to `project_details.csv`.
   - Edit the file to reflect your project details.

2. **Generate Report**

### Basic Command
```bash
uv run main.py
```

### Optional Arguments

- `--pull`: Perform `git pull` before retrieving branches.
- `--base-path <path>`: Specify the base directory for project search (default: current directory).
- `--manual-csv <path>`: Path to the manual CSV file (default: `inputs/project_details.csv`).
- `--output-dir <path>`: Directory to save the output report (default: `outputs`).

### Example
```bash
uv run main.py --pull --base-path /path/to/projects --output-dir /custom/outputs
```

## Output

- CSV report: Generated in the specified `outputs` folder with the format `YYYY-MM-DD_report.csv`.
- Markdown report: Also saved in the `outputs` folder as `YYYY-MM-DD_report.md`.

## License

MIT License

Copyright (c) 2025 ohnotnow
