import os
import json
import subprocess


def find_latest_result_file(base_folder: str):
  print(f"[INFO] Searching for results in base folder: {base_folder}")
  if not os.path.isdir(base_folder):
    print(f"[ERROR] Base folder not found: {base_folder}")
    return None, None
  # Try timestamped subfolders first
  subfolders = [f.path for f in os.scandir(base_folder) if f.is_dir()]
  # Exclude the aggregation folder named 'artifacts' from consideration
  subfolders = [p for p in subfolders if os.path.basename(p) != 'artifacts']
  if subfolders:
    latest_subfolder = max(subfolders, key=os.path.getmtime)
    print(f"[INFO] Using latest subfolder: {latest_subfolder}")
    result_file = os.path.join(latest_subfolder, 'CoreSanity_SchemaValidation_response.json')
    if os.path.isfile(result_file):
      print(f"[INFO] Found result file: {result_file}")
      return result_file, latest_subfolder
    else:
      print(f"[WARN] Result JSON not found in {latest_subfolder}")
  # Fallback: JSON directly inside base_folder
  direct_json = os.path.join(base_folder, 'CoreSanity_SchemaValidation_response.json')
  if os.path.isfile(direct_json):
    print(f"[INFO] Found direct result file: {direct_json}")
    return direct_json, base_folder
  print(f"[ERROR] No timestamped subfolders found and no direct JSON in {base_folder}")
  return None, None


def get_current_branch_folder():
    try:
        branch_name = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf-8').strip()
        print(f"[INFO] Detected current git branch: {branch_name}")
        return branch_name
    except Exception as e:
        raise RuntimeError(f"Could not determine the current branch folder: {e}")


