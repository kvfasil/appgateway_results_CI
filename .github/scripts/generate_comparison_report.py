import json
import os
import glob
import subprocess

def find_latest_result_file(base_folder):
    """Finds the latest 'complete_firebolt_schema_validation_response.json' in a given base folder."""
    print(f"[INFO] Searching for results in base folder: {base_folder}")
    if not os.path.isdir(base_folder):
        print(f"[ERROR] Base folder not found: {base_folder}")
        return None

    # Find all timestamped subfolders
    subfolders = [f.path for f in os.scandir(base_folder) if f.is_dir()]
    if not subfolders:
        print(f"[ERROR] No timestamped subfolders found in {base_folder}")
        return None

    # Get the latest subfolder
    latest_subfolder = max(subfolders, key=os.path.getmtime)
    print(f"[INFO] Using latest subfolder: {latest_subfolder}")

    # Find the JSON file
    result_file = os.path.join(latest_subfolder, 'complete_firebolt_schema_validation_response.json')
    if not os.path.isfile(result_file):
        print(f"[ERROR] Result JSON not found in {latest_subfolder}")
        return None
    
    print(f"[INFO] Found result file: {result_file}")
    return result_file

def get_current_branch_folder():
    """Determines the current branch folder name by checking the active git branch."""
    try:
        branch_name = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf-8').strip()
        print(f"[INFO] Detected current git branch: {branch_name}")
        if os.path.isdir(branch_name):
            print(f"[INFO] Found a directory with the same name as the branch: {branch_name}")
            return branch_name
        else:
            raise RuntimeError(f"A directory named '{branch_name}' was not found in the current path.")
    except Exception as e:
        raise RuntimeError(f"Could not determine the current branch folder: {e}")

def generate_comparison_report():
    """Generates an HTML report comparing two test results."""
    
    # --- 1. Find the two JSON files to compare ---
    base_result_dir = os.getenv('BASE_RESULT_DIR')
    if not base_result_dir:
        print("[ERROR] Environment variable 'BASE_RESULT_DIR' is not set.")
        return
    base_result_file = os.path.join(base_result_dir, 'complete_firebolt_schema_validation_response.json')
    current_branch_folder = get_current_branch_folder()

    print(f"[INFO] Using base reference file: {base_result_file}")
    if not os.path.isfile(base_result_file):
        print(f"[ERROR] Base reference file not found at: {base_result_file}")
        return

    current_result_file = find_latest_result_file(current_branch_folder)

    if not current_result_file:
        print("[ERROR] Cannot generate comparison report. Current result file is missing.")
        return

    with open(base_result_file) as f:
        base_data = json.load(f)
    with open(current_result_file) as f:
        current_data = json.load(f)

    # --- 2. Compare the results ---
    base_tests = {test['test_id']: test for test in base_data['test_results']}
    current_tests = {test['test_id']: test for test in current_data['test_results']}

    regressions = []
    improvements = []
    
    for test_id, current_test in current_tests.items():
        base_test = base_tests.get(test_id)
        if base_test:
            base_status_ok = base_test['status'] in ['Passed', 'Success']
            current_status_ok = current_test['status'] in ['Passed', 'Success']
            
            # Regression: Was OK, now it's not
            if base_status_ok and not current_status_ok:
                regressions.append((current_test, base_test))
            
            # Improvement: Was not OK, now it is
            if not base_status_ok and current_status_ok:
                improvements.append((current_test, base_test))

    new_tests = [current_tests[test_id] for test_id in current_tests if test_id not in base_tests]
    removed_tests = [base_tests[test_id] for test_id in base_tests if test_id not in current_tests]

    # --- 3. Generate HTML content ---
    def create_regressions_html(items):
        rows = ''
        for current, base in items:
            rows += f"<tr><td>{current['test_name']}</td><td class='status status-passed'>{base['status']}</td><td class='status status-failed'>{current['status']}</td></tr>"
        return rows

    def create_improvements_html(items):
        rows = ''
        for current, base in items:
            rows += f"<tr><td>{current['test_name']}</td><td class='status status-failed'>{base['status']}</td><td class='status status-passed'>{current['status']}</td></tr>"
        return rows

    def create_single_list_html(items):
        rows = ''
        for item in items:
            status_class = 'status-passed' if item['status'] in ['Passed', 'Success'] else 'status-failed'
            rows += f"<tr><td>{item['test_name']}</td><td class='status {status_class}'>{item['status']}</td></tr>"
        return rows

    regressions_html = create_regressions_html(regressions)
    improvements_html = create_improvements_html(improvements)
    new_tests_html = create_single_list_html(new_tests)
    removed_tests_html = create_single_list_html(removed_tests)

    # --- 4. Generate final HTML from an embedded template ---
    report_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Comparison Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
            background-color: #f6f8fa;
        }}
        h1, h2 {{
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        h1 {{
            font-size: 2em;
        }}
        h2 {{
            font-size: 1.5em;
            margin-top: 40px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            background-color: #fff;
        }}
        th, td {{
            border: 1px solid #dfe2e5;
            padding: 10px 15px;
            text-align: left;
        }}
        th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        .status {{
            font-weight: bold;
            text-align: center;
            border-radius: 5px;
            padding: 5px 8px;
            color: white;
        }}
        .status-passed {{
            background-color: #28a745;
        }}
        .status-failed {{
            background-color: #d73a49;
        }}
        .summary {{
            background-color: #fff;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .summary-item {{
            background-color: #f6f8fa;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #dfe2e5;
        }}
        .summary-item h3 {{
            margin: 0 0 10px 0;
            font-size: 1.1em;
        }}
        .summary-item p {{
            margin: 0;
            font-size: 2em;
            font-weight: bold;
        }}
        .branch-info {{
            margin-bottom: 20px;
            font-style: italic;
            color: #586069;
        }}
    </style>
</head>
<body>
    <h1>Test Comparison Report</h1>

    <div class="branch-info">
        <p><strong>Current:</strong> <span id="current-branch-name">{os.path.basename(current_branch_folder)} (latest)</span></p>
        <p><strong>Base:</strong> <span id="base-branch-name">{base_result_dir}</span></p>
    </div>

    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <h3>Regressions</h3>
                <p><span id="regressions-count">{len(regressions)}</span></p>
            </div>
            <div class="summary-item">
                <h3>Improvements</h3>
                <p><span id="improvements-count">{len(improvements)}</span></p>
            </div>
            <div class="summary-item">
                <h3>New Tests</h3>
                <p><span id="new-tests-count">{len(new_tests)}</span></p>
            </div>
            <div class="summary-item">
                <h3>Removed Tests</h3>
                <p><span id="removed-tests-count">{len(removed_tests)}</span></p>
            </div>
        </div>
    </div>

    <h2>Regressions</h2>
    <table>
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Base Status</th>
                <th>Current Status</th>
            </tr>
        </thead>
        <tbody>
            {regressions_html}
        </tbody>
    </table>

    <h2>Improvements</h2>
    <table>
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Base Status</th>
                <th>Current Status</th>
            </tr>
        </thead>
        <tbody>
            {improvements_html}
        </tbody>
    </table>

    <h2>New Tests</h2>
    <table>
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {new_tests_html}
        </tbody>
    </table>

    <h2>Removed Tests</h2>
    <table>
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {removed_tests_html}
        </tbody>
    </table>

</body>
</html>
"""

    # --- 5. Write final report ---
    with open('comparison_report.html', 'w') as f:
        f.write(report_html)
    
    print("[SUCCESS] Generated comparison_report.html")

if __name__ == "__main__":
    generate_comparison_report()
