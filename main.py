import os
import json
import re
import sys
import subprocess
import argparse
from datetime import datetime
import pandas as pd
#from markdown_pdf import MarkdownPdf, Section

current_laravel_version = "11.0"
current_php_version = "8.4"

def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate a report by merging dynamic project data with a manual CSV."
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="If set, perform 'git pull' before retrieving branches."
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",  # Default to current directory
        help="Base directory to search for projects."
    )
    parser.add_argument(
        "--manual-json",
        type=str,
        default="inputs/project_details.json",
        help="Path to the manual JSON file."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory to save the output report."
    )

    parser.add_argument(
        "--add-new",
        action="store_true",
        help="If set, add a new project to the local JSON file and exit."
    )

    return parser.parse_args()

def add_new_project_to_manual_json(json_path: str) -> None:
    with open(json_path, 'r') as file:
        data = json.load(file)

    local_dir = input("Enter the local directory of the new project: ")
    project_name = input("Enter the project name: ")
    audience = input("Enter the audience: ")
    busy_times = input("Enter the busy times: ")
    external_user_access = input("Enter the external user access: ")
    criticallity = input("Enter the criticallity: ")
    workaround = input("Enter the workaround: ")

    data.append({
        "Local Directory": local_dir,
        "Project Name": project_name,
        "Laravel": "_",
        "PHP": "_",
        "Upgrade Branch": "_",
        "Flux?": "N",
        "Notes": "",
        "Audience": audience,
        "Busy times": busy_times,
        "External User Access?": external_user_access,
        "Criticallity": criticallity,
        "Workaround": workaround
    })

    with open(json_path, 'w') as file:
        json.dump(data, file, indent=4)


def validate_projects_in_manual_json(projects, manual_df):
    """
    Validates that all known projects are present in the manual JSON's 'Local Directory' column.

    Args:
        projects (list): List of known project directory names.
        manual_df (pd.DataFrame): DataFrame containing the manual JSON data.

    Raises:
        SystemExit: Exits the script if any project is missing.
    """
    # Extract the 'Local Directory' column as a set for efficient lookup
    manual_projects_set = set(manual_df['Local Directory'].dropna().astype(str))

    # Identify missing projects
    missing_projects = [project for project in projects if project not in manual_projects_set]

    if missing_projects:
        print("**Warning:** The following known projects are missing in the manual JSON file:")
        for project in missing_projects:
            print(f" - {project}")
        print("\nPlease update the manual JSON file to include all known projects before proceeding.")
        sys.exit(1)  # Exit the script with a non-zero status to indicate an error
    else:
        print("✅ All known projects are present in the manual JSON file.")


