import json

import glob
import os
import subprocess
from datetime import datetime

# Get current branch name
def get_branch_name():
  try:
    return (
      subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
      .decode('utf-8')
      .strip()
    )
  except Exception:
    return None

import sys
branch_name = os.environ.get('RESULT_BRANCH') or os.environ.get('GITHUB_HEAD_REF') or os.environ.get('GITHUB_REF_NAME') or get_branch_name()
print(f"[DEBUG] Detected branch name: {branch_name}")
if not branch_name:
  raise RuntimeError('Could not determine branch name.')

# List all visible folders in the workspace
all_folders = [f for f in os.listdir('.') if os.path.isdir(f) and not f.startswith('.')]
print(f"[DEBUG] Visible folders in workspace: {all_folders}")

# Try to use the branch-named folder first
if os.path.isdir(branch_name):
  search_folder = branch_name
  print(f"[DEBUG] Using branch-named folder: {search_folder}")
else:
  # Fallback: pick the first folder matching pattern (e.g., RDKEMW-*)
  if not all_folders:
    raise FileNotFoundError('[ERROR] No candidate results folders found in workspace root.')
  search_folder = sorted(all_folders)[-1]
  print(f"[DEBUG] Branch-named folder not found. Using fallback folder: {search_folder}")

# Find all subfolders (assumed to be timestamped) inside the search folder
subfolders = [f.path for f in os.scandir(search_folder) if f.is_dir()]
print(f"[DEBUG] Subfolders in {search_folder}: {[os.path.basename(f) for f in subfolders]}")
if not subfolders:
  raise FileNotFoundError(f'[ERROR] No subfolders found in {search_folder}. Folder contents: {os.listdir(search_folder)}')

# Pick the latest subfolder by name (assuming timestamp format)
latest_subfolder = sorted(subfolders)[-1]
print(f"[DEBUG] Using latest subfolder: {latest_subfolder}")

# Look for the JSON file in the latest subfolder
json_path = os.path.join(latest_subfolder, 'complete_firebolt_schema_validation_response.json')
print(f"[DEBUG] Looking for JSON at: {json_path}")
if not os.path.isfile(json_path):
  raise FileNotFoundError(f'[ERROR] No firebolt schema validation JSON found in {json_path}. Files in subfolder: {os.listdir(latest_subfolder)}')
latest_json = json_path

with open(latest_json) as f:
    data = json.load(f)

# Extract folder timestamp
folder_name = os.path.basename(os.path.dirname(latest_json))

# HTML template (from your current working version)
html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Firebolt Schema Validation Result</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f4f4f4; }}
    .container {{ max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }}
    h1 {{ text-align: center; }}
    .summary {{ display: flex; justify-content: space-around; margin-bottom: 20px; }}
    .summary div {{ background: #eee; border-radius: 8px; padding: 16px 32px; text-align: center; }}
    .summary .passed {{ color: #2e7d32; font-weight: bold; }}
    .summary .failed {{ color: #c62828; font-weight: bold; }}
    .summary .skipped {{ color: #888; }}
    .tabs {{ display: flex; justify-content: center; margin-bottom: 20px; }}
    .tab {{ padding: 12px 32px; cursor: pointer; border-radius: 8px 8px 0 0; background: #ddd; margin: 0 2px; font-weight: bold; }}
    .tab.active {{ background: #1976d2; color: #fff; }}
    .test-list {{ background: #fafafa; border-radius: 0 0 8px 8px; padding: 16px; }}
    .test-item {{ border-bottom: 1px solid #eee; padding: 12px 0; }}
    .test-item:last-child {{ border-bottom: none; }}
    .test-name {{ font-weight: bold; }}
    .test-status {{ margin-left: 12px; font-size: 0.95em; }}
    .test-status.passed {{ color: #2e7d32; }}
    .test-status.failed {{ color: #c62828; }}
    .test-status.skipped {{ color: #888; }}
    .test-steps {{ margin-top: 8px; margin-left: 24px; }}
    .step {{ margin-bottom: 6px; }}
    .step .step-desc {{ font-size: 0.97em; }}
    .step .step-status.failed {{ color: #c62828; }}
    .step .step-status.passed {{ color: #2e7d32; }}
    .step .step-status.skipped {{ color: #888; }}
    table {{ width:100%;border-collapse:collapse;background:#fafafa;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px #0001; margin-bottom: 24px; }}
    th, td {{ padding:8px; text-align:center; }}
    thead {{ background:#1976d2;color:#fff; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1 id=\"suiteName\">{data['suite_name']}</h1>
    <div style=\"text-align:center;margin-bottom:8px;\">
      <span id=\"timestamp\" style=\"color:#888;font-size:1em;\">Generated On: {folder_name}</span>
    </div>
    <div class=\"summary\" style=\"margin-bottom: 20px;\">
      <div><span id=\"totalTests\">{data['total_tests']}</span><br>Total</div>
      <div class=\"passed\"><span id=\"passedTests\">{data['passed']}</span><br>Passed</div>
      <div class=\"failed\"><span id=\"failedTests\">{data['failed']}</span><br>Failed</div>
      <div class=\"skipped\"><span id=\"skippedTests\">{data['skipped']}</span><br>Skipped</div>
      <div><span id=\"duration\">{data['duration_ms']}</span> ms<br>Duration</div>
    </div>
    <div style=\"margin-bottom: 24px;\">
      <table id=\"categorySummaryTable\">
        <thead><tr><th>Category</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th></tr></thead>
        <tbody id=\"categorySummaryBody\"></tbody>
      </table>
    </div>
    <div class=\"tabs\" id=\"categoryTabs\" style=\"margin-bottom: 20px;\"></div>
    <div class=\"tabs\" style=\"margin-bottom: 20px;\">
      <div class=\"tab active\" id=\"tab-all\" onclick=\"showTab('All')\">All</div>
      <div class=\"tab\" id=\"tab-pass\" onclick=\"showTab('Passed')\">Pass</div>
      <div class=\"tab\" id=\"tab-fail\" onclick=\"showTab('Failed')\">Fail</div>
    </div>
    <div class=\"test-list\" id=\"testList\"></div>
  </div>
  <script>
    const data = {json.dumps(data)};
    // ...existing JS logic from your current HTML...
  </script>
</body>
</html>
"""

with open('firebolt_schema_validation_result.html', 'w') as f:
    f.write(html)

print('firebolt_schema_validation_result.html generated.')