def generate_test_report():
    # Prefer explicit RESULT_BRANCH when provided (CI manual dispatch or workflow)
    branch_folder = os.getenv('RESULT_BRANCH')
    print(f"[INFO] Using RESULT_BRANCH env var: {branch_folder}")

    # Initialize result variables
    result_file = None
    latest_subfolder = None

    # Try RESULT_DIR as a primary source
    if True:
      result_dir = os.getenv('RESULT_DIR')
      if result_dir:
        print(f"[INFO] Loading files from RESULT_DIR: {result_dir}")
        result_file, latest_subfolder = find_latest_result_file(result_dir)
      if not result_file:
        print("[ERROR] Cannot generate test report. Result JSON is missing.")
        print("[ERROR] RESULT_DIR is empty Aborting report generation.")
        return

    with open(result_file) as f:
        data = json.load(f)

    # Derive a readable timestamp from the subfolder name if possible
    timestamp = os.path.basename(latest_subfolder)
    
    # print timestamp info
    print(f"[INFO] Using timestamp for report: {timestamp}")

    # Build HTML with embedded data
    # Note: double curly braces to escape within f-string CSS/JS
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Firebolt Schema Validation Result</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 0; padding: 0; background: #f4f7f9; color:#1a2c42; }}
        .container {{ max-width: 1200px; margin: 32px auto; background: #fff; border-radius: 10px; box-shadow: 0 6px 16px rgba(0,0,0,0.08); padding: 28px; }}
        h1 {{ text-align: center; margin: 0 0 6px 0; }}
        .meta {{ text-align:center; color:#6b7b8c; font-size: 13px; margin-bottom: 16px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr)); gap: 14px; margin-bottom: 16px; }}
        .card {{ background:#f9fafb; border:1px solid #eef2f5; border-radius:10px; padding:14px; text-align:center; }}
        .card h3 {{ margin:0 0 6px 0; font-size:13px; color:#44566c; font-weight:600; }}
        .card .count {{ font-size:24px; font-weight:700; }}
        .card.passed .count{{ color:#28a745; }}
        .card.failed .count{{ color:#dc3545; }}
        .card.skipped .count{{ color:#6c757d; }}
        .progress {{ position:relative; height:6px; background:#eef2f5; border-radius:999px; overflow:hidden; margin-top:8px; }}
        .progress > span {{ position:absolute; left:0; top:0; bottom:0; background:linear-gradient(90deg,#28a745,#20c997); border-radius:999px; }}
        .controls {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; justify-content:space-between; background:#f9fafb; border:1px solid #eef2f5; border-radius:10px; padding:10px 12px; margin: 10px 0 18px 0; }}
        .left-controls, .right-controls{{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
        .search {{ display:flex; align-items:center; gap:8px; background:#fff; border:1px solid #e3e8ee; border-radius:8px; padding:6px 10px; }}
        .search input{{ border:none; outline:none; font-size:14px; min-width:220px; }}
        .select {{ border:1px solid #e3e8ee; background:#fff; border-radius:8px; padding:6px 10px; font-size:14px; }}
        .btn {{ border:1px solid #e3e8ee; background:#fff; border-radius:8px; padding:6px 10px; font-size:13px; cursor:pointer; }}
        .btn:hover{{ background:#f3f6f9; }}
        .tabs {{ display:flex; justify-content:center; flex-wrap:wrap; margin: 10px 0 12px 0; gap:6px; }}
        .tab {{ padding:10px 18px; cursor:pointer; border-radius:999px; background:#e9eef3; font-weight:600; color:#44566c; }}
        .tab.active {{ background:#1976d2; color:#fff; }}
        .test-list {{ background:#fff; border:1px solid #eef2f5; border-radius:10px; padding: 0 0 6px 0; overflow:hidden; }}
        .test-item {{ border-top: 1px solid #eef2f5; padding: 12px 16px; }}
        .test-item:first-child{{ border-top:none; }}
        .test-header {{ display:flex; justify-content:space-between; align-items:center; gap:12px; cursor:pointer; }}
        .test-name {{ font-weight:600; }}
        .idtag {{ font-size:11px; padding:2px 6px; border-radius:6px; background:#eef1f4; color:#6b7b8c; margin-right:8px; border:1px solid #e3e8ee; }}
        .badge {{ font-size:12px; padding:3px 8px; border-radius:999px; border:1px solid currentColor; }}
        .badge.passed{{ color:#28a745; background:#eaf7ef; }}
        .badge.failed{{ color:#dc3545; background:#fdecef; }}
        .badge.skipped{{ color:#6c757d; background:#eef1f4; }}
        .duration {{ color:#6b7b8c; font-size:12px; }}
        .details {{ display:none; background:#f9fbfd; border:1px solid #eef2f5; border-radius:8px; margin-top:10px; padding:12px; }}
        .detail-grid{{ display:flex; gap:12px; flex-wrap:wrap; }}
        .col{{ flex:1 1 380px; }}
        h4{{ margin:8px 0 6px 0; font-size:13px; color:#44566c; }}
        pre{{ background:#eef2f5; padding:10px; border-radius:6px; overflow:auto; font-size:12px; white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; }}
        table {{ width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px #0001; margin-bottom: 16px; }}
        th, td {{ padding:10px; text-align:center; }}
        thead {{ background:#1976d2;color:#fff; }}
        .link{{ color:#1976d2; cursor:pointer; text-decoration:underline; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h1 id="suiteName">{data.get('suite_name', 'Firebolt Schema Validation')}</h1>
        <div class="meta"><span id="timestamp">Generated On: {timestamp}</span></div>
        <div class="summary">
          <div class="card">
            <h3>Total</h3>
            <div class="count" id="totalTests">{data.get('total_tests', len(data.get('test_results', [])))}</div>
          </div>
          <div class="card passed">
            <h3>Passed</h3>
            <div class="count" id="passedTests">{data.get('passed', 0)}</div>
            <div class="progress"><span id="passBar" style="width:0%"></span></div>
          </div>
          <div class="card failed">
            <h3>Failed</h3>
            <div class="count" id="failedTests">{data.get('failed', 0)}</div>
          </div>
          <div class="card">
            <h3>Skipped</h3>
            <div class="count" id="skippedTests">{data.get('skipped', 0)}</div>
          </div>
          <div class="card">
            <h3>Duration</h3>
            <div class="count" id="duration">{data.get('duration_ms', 0)} ms</div>
          </div>
        </div>
        <div style="margin-bottom: 16px;">
          <table id="categorySummaryTable">
            <thead><tr><th>Category</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th></tr></thead>
            <tbody id="categorySummaryBody"></tbody>
            <tfoot id="categorySummaryFoot"></tfoot>
          </table>
        </div>
        <div class="tabs" id="categoryTabs" style="margin-bottom: 12px;"></div>
        <div class="controls">
          <div class="left-controls">
            <div class="search">
              <span>🔎</span>
              <input id="searchBox" type="text" placeholder="Search tests by name or ID..." />
            </div>
            <select id="sortSelect" class="select">
              <option value="status">Sort: Status</option>
              <option value="name">Sort: Name</option>
              <option value="duration">Sort: Duration</option>
            </select>
          </div>
          <div class="right-controls">
            <button class="btn" onclick="expandAll()">Expand All</button>
            <button class="btn" onclick="collapseAll()">Collapse All</button>
          </div>
        </div>
        <div class="tabs" style="margin-bottom: 12px;">
          <div class="tab active" id="tab-all" onclick="showTab('All')">All</div>
          <div class="tab" id="tab-pass" onclick="showTab('Passed')">Pass</div>
          <div class="tab" id="tab-fail" onclick="showTab('Failed')">Fail</div>
        </div>
        <div class="test-list" id="testList"></div>
      </div>
      <script>
        const data = {json.dumps(data)};
        // Category extraction
        const categories = Array.from(new Set(data.test_results.map(t => (t.test_id||'').split(/\\d/)[0])));
        let selectedCategory = 'All';
        let currentSearch = '';
        let currentSort = 'status';

        function renderCategoryTabs() {{
          const catTabs = document.getElementById('categoryTabs');
          catTabs.innerHTML = '';
          const allTab = document.createElement('div');
          allTab.className = 'tab' + (selectedCategory === 'All' ? ' active' : '');
          allTab.textContent = 'All';
          allTab.onclick = () => {{ selectedCategory = 'All'; renderCategoryTabs(); showTab(currentStatusTab); }};
          catTabs.appendChild(allTab);
          categories.forEach(cat => {{
            const tab = document.createElement('div');
            tab.className = 'tab' + (cat === selectedCategory ? ' active' : '');
            tab.textContent = cat;
            tab.onclick = () => {{ selectedCategory = cat; renderCategoryTabs(); showTab(currentStatusTab); }};
            catTabs.appendChild(tab);
          }});
        }}

        // Category summary table
        function renderCategorySummaryTable() {{
          const tbody = document.getElementById('categorySummaryBody');
          const tfoot = document.getElementById('categorySummaryFoot');
          tbody.innerHTML = '';
          tfoot.innerHTML = '';
          const allCats = categories;
          let grandTotal = 0, grandPassed = 0, grandFailed = 0, grandSkipped = 0;
          
          allCats.forEach(cat => {{
            const catTests = data.test_results.filter(t => (t.test_id||'').split(/\\d/)[0] === cat);
            const total = catTests.length;
            const passed = catTests.filter(t => t.status === 'Passed' || t.status === 'Success').length;
            const failed = catTests.filter(t => t.status === 'Failed').length;
            const skipped = catTests.filter(t => t.status === 'Skipped').length;
            
            grandTotal += total;
            grandPassed += passed;
            grandFailed += failed;
            grandSkipped += skipped;
            
            const tr = document.createElement('tr');
            tr.innerHTML = `<td class='link' onclick="filterCategory('${'{'}cat{'}'}')">${'{'}cat{'}'}</td>
                            <td>${'{'}total{'}'}</td>
                            <td style='color:#28a745;'>${'{'}passed{'}'}</td>
                            <td style='color:#dc3545;'>${'{'}failed{'}'}</td>
                            <td style='color:#6c757d;'>${'{'}skipped{'}'}</td>`;
            tbody.appendChild(tr);
          }});
          
          // Add total row in footer
          const totalTr = document.createElement('tr');
          totalTr.innerHTML = `<td style='font-weight:bold;background:#f8f9fa;'><b>Total</b></td>
                              <td style='font-weight:bold;background:#f8f9fa;'><b>${'{'}grandTotal{'}'}</b></td>
                              <td style='font-weight:bold;background:#f8f9fa;color:#28a745;'><b>${'{'}grandPassed{'}'}</b></td>
                              <td style='font-weight:bold;background:#f8f9fa;color:#dc3545;'><b>${'{'}grandFailed{'}'}</b></td>
                              <td style='font-weight:bold;background:#f8f9fa;color:#6c757d;'><b>${'{'}grandSkipped{'}'}</b></td>`;
          tfoot.appendChild(totalTr);
        }}

        window.filterCategory = function(cat) {{
          selectedCategory = cat;
          renderCategoryTabs();
          showTab(currentStatusTab);
        }}

        // Tab logic
        let currentStatusTab = 'All';
        window.showTab = function(status) {{
          currentStatusTab = status;
          document.getElementById('tab-all').classList.remove('active');
          document.getElementById('tab-pass').classList.remove('active');
          document.getElementById('tab-fail').classList.remove('active');
          if (status === 'All') {{
            document.getElementById('tab-all').classList.add('active');
          }} else if (status === 'Passed') {{
            document.getElementById('tab-pass').classList.add('active');
          }} else {{
            document.getElementById('tab-fail').classList.add('active');
          }}
          renderTestList(status);
        }}

        function renderTestList(status) {{
          const testList = document.getElementById('testList');
          testList.innerHTML = '';
          let filtered = data.test_results;
          if (selectedCategory !== 'All') {{
            filtered = filtered.filter(t => (t.test_id||'').split(/\\d/)[0] === selectedCategory);
          }}
          if (status === 'Passed') {{
            filtered = filtered.filter(t => t.status === 'Passed' || t.status === 'Success');
          }} else if (status === 'Failed') {{
            filtered = filtered.filter(t => t.status === 'Failed');
          }}
          if (currentSearch.trim() !== ''){{
            const q = currentSearch.toLowerCase();
            filtered = filtered.filter(t => (t.test_name||'').toLowerCase().includes(q) || (t.test_id||'').toLowerCase().includes(q));
          }}
          if (currentSort === 'status'){{
            filtered.sort((a, b) => {{ const order = {{ 'Passed': 0, 'Success': 0, 'Failed': 1, 'Skipped': 2 }}; return (order[a.status]||9) - (order[b.status]||9); }});
          }} else if (currentSort === 'name'){{
            filtered.sort((a,b)=> (a.test_name||'').localeCompare(b.test_name||''));
          }} else if (currentSort === 'duration'){{
            filtered.sort((a,b)=> (a.duration_ms||0) - (b.duration_ms||0));
          }}
          if (filtered.length === 0) {{
            testList.innerHTML = `<div style='padding:12px;'>No ${'{'}status === 'All' ? '' : status.toLowerCase(){'}'} test cases${'{'}selectedCategory !== 'All' ? ' in ' + selectedCategory : ''{'}' }.</div>`;
            return;
          }}
          filtered.forEach((test) => {{
            const testDiv = document.createElement('div');
            testDiv.className = 'test-item';

            const header = document.createElement('div');
            header.className = 'test-header';
            header.innerHTML = `<div>
                <span class="idtag">${'{'}test.test_id || ''{'}'}</span>
                <span class="test-name">${'{'}test.test_name{'}'}</span>
                <span class="badge ${'{'}(test.status||'').toLowerCase(){'}'}">${'{'}test.status{'}'}</span>
              </div>
              <div class="duration">${'{'}(test.duration_ms||0){'}'} ms</div>`;

            const detailsDiv = document.createElement('div');
            detailsDiv.className = 'details';
            detailsDiv.innerHTML = `<div style='margin-bottom:8px;color:#6b7b8c;font-size:12px;'><b>Test ID:</b> ${'{'}test.test_id || ''{'}'}</div>`;
            if (test.steps && test.steps.length > 0) {{
              test.steps.forEach((step) => {{
                const req = step.request ? JSON.stringify(step.request, null, 2) : '';
                const res = step.response ? JSON.stringify(step.response, null, 2) : '';
                const err = step.error ? `${'{'}step.error{'}'}` : '';
                
                // Generate example when test failed
                let exampleSection = '';
                if (test.status === 'Failed' && step.error) {{
                  const exampleRequest = step.request ? JSON.stringify(step.request, null, 2) : 
                    `{{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "Device.version",
  "params": {{}}
}}`;
                  const exampleResponse = (step.examples && step.examples.length > 0 && step.examples[0].expected_result !== undefined)
                    ? JSON.stringify(step.examples[0].expected_result, null, 2)
                    : (res || '');
                  exampleSection = `<h4 style='color:#28a745;'>✨ Expected Example</h4>
                    <div class='detail-grid' style='margin-bottom:10px;'>
                      <div class='col'>
                        <h5>Example Request</h5>
                        <pre style='background:#eaf7ef;border:1px solid #28a745;'>${'{'}exampleRequest{'}'}</pre>
                      </div>
                      <div class='col'>
                        <h5>Example Response</h5>
                        <pre style='background:#eaf7ef;border:1px solid #28a745;'>${'{'}exampleResponse{'}'}</pre>
                      </div>
                    </div>`;
                }}
                
                detailsDiv.innerHTML += `<div style='margin-bottom:12px;'>
                  <div><b>Step:</b> ${'{'}step.description || step.step_id || ''{'}'}</div>
                  <div class='detail-grid'>
                    <div class='col'>
                      <h4>Request <span class='link' onclick="copyText(this)">Copy</span></h4>
                      <pre>${'{'}req{'}'}</pre>
                    </div>
                    <div class='col'>
                      <h4>Response <span class='link' onclick="copyText(this)">Copy</span></h4>
                      <pre>${'{'}res{'}'}</pre>
                      ${'{'}err ? `<h4 style='color:#dc3545;'>❌ Error Details</h4><pre style='background:#fdecef;color:#842029;border:1px solid #dc3545;'>${'{'}err{'}'}</pre>` : ''{'}'}
                    </div>
                  </div>
                  ${'{'}exampleSection{'}'}
                </div>`;
              }});
            }}
            testDiv.appendChild(header);
            testDiv.appendChild(detailsDiv);

            header.addEventListener('click', function(e) {{
              if (e.target.tagName === 'A' || e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
              detailsDiv.style.display = detailsDiv.style.display === 'none' ? 'block' : 'none';
            }});

            testList.appendChild(testDiv);
          }});
        }}

        // Initial render
        renderCategoryTabs();
        renderCategorySummaryTable();
        window.showTab('All');

        // Enhance counters and bars
        const passPct = data.total_tests ? Math.round(((data.passed||0)/data.total_tests)*100) : 0;
        const passBar = document.getElementById('passBar');
        if (passBar) passBar.style.width = passPct + '%';

        // Controls listeners
        document.getElementById('searchBox').addEventListener('input', (e)=>{{ currentSearch = e.target.value || ''; showTab(currentStatusTab); }});
        document.getElementById('sortSelect').addEventListener('change', (e)=>{{ currentSort = e.target.value; showTab(currentStatusTab); }});

        // Expand/Collapse helpers
        window.expandAll = function(){{
          document.querySelectorAll('.details').forEach(d => d.style.display = 'block');
        }}
        window.collapseAll = function(){{
          document.querySelectorAll('.details').forEach(d => d.style.display = 'none');
        }}

        // Copy helper
        window.copyText = function(el){{
          const pre = el.closest('h4')?.nextElementSibling;
          if (!pre) return;
          const txt = pre.innerText;
          navigator.clipboard?.writeText(txt).then(()=>{{
            const old = el.textContent;
            el.textContent = 'Copied';
            setTimeout(()=> el.textContent = 'Copy', 1000);
          }}).catch(()=>{{}});
        }}
      </script>
    </body>
    </html>
    """

    out_path = os.path.join(os.getcwd(), 'CoreSanity_SchemaValidation_result_report.html')
    with open(out_path, 'w') as f:
        f.write(html)
    print(f"[SUCCESS] Generated test report: {out_path}")


if __name__ == '__main__':
    generate_test_report()