def get_git_branches(project_path, pull=False):
    """
    Retrieves all Git branch names in the given project directory.
    Optionally performs a 'git pull' to update remote branches.

    Args:
        project_path (str): Path to the project directory.
        pull (bool): Whether to perform 'git pull' before fetching branches.

    Returns:
        list: A list of branch names.
    """
    try:
        if pull:
            print(f"Performing 'git pull' in {project_path}...")
            pull_result = subprocess.run(
                ['git', 'pull'],
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            print(pull_result.stdout)

        print(f"Retrieving branches in {project_path}...")
        result = subprocess.run(
            ['git', 'branch'],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        branches = result.stdout.splitlines()
        # Clean branch names by removing leading '*' and whitespace
        branches = [branch.strip().lstrip('* ').strip() for branch in branches]
        return branches
    except subprocess.CalledProcessError as e:
        print(f"Git command failed in {project_path}: {e.stderr.strip()}")
        return []
    except Exception as e:
        print(f"Error retrieving git branches in {project_path}: {e}")
        return []

def extract_laravel_version_from_branch(branch_name):
    """
    Extracts the Laravel version number from a branch name if it indicates a Laravel upgrade.
    """
    pattern = r'^upgrade/(?:laravel)?L?(\d+(?:\.\d+)?)$'
    match = re.match(pattern, branch_name, re.IGNORECASE)
    if match:
        version_str = match.group(1)
        try:
            version = float(version_str)
            return version
        except ValueError:
            return None
    return None

def extract_versions(base_path, perform_pull, projects):
    data = []

    for entry in os.scandir(base_path):
        if entry.is_dir():
            composer_path = os.path.join(entry.path, 'composer.json')

            if os.path.isfile(composer_path):
                project_name = entry.name
                if project_name not in projects:
                    continue

                laravel_version = "Unknown"
                php_version = "Unknown"
                highest_upgrade_version = ""

                try:
                    with open(composer_path, 'r') as f:
                        content = f.read()

                        laravel_match = re.search(r'"laravel/framework":\s*"([^"]+)"', content)
                        if laravel_match:
                            laravel_version = laravel_match.group(1)

                        php_match = re.search(r'"php":\s*"([^"]+)"', content)
                        if php_match:
                            php_version = php_match.group(1)
                except Exception as e:
                    print(f"Error reading {composer_path}: {e}")
                    continue

                current_version_str = laravel_version.lstrip('^').strip()
                try:
                    current_version = float(current_version_str)
                except ValueError:
                    current_version = 0

                branches = get_git_branches(entry.path, perform_pull)
                upgrade_versions = []

                for branch in branches:
                    if branch.startswith('upgrade/'):
                        version = extract_laravel_version_from_branch(branch)
                        if version and version > current_version:
                            upgrade_versions.append(version)

                if upgrade_versions:
                    highest_version = max(upgrade_versions)
                    if highest_version.is_integer():
                        highest_upgrade_version = f"laravel{int(highest_version)}"
                    else:
                        highest_upgrade_version = f"laravel{highest_version}"
                else:
                    highest_upgrade_version = ""

                data.append({
                    'Local Directory': project_name,  # Assuming 'Local Directory' corresponds to project_name
                    'Project Name': project_name,  # Include both if necessary
                    'Laravel Version': laravel_version,
                    'PHP Version': php_version,
                    'Upgrade Laravel Version': highest_upgrade_version
                })

    return data

def dynamic_data_to_dataframe(dynamic_data):
    dynamic_df = pd.DataFrame(dynamic_data)
    return dynamic_df

def read_manual_json(manual_json_path):
    try:
        manual_df = pd.read_json(manual_json_path)
        return manual_df
    except Exception as e:
        print(f"Error reading manual JSON file: {e}")
        return pd.DataFrame()

def merge_dataframes(manual_df, dynamic_df):
    # Merge on 'Local Directory'
    merged_df = pd.merge(manual_df, dynamic_df, on='Local Directory', how='outer', suffixes=('_manual', '_dynamic'))
    return merged_df

def replace_placeholders(merged_df):
    # Replace 'Laravel' with 'Laravel Version' from dynamic data
    if 'Laravel Version' in merged_df.columns:
        merged_df['Laravel'] = merged_df['Laravel Version'].fillna(merged_df['Laravel'])
        merged_df.drop(['Laravel Version'], axis=1, inplace=True)

    # Replace 'PHP' with 'PHP Version' from dynamic data
    if 'PHP Version' in merged_df.columns:
        merged_df['PHP'] = merged_df['PHP Version'].fillna(merged_df['PHP'])
        merged_df.drop(['PHP Version'], axis=1, inplace=True)

    # Replace 'Upgrade Branch' with 'Upgrade Laravel Version' from dynamic data
    if 'Upgrade Laravel Version' in merged_df.columns:
        merged_df['Upgrade Branch'] = merged_df['Upgrade Laravel Version'].fillna(merged_df['Upgrade Branch'])
        merged_df.drop(['Upgrade Laravel Version'], axis=1, inplace=True)

    return merged_df

def finalize_report(merged_df):
    # Replace any remaining NaN values with appropriate defaults
    merged_df.fillna('N/A', inplace=True)

    # Define the desired column order based on the manual CSV
    desired_order = [
        'Project Name',
        'Laravel',
        'PHP',
        'Upgrade Branch',
        'Flux?',
        'Notes',
        'Audience',
        'Busy times',
        'External User Access?',
        'Criticallity',
        'Workaround'
    ]

    # Add any additional columns that exist in the merged_df but not in desired_order
    if 'Project Name_manual' in merged_df.columns:
        merged_df['Project Name'] = merged_df['Project Name_manual']
        merged_df.drop(['Project Name_manual', 'Project Name_dynamic'], axis=1, errors='ignore', inplace=True)

    # additional_cols = [col for col in merged_df.columns if col not in desired_order]
    # final_columns_order = desired_order + additional_cols

    # Ensure all columns are present
    # final_columns_order = [col for col in final_columns_order if col in merged_df.columns]
    # merged_df = merged_df[final_columns_order]
    final_df = merged_df[desired_order]

    return final_df

def save_merged_csv(merged_df, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)

    today_str = datetime.now().strftime('%Y-%m-%d')
    output_file = os.path.join(output_dir, f"{today_str}_report.csv")

    try:
        merged_df.to_csv(output_file, index=False)
        print(f"Report generated and saved to {output_file}")
    except Exception as e:
        print(f"Error saving the merged CSV file: {e}")

def write_final_text_reports(merged_df: pd.DataFrame, output_dir: str = "outputs"):
    os.makedirs(output_dir, exist_ok=True)

    today_str = datetime.now().strftime('%Y-%m-%d')
    markdown_output_file = os.path.join(output_dir, f"{today_str}_report.md")
    pdf_output_file = os.path.join(output_dir, f"{today_str}_report.pdf")
    human_today_str = datetime.now().strftime('%d %B %Y')
    markdown_text = f"# IT Applications Status Report - {human_today_str}\n\n"
    markdown_text += f"- Current Laravel Version: {current_laravel_version} (yearly update ~February)\n"
    markdown_text += f"- Current PHP Version: {current_php_version} (yearly update ~November)\n\n"
    markdown_text += f"## Project Status\n\n"
    markdown_text += merged_df.to_markdown(index=False)

    with open(markdown_output_file, 'w') as file:
        file.write(markdown_text)

    #pdf = MarkdownPdf()
    #pdf.add_section(Section(markdown_text, toc=False))
    #pdf.meta['Title'] = f"IT Applications Status Report - {human_today_str}"
    #pdf.meta["author"] = "COSE IT"
    #pdf.save(pdf_output_file)

    print(f"Report generated and saved to {pdf_output_file} and {markdown_output_file}")

if __name__ == "__main__":
    args = parse_arguments()

    base_path = args.base_path
    manual_json_path = args.manual_json
    output_dir = args.output_dir
    perform_pull = args.pull  # Boolean flag

    if args.add_new:
        add_new_project_to_manual_json(manual_json_path)
        print(f"New project added to {manual_json_path}. Exiting...")
        sys.exit(0)
    # Read manual CSV data
    manual_df = read_manual_json(manual_json_path)
    # extract the 'Local Directory' column as an array called 'projects'
    projects = manual_df['Local Directory'].tolist()

    # Sanity check against the list of projects at the top of this script
    validate_projects_in_manual_json(projects, manual_df)

    # Extract dynamic data
    extracted_data = extract_versions(base_path, perform_pull, projects)
    dynamic_df = dynamic_data_to_dataframe(extracted_data)

    # Merge both DataFrames on 'Local Directory'
    merged_df = merge_dataframes(manual_df, dynamic_df)

    # Replace placeholders with dynamic data
    merged_df = replace_placeholders(merged_df)

    # Finalize the report
    final_report_df = finalize_report(merged_df)

    # Save the merged report to a new CSV and markdown file
    save_merged_csv(final_report_df, output_dir)
    write_final_text_reports(final_report_df, output_dir)
