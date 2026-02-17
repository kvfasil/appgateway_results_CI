import os
import sys
import json

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Badger Core Sanity Test Report</title>
  <style>
    body { font-family: sans-serif; background: #f4f7f9; color: #1a2c42; }
    .container { max-width: 950px; margin: 32px auto; background: #fff; border-radius: 10px; box-shadow: 0 6px 16px rgba(0,0,0,0.08); padding: 28px; }
    h1 { text-align: center; }
    .platform-info { display: flex; justify-content: space-between; align-items: center; background: #e9eef3; border-radius: 8px; padding: 10px 18px; margin: 18px 0 18px 0; font-size: 15px; }
    .platform-info .left { font-weight: 600; }
    .platform-info .right { text-align: right; }
    .platform-info .value { font-weight: 600; }
    .summary { display: flex; justify-content: space-around; margin: 18px 0 24px 0; }
    .summary div { background: #f4f7f9; border-radius: 8px; padding: 12px 18px; min-width: 90px; text-align: center; box-shadow: 0 1px 4px #0001; }
    .summary .passed { color: #28a745; }
    .summary .failed { color: #dc3545; }
    .summary .skipped { color: #6c757d; }
    ul { padding-left: 0; list-style: none; }
    li.test-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px;
      margin-bottom: 8px;
      background: #f9fafb;
      border-radius: 6px;
      border: 1px solid #e3e8ee;
      font-size: 15px;
      transition: box-shadow 0.2s;
      box-shadow: 0 1px 2px #0001;
    }
    li.test-row:hover { box-shadow: 0 2px 8px #0002; background: #f3f6fa; }
    .test-id { font-family: monospace; color: #1976d2; min-width: 110px; font-size: 14px; }
    .test-name { flex: 1; margin: 0 18px; font-weight: 500; }
    .test-status { min-width: 80px; text-align: right; font-size: 14px; font-weight: 600; border-radius: 12px; padding: 3px 12px; }
    .test-status.passed { color: #28a745; background: #eaf7ef; border: 1px solid #28a745; }
    .test-status.failed { color: #dc3545; background: #fdecef; border: 1px solid #dc3545; }
    .test-status.skipped { color: #6c757d; background: #eef1f4; border: 1px solid #6c757d; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Badger Core Sanity Test Report</h1>
    <div class="platform-info">
      <div class="left">
        <span class="value" id="imagename"></span><br>
        <span class="value" id="middleware_version"></span>
      </div>
      <div class="right">
        <span class="value" id="test_date"></span><br>
        <span class="value" id="fw_class"></span>
      </div>
    </div>
    <div class="summary">
      <div id="sumTotal" style="cursor:pointer;"><b>Total</b><br><span id="totalTests"></span></div>
      <div id="sumPassed" class="passed" style="cursor:pointer;"><b>Passed</b><br><span id="passedTests"></span></div>
      <div id="sumFailed" class="failed" style="cursor:pointer;"><b>Failed</b><br><span id="failedTests"></span></div>
      <div id="sumSkipped" class="skipped" style="cursor:pointer;"><b>Skipped</b><br><span id="skippedTests"></span></div>
      <div><b>Duration</b><br><span id="duration"></span></div>
    </div>
    <table id="catSummary" style="width:100%;margin-bottom:18px;background:#f9fafb;border-radius:8px;box-shadow:0 1px 4px #0001;overflow:hidden;">
      <thead style="background:#e9eef3;font-weight:bold;"><tr><td>Category</td><td style='color:#28a745;cursor:pointer;'>Passed</td><td style='color:#dc3545;cursor:pointer;'>Failed</td><td style='color:#6c757d;cursor:pointer;'>Skipped</td></tr></thead>
      <tbody></tbody>
    </table>
    <input id="filterInput" type="text" placeholder="Filter by name or ID..." style="width:100%;margin-bottom:12px;padding:8px 10px;border-radius:6px;border:1px solid #ccc;font-size:15px;" />
    <ul id="testNames"></ul>
  </div>
  <script>
    const data = __DATA__;
    // Platform info values (injected by Python)
    let img = data._platform?.imagename || '';
    if (img) {
      let parts = img.split('_');
      let trimmed = parts.slice(0, 4).join('_');
      document.getElementById('imagename').textContent = trimmed;
    } else {
      document.getElementById('imagename').textContent = '';
    }
    document.getElementById('middleware_version').textContent = data._platform?.MIDDLEWARE_VERSION || '';
    document.getElementById('fw_class').textContent = data._platform?.FW_CLASS || '';
    let dt = data._platform?.test_date || '';
    if (/^\d{8}_\d{6}$/.test(dt)) {
      const y = dt.slice(0,4), m = dt.slice(4,6), d = dt.slice(6,8);
      const hh = dt.slice(9,11), mm = dt.slice(11,13), ss = dt.slice(13,15);
      document.getElementById('test_date').textContent = `${y}-${m}-${d} ${hh}:${mm}:${ss}`;
    } else {
      document.getElementById('test_date').textContent = dt;
    }
    document.getElementById('totalTests').textContent = data.total_tests || (data.test_results ? data.test_results.length : 0);
    document.getElementById('passedTests').textContent = data.passed || 0;
    document.getElementById('failedTests').textContent = data.failed || 0;
    document.getElementById('skippedTests').textContent = data.skipped || 0;
    document.getElementById('duration').textContent = (data.duration_ms || 0) + ' ms';
    const ul = document.getElementById('testNames');
    const filterInput = document.getElementById('filterInput');
    let currentCategory = null;
    let currentStatus = null;
    function renderList() {
      ul.innerHTML = '';
      const q = (filterInput.value || '').toLowerCase();
      (data.test_results || []).forEach((test, idx) => {
        let cat = (test.test_id||'').split(/\d/)[0];
        if ((currentCategory && cat !== currentCategory)) return;
        if (currentStatus && currentStatus !== 'Total') {
          if (currentStatus === 'Passed' && !(test.status === 'Passed' || test.status === 'Success')) return;
          if (currentStatus === 'Failed' && test.status !== 'Failed') return;
          if (currentStatus === 'Skipped' && test.status !== 'Skipped') return;
        }
        if (!q || (test.test_name && test.test_name.toLowerCase().includes(q)) || (test.test_id && test.test_id.toLowerCase().includes(q))) {
          const li = document.createElement('li');
          li.className = 'test-row';
          li.style.cursor = 'pointer';
          let statusClass = '';
          if (test.status === 'Passed' || test.status === 'Success') statusClass = 'passed';
          else if (test.status === 'Failed') statusClass = 'failed';
          else if (test.status === 'Skipped') statusClass = 'skipped';
          li.innerHTML = `<span class=\"test-id\">${test.test_id || ''}</span><span class=\"test-name\">${test.test_name || ''}</span><span class=\"test-status ${statusClass}\">${test.status || ''}</span>`;
          const details = document.createElement('div');
          details.style.display = 'none';
          details.style.background = '#f9fafb';
          details.style.border = '1px solid #e3e8ee';
          details.style.borderRadius = '6px';
          details.style.margin = '0 0 12px 0';
          details.style.padding = '10px 14px';
          details.style.fontSize = '14px';
          details.style.position = 'relative';
          let html = `<div><b>Status:</b> ${test.status || ''}</div>`;
          html += `<div><b>Duration:</b> ${test.duration_ms || 0} ms</div>`;
          if (test.status === 'Skipped') {
            if (test.steps && test.steps.length > 0) {
              html += `<div><b>Steps:</b><ol style='margin:6px 0 0 18px;'>`;
              test.steps.forEach((step, idx) => {
                html += `<li><b>${step.description || step.step_id || ''}</b><br>`;
                if (step.request) html += `<span>Request:<br><pre style='background:#eef2f5;padding:6px 8px;border-radius:4px;margin:4px 0;'>${JSON.stringify(step.request, null, 2)}</pre></span>`;
                if (step.response) html += `<span>Response:<br><pre style='background:#eef2f5;padding:6px 8px;border-radius:4px;margin:4px 0;'>${JSON.stringify(step.response, null, 2)}</pre></span>`;
                if (step.error) html += `<span style='color:#c00;'>Error: ${step.error}</span><br>`;
                if (step.examples && step.examples.length > 0) {
                  const ex = step.examples[0];
                  html += `<div style='margin-top:6px;'><b>Example Result:</b><br><pre style='background:#eaf7ef;padding:6px 8px;border-radius:4px;margin:4px 0;'>${JSON.stringify(ex.expected_result, null, 2)}</pre></div>`;
                }
                html += `</li>`;
              });
              html += `</ol></div>`;
            }
            if (test.error) html += `<div style='color:#c00;'><b>Error:</b> ${test.error}</div>`;
          } else {
            if (test.error) html += `<div style='color:#c00;'><b>Error:</b> ${test.error}</div>`;
            if (test.steps && test.steps.length > 0) {
              html += `<div><b>Steps:</b><ol style='margin:6px 0 0 18px;'>`;
              test.steps.forEach((step, idx) => {
                html += `<li><b>${step.description || step.step_id || ''}</b><br>`;
                if (step.status) html += `<span>Status: ${step.status}</span><br>`;
                if (step.request) html += `<span>Request:<br><pre style='background:#eef2f5;padding:6px 8px;border-radius:4px;margin:4px 0;'>${JSON.stringify(step.request, null, 2)}</pre></span>`;
                if (step.response) html += `<span>Response:<br><pre style='background:#eef2f5;padding:6px 8px;border-radius:4px;margin:4px 0;'>${JSON.stringify(step.response, null, 2)}</pre></span>`;
                if (step.error) html += `<span style='color:#c00;'>Error: ${step.error}</span><br>`;
                if ((test.status === 'Failed' || step.status === 'Failed') && step.examples && step.examples.length > 0) {
                  const ex = step.examples[0];
                  html += `<div style='margin-top:6px;'><b>Example Result:</b><br><pre style='background:#eaf7ef;padding:6px 8px;border-radius:4px;margin:4px 0;'>${JSON.stringify(ex.expected_result, null, 2)}</pre></div>`;
                }
                html += `</li>`;
              });
              html += `</ol></div>`;
            }
          }
          details.innerHTML = html;
          li.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' || e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
            Array.from(ul.children).forEach((otherLi, i) => {
              if (otherLi !== li) {
                const otherDetails = otherLi.nextSibling;
                if (otherDetails && otherDetails.classList && otherDetails.classList.contains('test-details')) {
                  otherDetails.style.display = 'none';
                }
              }
            });
            details.style.display = details.style.display === 'none' ? 'block' : 'none';
          });
          details.classList.add('test-details');
          ul.appendChild(li);
          ul.appendChild(details);
        }
      });
    }
    function renderCatSummary() {
      const tbody = document.querySelector('#catSummary tbody');
      tbody.innerHTML = '';
      const catStats = {};
      let totalPassed = 0, totalFailed = 0, totalSkipped = 0;
      (data.test_results || []).forEach(test => {
        let cat = (test.test_id||'').split(/\d/)[0];
        if (!catStats[cat]) catStats[cat] = {passed:0,failed:0,skipped:0};
        if (test.status === 'Passed' || test.status === 'Success') { catStats[cat].passed++; totalPassed++; }
        else if (test.status === 'Failed') { catStats[cat].failed++; totalFailed++; }
        else if (test.status === 'Skipped') { catStats[cat].skipped++; totalSkipped++; }
      });
      Object.entries(catStats).forEach(([cat, stat]) => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.innerHTML = `<td>${cat}</td><td style='color:#28a745;'>${stat.passed}</td><td style='color:#dc3545;'>${stat.failed}</td><td style='color:#6c757d;'>${stat.skipped}</td>`;
        tr.children[0].onclick = (e) => {
          e.stopPropagation();
          currentCategory = (currentCategory === cat) ? null : cat;
          currentStatus = null;
          renderList();
          Array.from(tbody.children).forEach(row => row.style.background = '');
          if (currentCategory) tr.style.background = '#e0e7ef';
        };
        tr.children[1].onclick = (e) => {
          e.stopPropagation();
          currentCategory = cat;
          currentStatus = 'Passed';
          renderList();
          Array.from(tbody.children).forEach(row => row.style.background = '');
          tr.style.background = '#e0e7ef';
        };
        tr.children[2].onclick = (e) => {
          e.stopPropagation();
          currentCategory = cat;
          currentStatus = 'Failed';
          renderList();
          Array.from(tbody.children).forEach(row => row.style.background = '');
          tr.style.background = '#e0e7ef';
        };
        tr.children[3].onclick = (e) => {
          e.stopPropagation();
          currentCategory = cat;
          currentStatus = 'Skipped';
          renderList();
          Array.from(tbody.children).forEach(row => row.style.background = '');
          tr.style.background = '#e0e7ef';
        };
        tbody.appendChild(tr);
      });
      const totalTr = document.createElement('tr');
      totalTr.style.background = '#f3f6fa';
      totalTr.style.fontWeight = 'bold';
      totalTr.innerHTML = `<td>Total</td><td style='color:#28a745;'>${totalPassed}</td><td style='color:#dc3545;'>${totalFailed}</td><td style='color:#6c757d;'>${totalSkipped}</td>`;
      totalTr.children[0].onclick = (e) => {
        e.stopPropagation();
        currentCategory = null;
        currentStatus = 'Total';
        renderList();
        Array.from(tbody.children).forEach(row => row.style.background = '');
        totalTr.style.background = '#e0e7ef';
      };
      totalTr.children[1].onclick = (e) => {
        e.stopPropagation();
        currentCategory = null;
        currentStatus = 'Passed';
        renderList();
        Array.from(tbody.children).forEach(row => row.style.background = '');
        totalTr.style.background = '#e0e7ef';
      };
      totalTr.children[2].onclick = (e) => {
        e.stopPropagation();
        currentCategory = null;
        currentStatus = 'Failed';
        renderList();
        Array.from(tbody.children).forEach(row => row.style.background = '');
        totalTr.style.background = '#e0e7ef';
      };
      totalTr.children[3].onclick = (e) => {
        e.stopPropagation();
        currentCategory = null;
        currentStatus = 'Skipped';
        renderList();
        Array.from(tbody.children).forEach(row => row.style.background = '');
        totalTr.style.background = '#e0e7ef';
      };
      tbody.appendChild(totalTr);
    }
    renderCatSummary();
    renderList();
  </script>
</body>
</html>
'''

def parse_version_txt(version_txt_path, folder_name):
  platform = {}
  if not os.path.isfile(version_txt_path):
    return platform
  with open(version_txt_path) as f:
    for line in f:
      if line.startswith('imagename:'):
        platform['imagename'] = line.strip().split(':',1)[1]
      elif line.startswith('MIDDLEWARE_VERSION='):
        platform['MIDDLEWARE_VERSION'] = line.strip().split('=',1)[1]
      elif line.startswith('FW_CLASS='):
        platform['FW_CLASS'] = line.strip().split('=',1)[1]
  platform['test_date'] = folder_name
  return platform

def main():
  if len(sys.argv) != 2:
    print("Usage: python generate_badger_report_js.py <result_json>")
    sys.exit(1)
  json_path = sys.argv[1]
  if not os.path.isfile(json_path):
    print(f"File not found: {json_path}")
    sys.exit(1)
  version_txt_path = os.path.join(os.path.dirname(json_path), 'version.txt')
  folder_name = os.path.basename(os.path.dirname(json_path))
  platform = parse_version_txt(version_txt_path, folder_name)
  with open(json_path) as f:
    data = json.load(f)
  data['_platform'] = platform
  html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data))
  output_dir = os.path.join(os.path.dirname(os.path.dirname(json_path)), 'web_result')
  os.makedirs(output_dir, exist_ok=True)
  output_html = os.path.join(output_dir, 'fb_badger_sanity_result.html')
  with open(output_html, 'w') as f:
    f.write(html)
  print(f"[SUCCESS] Generated JS-based report: {output_html}")

  # --- Create or update summary.json ---
  summary_path = os.path.join(output_dir, 'summary.json')
  # Extract values from input path (e.g., develop/RDKEMW-2222/SCXI11BEI/20260217_124421)
  path_parts = os.path.normpath(json_path).split(os.sep)
  # result_category: develop
  result_category = path_parts[0] if len(path_parts) > 0 else ''
  # branch: RDKEMW-2222
  branch = path_parts[1] if len(path_parts) > 1 else ''
  # proposition: SCXI11BEI
  proposition = path_parts[2] if len(path_parts) > 2 else ''
  # date: 20260217_124421
  date = path_parts[3] if len(path_parts) > 3 else ''
  image = platform.get('imagename', '')
  rdk_version = platform.get('MIDDLEWARE_VERSION', '')
  total = data.get('total_tests', len(data.get('test_results', [])))
  passed = data.get('passed', 0)
  failed = data.get('failed', 0)
  skipped = data.get('skipped', 0)

  badger_sanity_test = {
    'result_category': result_category,
    'date': date,
    'image': image,
    'RDK version': rdk_version,
    'branch': branch,
    'proposition': proposition,
    'result': {
      'Total': total,
      'passed': passed,
      'failed': failed,
      'skiped': skipped
    }
  }

  # Load or create summary.json
  summary = {}
  if os.path.isfile(summary_path):
    try:
      with open(summary_path) as f:
        summary = json.load(f)
    except Exception:
      summary = {}
  # Update or add badger_sanity_test
  summary['badger_sanity_test'] = badger_sanity_test
  with open(summary_path, 'w') as f:
    json.dump(summary, f, indent=2)
  print(f"[SUCCESS] Updated summary.json: {summary_path}")

if __name__ == "__main__":
  main()
