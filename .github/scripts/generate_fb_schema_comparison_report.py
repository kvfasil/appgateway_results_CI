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
    
    # Use CURRENT_BRANCH_DIR if set, otherwise fall back to git branch
    current_branch_folder = os.getenv('CURRENT_BRANCH_DIR')
    if current_branch_folder:
        print(f"[INFO] Using CURRENT_BRANCH_DIR env var: {current_branch_folder}")
        if not os.path.isdir(current_branch_folder):
            raise RuntimeError(f"The directory specified by CURRENT_BRANCH_DIR does not exist: {current_branch_folder}")
    else:
        print("[INFO] CURRENT_BRANCH_DIR not set, determining folder from git branch.")
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

    # Resolve display paths
    current_run_folder = os.path.dirname(current_result_file)

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

    # Build HTML sections after helper functions are defined

    # --- 3. Generate HTML content ---
    def create_test_row(test, base_test=None):
        test_id = test['test_id']
        test_name = test['test_name']
        current_status = test['status']
        base_status = base_test['status'] if base_test else 'N/A'
        
        status_class = 'status-passed' if current_status in ['Passed', 'Success'] else 'status-failed'
        
        # Extract request and response from the first step
        request_details = test.get('steps', [{}])[0].get('request', {})
        response_details = test.get('steps', [{}])[0].get('response', {})
        error_details = test.get('steps', [{}])[0].get('error', 'No error details.')

        details_html = f"""
        <div class="details" id="details-{test_id}">
            <div style=\"font-size:12px;color:#6b7b8c;margin:8px 20px;\"><b>Test ID:</b> {test_id}</div>
            <div class="details-content">
                <div class="column">
                    <h4>Request</h4>
                    <pre><code>{json.dumps(request_details, indent=2)}</code></pre>
                </div>
                <div class="column">
                    <h4>Response</h4>
                    <pre><code>{json.dumps(response_details, indent=2)}</code></pre>
                    <h4>Error</h4>
                    <pre><code>{error_details}</code></pre>
                </div>
            </div>
        </div>
        """
        
        row_html = f"""
        <tr class="test-row" onclick="toggleDetails('{test_id}')">
            <td><span class=\"idtag\">{test_id}</span>{test_name}</td>
            <td class='status'>{base_status}</td>
            <td class='status {status_class}'>{current_status}</td>
        </tr>
        <tr>
            <td colspan="3">{details_html}</td>
        </tr>
        """
        return row_html

    def create_single_test_row(test):
        test_id = test['test_id']
        test_name = test['test_name']
        current_status = test['status']
        
        status_class = 'status-passed' if current_status in ['Passed', 'Success'] else 'status-failed'
        
        request_details = test.get('steps', [{}])[0].get('request', {})
        response_details = test.get('steps', [{}])[0].get('response', {})
        error_details = test.get('steps', [{}])[0].get('error', 'No error details.')

        details_html = f"""
        <div class="details" id="details-{test_id}">
            <div style=\"font-size:12px;color:#6b7b8c;margin:8px 20px;\"><b>Test ID:</b> {test_id}</div>
            <div class="details-content">
                <div class="column">
                    <h4>Request</h4>
                    <pre><code>{json.dumps(request_details, indent=2)}</code></pre>
                </div>
                <div class="column">
                    <h4>Response</h4>
                    <pre><code>{json.dumps(response_details, indent=2)}</code></pre>
                    <h4>Error</h4>
                    <pre><code>{error_details}</code></pre>
                </div>
            </div>
        </div>
        """
        
        row_html = f"""
        <tr class="test-row" onclick="toggleDetails('{test_id}')">
            <td><span class=\"idtag\">{test_id}</span>{test_name}</td>
            <td class='status {status_class}'>{current_status}</td>
        </tr>
        <tr>
            <td colspan="2">{details_html}</td>
        </tr>
        """
        return row_html

    # Build section HTML (joins will yield empty strings when no differences)
    regressions_html = "".join([create_test_row(current, base) for current, base in regressions])
    improvements_html = "".join([create_test_row(current, base) for current, base in improvements])
    new_tests_html = "".join([create_single_test_row(test) for test in new_tests])
    removed_tests_html = "".join([create_single_test_row(test) for test in removed_tests])

    # --- 4. Generate final HTML from an embedded template ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Firebolt Schema Validation Comparison Report</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f4f7f9;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: auto;
                background-color: #fff;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }}
            h1, h2 {{
                color: #1a2c42;
                border-bottom: 2px solid #eef2f5;
                padding-bottom: 10px;
                margin-top: 0;
            }}
            h2 {{
                margin-top: 30px;
            }}
            .page-title {{
                text-align: center;
                border-bottom: none;
                margin-bottom: 10px;
            }}
            .summary {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 14px;
                margin: 10px 0 20px 0;
            }}
            .run-info {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                font-size: 13px;
                color: #44566c;
                background: #f9fafb;
                border: 1px solid #eef2f5;
                border-radius: 8px;
                padding: 10px 12px;
                margin: 6px 0 16px 0;
            }}
            .run-info code {{
                background: #eef2f5;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
                font-size: 12px;
                color: #1a2c42;
            }}
            .summary-card {{
                background-color: #f9fafb;
                border: 1px solid #eef2f5;
                border-radius: 8px;
                padding: 14px;
                text-align: center;
            }}
            .summary-card h3 {{
                margin: 0 0 6px 0;
                font-size: 14px;
                font-weight: 600;
                color: #44566c;
            }}
            .summary-card .count {{
                font-size: 24px;
                font-weight: 700;
                color: #1a2c42;
            }}
            /* Inline section description style */
            .section-inline-desc {{
                margin-left: 8px;
                font-size: 13px;
                color: #6b7b8c;
                font-weight: 400;
            }}
            .summary-card.regressions .count {{ color: #dc3545; }}
            .summary-card.improvements .count {{ color: #28a745; }}
            .summary-card.new .count {{ color: #007bff; }}
            .summary-card.removed .count {{ color: #6c757d; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #eef2f5;
            }}
            th {{
                background-color: #f9fafb;
                font-weight: 600;
                color: #555;
            }}
            tr.test-row {{
                cursor: pointer;
                transition: background-color 0.2s ease;
            }}
            tr.test-row:hover {{
                background-color: #f9fafb;
            }}
            .status {{
                font-weight: 600;
            }}
            .status-passed {{
                color: #28a745;
            }}
            .status-failed {{
                color: #dc3545;
            }}
            .details {{
                display: none;
                padding: 0;
                background-color: #fafafa;
            }}
            .details-content {{
                display: flex;
                padding: 20px;
                border-top: 2px solid #eef2f5;
            }}
            .idtag {{
                display: inline-block;
                font-size: 12px;
                padding: 2px 6px;
                border-radius: 6px;
                background: #eef1f4;
                color: #6b7b8c;
                margin-right: 8px;
                border: 1px solid #e3e8ee;
            }}
            .column {{
                flex: 1;
                padding: 0 15px;
            }}
            .column:first-child {{
                border-right: 1px solid #eef2f5;
            }}
            pre {{
                background-color: #eef2f5;
                padding: 15px;
                border-radius: 6px;
                white-space: pre-wrap;
                word-wrap: break-word;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
                font-size: 13px;
            }}
            code {{
                color: #1a2c42;
            }}
            .no-changes {{
                text-align: center;
                padding: 50px;
            }}
            .section {{
                margin-top: 20px;
            }}
            .section-title {{
                cursor: pointer;
                user-select: none;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }}
            .section-body {{
                display: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="page-title">Regression Test Results</h1>
            <div class="run-info">
                <div><strong>Current:</strong> <code>{current_run_folder}</code></div>
                <div><strong>Base:</strong> <code>{base_result_dir}</code></div>
            </div>
            <div class="summary">
                <div class="summary-card regressions">
                    <h3>🚨Regressions</h3>
                    <div class="count">{len(regressions)}</div>
                </div>
                <div class="summary-card improvements">
                    <h3>✨Improvements</h3>
                    <div class="count">{len(improvements)}</div>
                </div>
                <div class="summary-card new">
                    <h3>💡New Tests</h3>
                    <div class="count">{len(new_tests)}</div>
                </div>
                <div class="summary-card removed">
                    <h3>🗑️Removed Tests</h3>
                    <div class="count">{len(removed_tests)}</div>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title" data-target="regressions"><span style="color: #dc3545;">&#x1f6a8;</span>Regressions ({len(regressions)})<span class="section-inline-desc">(Passed in Base, Failed Now)</span></h2>
                <div id="section-regressions" class="section-body">
                    <table>
                        <thead><tr><th>Test Name</th><th>Base Status</th><th>Current Status</th></tr></thead>
                        <tbody>{regressions_html}</tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title" data-target="improvements"><span style="color: #28a745;">&#x2728;</span>Improvements ({len(improvements)})<span class="section-inline-desc">(Failed in Base, Passed Now)</span></h2>
                <div id="section-improvements" class="section-body">
                    <table>
                        <thead><tr><th>Test Name</th><th>Base Status</th><th>Current Status</th></tr></thead>
                        <tbody>{improvements_html}</tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title" data-target="new-tests"><span style="color: #007bff;">&#x1f4a1;</span>New Tests ({len(new_tests)})<span class="section-inline-desc">(Only in Current)</span></h2>
                <div id="section-new-tests" class="section-body">
                    <table>
                        <thead><tr><th>Test Name</th><th>Status</th></tr></thead>
                        <tbody>{new_tests_html}</tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title" data-target="removed-tests"><span style="color: #6c757d;">&#x1f5d1;</span>Removed Tests ({len(removed_tests)})<span class="section-inline-desc">(Only in Base)</span></h2>
                <div id="section-removed-tests" class="section-body">
                    <table>
                        <thead><tr><th>Test Name</th><th>Status</th></tr></thead>
                        <tbody>{removed_tests_html}</tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            function toggleDetails(testId) {{
                const details = document.getElementById('details-' + testId);
                if (details.style.display === 'block') {{
                    details.style.display = 'none';
                }} else {{
                    details.style.display = 'block';
                }}
            }}

            function toggleSection(sectionKey) {{
                const body = document.getElementById('section-' + sectionKey);
                if (!body) return;
                body.style.display = (body.style.display === 'block') ? 'none' : 'block';
            }}

            document.addEventListener('DOMContentLoaded', function () {{
                // Click to toggle each section
                const headers = document.querySelectorAll('.section-title');
                headers.forEach(h => {{
                    h.addEventListener('click', () => toggleSection(h.dataset.target));
                }});
                // Keep all sections collapsed by default
            }});
        </script>
    </body>
    </html>
    """

    # --- 4. (Legacy alternate layout, not used for output) ---
    html_content_unused = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Firebolt Schema Validation Comparison Report</title>
        <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            line-height: 1.6;
            color: #24292e;
            background-color: #f6f8fa;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            border-bottom: 2px solid #eaecef;
            padding-bottom: 10px;
        }}
        .summary-section {{
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
        .tab-container {{
            display: flex;
            border-bottom: 2px solid #dfe2e5;
            margin-bottom: 20px;
        }}
        .tab {{
            padding: 10px 20px;
            cursor: default;
            background-color: #f1f1f1;
            border: 1px solid #dfe2e5;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            margin-right: 5px;
        }}
        .tab.active {{
            background-color: #fff;
            border-bottom: 1px solid #fff;
        }}
        .tab-content {{
            display: none;
            padding: 20px;
            border: 1px solid #dfe2e5;
            border-top: none;
            border-radius: 0 0 6px 6px;
            background-color: #fff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            border: 1px solid #dfe2e5;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f6f8fa;
        }}
        .diff {{
            white-space: pre-wrap;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
        }}
        .diff-added {{
            background-color: #e6ffed;
            color: #24292e;
        }}
        .diff-removed {{
            background-color: #ffeef0;
            color: #24292e;
        }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Firebolt Schema Validation Comparison Report</h1>

            <div class="tab-container">
                <div class="tab active">
                    <strong>Current:</strong>
                    <span>{os.path.basename(current_branch_folder)} (latest)</span>
                </div>
                <div class="tab">
                    <strong>Base:</strong>
                    <span>{base_result_dir}</span>
                </div>
            </div>

            <div class="summary-section">
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
        </div>

        <script>
        // Tab functionality
        const tabs = document.querySelectorAll('.tab');
        const contents = document.querySelectorAll('.tab-content');

        tabs.forEach(tab => {{
            tab.addEventListener('click', (evt) => {{
                // Remove active class from all tabs
                tabs.forEach(t => t.classList.remove('active'));
                // Hide all tab contents
                contents.forEach(c => c.style.display = 'none');

                // Add active class to the clicked tab
                evt.currentTarget.classList.add('active');

                // Show the corresponding tab content
                const index = Array.from(tabs).indexOf(evt.currentTarget);
                contents[index].style.display = 'block';
            }});
        }});

        // Automatically click the first tab on page load
        document.addEventListener('DOMContentLoaded', () => {{
            tabs[0].click();
        }});
        </script>
    </body>
    </html>
    """
    
    with open("comparison_report.html", 'w') as f:
        f.write(html_content)
    
    print(f"[SUCCESS] Generated comparison report: comparison_report.html")

if __name__ == "__main__":
    generate_comparison_report()
