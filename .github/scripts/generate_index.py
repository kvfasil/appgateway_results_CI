import os
import json
from glob import glob

# WORKSPACE is the root of the repo (two directories up from .github/scripts/)
WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUMMARY_FILES = list(glob(os.path.join(WORKSPACE, '**/web_result/summary.json'), recursive=True))

# Structure: { 'develop': {branch: [ (proposition, date, html_path) ] }, 'release': {...} }
results = {'develop': {}, 'release': {}}

for summary_path in SUMMARY_FILES:
    try:
        with open(summary_path) as f:
            summary = json.load(f)
        # Extract proposition from folder path (2 levels up from summary.json)
        # Path structure: .../branch/proposition/web_result/summary.json
        web_result_dir = os.path.dirname(summary_path)
        proposition_from_path = os.path.basename(os.path.dirname(web_result_dir))
        for key in ['core_sanity_test', 'badger_sanity_test']:
            if key in summary:
                entry = summary[key]
                cat = entry.get('result_category', 'develop')
                branch = entry.get('branch', 'unknown')
                proposition = proposition_from_path  # Use folder name instead of JSON value
                date = entry.get('date', 'unknown')
                image = entry.get('image', '')
                rdk_version = entry.get('RDK version', '')
                result_data = entry.get('result', {})
                # Find HTML file in same dir
                html_name = 'fb_core_sanity_result.html' if key == 'core_sanity_test' else 'fb_badger_sanity_result.html'
                html_path = os.path.relpath(os.path.join(os.path.dirname(summary_path), html_name), WORKSPACE)
                if not os.path.exists(os.path.join(WORKSPACE, html_path)):
                    continue
                if branch not in results[cat]:
                    results[cat][branch] = []
                results[cat][branch].append((proposition, date, html_path, key, image, rdk_version, result_data))
    except Exception as e:
        print(f"[WARN] Could not process {summary_path}: {e}")

# Generate HTML for summary_tab.html
summary_html = [
    '<table class="summary-table">',
    '<tr><th class="col-title">Develop</th><th class="col-title">Release</th></tr>',
    '<tr>'
]
import datetime
def parse_date(dt):
    try:
        return datetime.datetime.strptime(dt, "%Y%m%d_%H%M%S")
    except Exception:
        return datetime.datetime.min

for col in ['develop', 'release']:
    col_html = ['<div class="col">']
    # Group by branch, sort branches by latest report date
    branch_dates = []
    for branch, reports in results[col].items():
        # Find latest date for this branch
        latest_date = max((parse_date(r[1]) for r in reports), default=datetime.datetime.min)
        branch_dates.append((branch, latest_date))
    branch_dates.sort(key=lambda x: x[1], reverse=True)
    for branch, _ in branch_dates:
        reports = results[col][branch]
        # Group reports by proposition
        prop_groups = {}
        for proposition, date, html_path, key, image, rdk_version, result_data in reports:
            if proposition not in prop_groups:
                prop_groups[proposition] = {}
            prop_groups[proposition][key] = (date, html_path, image, rdk_version, result_data)
        
        col_html.append(f'<details style="margin-bottom:10px;"><summary class="branch">{branch}</summary><div class="prop-list">')
        
        for proposition, tests in prop_groups.items():
            # Build each test row
            test_rows = []
            for key in ['core_sanity_test', 'badger_sanity_test']:
                if key in tests:
                    date, html_path, image, rdk_version, result_data = tests[key]
                    link_path = '../' + html_path
                    label = 'Core Sanity' if key == 'core_sanity_test' else 'Badger Sanity'
                    total = result_data.get('Total', 0)
                    passed = result_data.get('passed', 0)
                    failed = result_data.get('failed', 0)
                    skipped = result_data.get('skiped', 0)
                    pass_pct = round((passed / total * 100), 1) if total > 0 else 0
                    fail_pct = round((failed / total * 100), 1) if total > 0 else 0
                    skip_pct = round((skipped / total * 100), 1) if total > 0 else 0
                    test_rows.append(f'<a href="{link_path}" target="_blank" class="test-link"><span class="lbl">{label}</span><span class="nums"><span class="p">{passed}</span><span class="f">{failed}</span><span class="s">{skipped}</span></span><span class="bar"><span class="bp" style="width:{pass_pct}%"></span><span class="bf" style="width:{fail_pct}%"></span><span class="bs" style="width:{skip_pct}%"></span></span></a>')
            # Build complete card
            card_html = f'''<div class="prop-row">
                <div class="prop-name">{proposition}</div>
                <div class="prop-tests">{''.join(test_rows)}</div>
            </div>'''
            col_html.append(card_html)
        col_html.append('</div></details>')
    col_html.append('</div>')
    summary_html.append(f'<div class="column">{''.join(col_html)}</div>')

summary_tab_path = os.path.join(WORKSPACE, 'tabs', 'summary_tab.html')
html_out = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Summary</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); color: #1a2c42; margin: 0; padding: 0; }
        .container { display: flex; width: 100%; min-height: 100vh; }
        .column { flex: 1; padding: 16px; overflow-y: auto; }
        .column:first-child { border-right: 2px solid #e3e8ee; }
        
        .col-title { 
            font-weight: 700; 
            font-size: 16px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white;
            padding: 14px 18px; 
            margin: -16px -16px 16px -16px; 
            text-transform: uppercase;
            letter-spacing: 1px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .column:last-child .col-title {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        
        details { margin-bottom: 10px; }
        details summary { list-style: none; cursor: pointer; }
        details summary::-webkit-details-marker { display: none; }
        
        .branch { 
            color: #1a2c42; 
            font-weight: 600; 
            font-size: 14px;
            padding: 10px 14px; 
            background: white; 
            border-radius: 8px; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .branch::before { content: "▸"; color: #1976d2; transition: transform 0.2s; }
        details[open] .branch::before { transform: rotate(90deg); }
        .branch:hover { 
            background: #e3f2fd; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            transform: translateY(-1px);
        }
        
        .prop-list { 
            margin: 8px 0 0 0; 
            padding: 0; 
        }
        .prop-card { 
            display: grid;
            grid-template-columns: 80px 1fr;
            gap: 8px;
            margin-bottom: 6px;
            background: white;
            border-radius: 6px;
            padding: 8px 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .prop-name {
            font-weight: 700;
            font-size: 11px;
            color: #333;
            border-right: 2px solid #e3e8ee;
            padding-right: 8px;
            display: flex;
            align-items: center;
        }
        .prop-tests {
            display: flex;
            flex-direction: column;
        }
        
        .test-row-compact { 
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
            text-decoration: none;
            color: inherit;
            font-size: 11px;
        }
        .test-row-compact:hover { background: #f8f9fa; border-radius: 4px; margin: 0 -4px; padding: 4px; }
        .test-label { font-weight: 600; color: #1976d2; width: 45px; }
        .test-nums { display: flex; gap: 6px; font-family: monospace; font-size: 11px; min-width: 70px; }
        .test-nums .p { color: #28a745; font-weight: 700; }
        .test-nums .f { color: #dc3545; font-weight: 700; }
        .test-nums .s { color: #ff9800; }
        
        .mini-bar { 
            flex: 1;
            height: 6px; 
            background: #e3e8ee; 
            border-radius: 3px; 
            overflow: hidden; 
            display: flex;
            min-width: 60px;
        }
        .mini-bar .bp { background: #4caf50; height: 100%; }
        .mini-bar .bf { background: #f44336; height: 100%; }
        .mini-bar .bs { background: #ff9800; height: 100%; }
        
        /* Compact prop row */
        .prop-row {
            display: grid;
            grid-template-columns: 85px 1fr;
            gap: 8px;
            margin-bottom: 6px;
            background: white;
            border-radius: 6px;
            padding: 8px 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .test-link {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
            text-decoration: none;
            color: inherit;
            font-size: 11px;
        }
        .test-link:hover { background: #f8f9fa; border-radius: 4px; margin: 0 -4px; padding: 4px; }
        .test-link .lbl { font-weight: 600; color: #1976d2; width: 85px; }
        .test-link .nums { display: flex; gap: 6px; font-family: monospace; font-size: 11px; min-width: 70px; }
        .test-link .nums .p { color: #28a745; font-weight: 700; }
        .test-link .nums .f { color: #dc3545; font-weight: 700; }
        .test-link .nums .s { color: #ff9800; }
        .test-link .bar { flex: 1; height: 6px; background: #e3e8ee; border-radius: 3px; overflow: hidden; display: flex; min-width: 60px; }
        .test-link .bar .bp { background: #4caf50; height: 100%; }
        .test-link .bar .bf { background: #f44336; height: 100%; }
        .test-link .bar .bs { background: #ff9800; height: 100%; }
        
        /* Progress bar for summary */
        .mini-progress { 
            height: 8px; 
            background: #e3e8ee; 
            border-radius: 4px; 
            overflow: hidden; 
            display: flex;
            margin-top: 8px;
        }
        .mini-progress > div { height: 100%; }
        .mini-progress .passed { background: #4caf50; }
        .mini-progress .failed { background: #f44336; }
        .mini-progress .skipped { background: #ff9800; }
    </style>
</head>
<body>
    <div class="container">
        <div class="column">
            <div class="col-title">📁 Develop</div>
'''
html_out += summary_html[3].replace('<div class="column"><div class="col">', '').replace('</div></div>', '')
html_out += '''
        </div>
        <div class="column">
            <div class="col-title">🚀 Release</div>
'''
html_out += summary_html[4].replace('<div class="column"><div class="col">', '').replace('</div></div>', '')
html_out += '''
        </div>
    </div>
</body>
</html>
'''
with open(summary_tab_path, 'w') as f:
        f.write(html_out)
print(f"[SUCCESS] Updated summary_tab.html with all reports.")

# Generate search_tab.html
# Flatten all reports into a single list for search
all_reports = []
for cat in ['develop', 'release']:
    for branch, reports in results[cat].items():
        for proposition, date, html_path, key, image, rdk_version, result_data in reports:
            total = result_data.get('Total', 0)
            passed = result_data.get('passed', 0)
            failed = result_data.get('failed', 0)
            skipped = result_data.get('skiped', 0)
            pass_rate = round((passed / total * 100), 1) if total > 0 else 0
            all_reports.append({
                'category': cat,
                'branch': branch,
                'proposition': proposition,
                'date': date,
                'html_path': '../' + html_path,
                'test_type': 'Core Sanity' if key == 'core_sanity_test' else 'Badger Sanity',
                'image': image,
                'rdk_version': rdk_version,
                'total': total,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'pass_rate': pass_rate
            })

# Sort by date descending
all_reports.sort(key=lambda r: parse_date(r['date']), reverse=True)

# Get unique values for filters
propositions = sorted(set(r['proposition'] for r in all_reports))
test_types = sorted(set(r['test_type'] for r in all_reports))

# Find latest develop and release
latest_develop = next((r for r in all_reports if r['category'] == 'develop'), None)
latest_release = next((r for r in all_reports if r['category'] == 'release'), None)

# Generate JSON data for JS
import json as json_module
reports_json = json_module.dumps(all_reports)

search_tab_path = os.path.join(WORKSPACE, 'tabs', 'search_tab.html')
search_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Search Reports</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f4f7f9; color: #1a2c42; margin: 0; padding: 12px; }}
        h2 {{ margin-top: 0; margin-bottom: 12px; color: #1976d2; font-size: 18px; }}
        
        /* Latest Section */
        .latest-section {{ display: flex; gap: 12px; margin-bottom: 12px; }}
        .latest-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .latest-header h3 {{ margin: 0; color: #1976d2; font-size: 14px; }}
        .latest-prop-select {{ padding: 4px 8px; border: 1px solid #e3e8ee; border-radius: 4px; font-size: 11px; background: white; }}
        .latest-card {{ flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .latest-card.release {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .latest-card h3 {{ margin: 0 0 6px 0; font-size: 11px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }}
        .latest-card .branch-name {{ font-size: 16px; font-weight: 700; margin-bottom: 4px; }}
        .latest-card .test-row {{ display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.2); }}
        .latest-card .test-row:last-child {{ border-bottom: none; }}
        .latest-card .test-name {{ font-size: 12px; opacity: 0.9; }}
        .latest-card .test-rate {{ font-size: 14px; font-weight: 700; }}
        .latest-card .test-rate.high {{ color: #90EE90; }}
        .latest-card .test-rate.low {{ color: #FFB6C1; }}
        .latest-card a {{ color: white; text-decoration: underline; font-size: 11px; }}
        
        /* Search & Filters */
        .search-filters {{ background: white; padding: 10px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px; }}
        .search-row {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
        .search-input {{ flex: 1; min-width: 150px; padding: 8px 12px; border: 1px solid #e3e8ee; border-radius: 6px; font-size: 13px; transition: border-color 0.2s; }}
        .search-input:focus {{ outline: none; border-color: #1976d2; }}
        select {{ padding: 8px 10px; border: 1px solid #e3e8ee; border-radius: 6px; font-size: 12px; background: white; cursor: pointer; min-width: 120px; }}
        select:focus {{ outline: none; border-color: #1976d2; }}
        
        /* Quick Filters */
        .quick-filters {{ margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }}
        .quick-btn {{ padding: 4px 10px; border: none; border-radius: 12px; font-size: 11px; cursor: pointer; transition: all 0.2s; }}
        .quick-btn.all {{ background: #e3f2fd; color: #1976d2; }}
        .quick-btn.passed {{ background: #e8f5e9; color: #2e7d32; }}
        .quick-btn.failed {{ background: #ffebee; color: #c62828; }}
        .quick-btn.develop {{ background: #ede7f6; color: #5e35b1; }}
        .quick-btn.release {{ background: #e0f2f1; color: #00695c; }}
        .quick-btn:hover {{ transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .quick-btn.active {{ box-shadow: inset 0 2px 4px rgba(0,0,0,0.2); }}
        
        /* Results Count & Sort */
        .results-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .results-count {{ color: #666; font-size: 12px; }}
        .sort-select {{ padding: 6px 10px; border: 1px solid #e3e8ee; border-radius: 4px; font-size: 11px; }}
        
        /* Results Grid */
        .results-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; }}
        .result-card {{ background: white; border-radius: 8px; padding: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); transition: transform 0.2s, box-shadow 0.2s; }}
        .result-card:hover {{ transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .result-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }}
        .result-title {{ font-size: 14px; font-weight: 600; color: #1976d2; margin: 0; }}
        .result-title a {{ color: inherit; text-decoration: none; }}
        .result-title a:hover {{ text-decoration: underline; }}
        .badge {{ padding: 2px 6px; border-radius: 8px; font-size: 9px; font-weight: 600; text-transform: uppercase; }}
        .badge.develop {{ background: #ede7f6; color: #5e35b1; }}
        .badge.release {{ background: #e0f2f1; color: #00695c; }}
        .badge.coresanity {{ background: #fff3e0; color: #e65100; }}
        .badge.badgersanity {{ background: #e1f5fe; color: #0277bd; }}
        
        /* Test Section */
        .test-section {{ margin: 8px 0; padding: 8px; background: #fafafa; border-radius: 6px; border-left: 3px solid #1976d2; }}
        .test-section-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
        .pass-rate-inline {{ font-weight: 700; font-size: 12px; }}
        .pass-rate-inline.high {{ color: #2e7d32; }}
        .pass-rate-inline.medium {{ color: #e65100; }}
        .pass-rate-inline.low {{ color: #c62828; }}
        .view-link {{ font-size: 10px; color: #1976d2; text-decoration: none; margin-left: auto; }}
        .view-link:hover {{ text-decoration: underline; }}
        
        .result-meta {{ display: flex; gap: 12px; margin-bottom: 6px; font-size: 11px; color: #666; }}
        .result-meta span {{ display: flex; align-items: center; gap: 2px; }}
        
        /* Progress Bar */
        .progress-container {{ margin-top: 6px; }}
        .progress-bar {{ height: 6px; background: #e3e8ee; border-radius: 3px; overflow: hidden; display: flex; }}
        .progress-passed {{ background: #4caf50; }}
        .progress-failed {{ background: #f44336; }}
        .progress-skipped {{ background: #ff9800; }}
        .progress-stats {{ display: flex; justify-content: space-between; margin-top: 4px; font-size: 10px; }}
        .stat-passed {{ color: #4caf50; }}
        .stat-failed {{ color: #f44336; }}
        .stat-skipped {{ color: #ff9800; }}
        
        /* Details Section */
        .result-details {{ margin-top: 6px; padding-top: 6px; border-top: 1px solid #e3e8ee; font-size: 10px; }}
        .detail-row {{ display: flex; margin-bottom: 2px; }}
        .detail-label {{ width: 70px; color: #888; }}
        .detail-value {{ color: #333; word-break: break-all; flex: 1; }}
        
        /* Pass Rate Circle */
        .pass-rate {{ width: 44px; height: 44px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; }}
        .pass-rate.high {{ background: #e8f5e9; color: #2e7d32; }}
        .pass-rate.medium {{ background: #fff3e0; color: #e65100; }}
        .pass-rate.low {{ background: #ffebee; color: #c62828; }}
        .pass-rate span {{ font-size: 8px; font-weight: 400; }}
        
        /* No Results */
        .no-results {{ text-align: center; padding: 40px; color: #888; }}
        
        /* Actions */
        .result-actions {{ margin-top: 6px; display: flex; gap: 4px; }}
        .action-btn {{ padding: 4px 8px; border: 1px solid #e3e8ee; border-radius: 4px; font-size: 10px; cursor: pointer; background: white; color: #666; transition: all 0.2s; }}
        .action-btn:hover {{ background: #f4f7f9; border-color: #1976d2; color: #1976d2; }}
    </style>
</head>
<body>
    <h2>🔍 Search Reports</h2>
    
    <!-- Latest Section -->
    <div class="latest-header">
        <h3>📌 Latest Reports</h3>
        <select id="latestProposition" class="latest-prop-select" onchange="renderLatest()">
            {"\n".join(f'<option value="{p}"' + (' selected' if p == 'SKXI11ADS' else '') + f'>{p}</option>' for p in propositions)}
        </select>
    </div>
    <div class="latest-section">
        <div class="latest-card develop">
            <h3>📁 Latest Develop</h3>
            <div id="latest-develop">Loading...</div>
        </div>
        <div class="latest-card release">
            <h3>🚀 Latest Release</h3>
            <div id="latest-release">Loading...</div>
        </div>
    </div>
    
    <!-- Search & Filters -->
    <div class="search-filters">
        <div class="search-row">
            <input type="text" class="search-input" id="searchInput" placeholder="Search by branch, proposition, image...">
            <select id="filterProposition">
                <option value="">All Propositions</option>
                {"".join(f'<option value="{p}">{p}</option>' for p in propositions)}
            </select>
            <select id="filterTestType">
                <option value="">All Test Types</option>
                {"".join(f'<option value="{t}">{t}</option>' for t in test_types)}
            </select>
            <select id="filterCategory">
                <option value="">All Categories</option>
                <option value="develop">Develop</option>
                <option value="release">Release</option>
            </select>
        </div>
        <div class="quick-filters">
            <button class="quick-btn all active" onclick="quickFilter('all')">All</button>
            <button class="quick-btn passed" onclick="quickFilter('passed')">✓ High Pass Rate (&gt;80%)</button>
            <button class="quick-btn failed" onclick="quickFilter('failed')">✗ Low Pass Rate (&lt;50%)</button>
            <button class="quick-btn develop" onclick="quickFilter('develop')">Develop Only</button>
            <button class="quick-btn release" onclick="quickFilter('release')">Release Only</button>
        </div>
    </div>
    
    <!-- Results Header -->
    <div class="results-header">
        <span class="results-count" id="resultsCount">Loading...</span>
        <select class="sort-select" id="sortSelect" onchange="sortResults()">
            <option value="date-desc">Newest First</option>
            <option value="date-asc">Oldest First</option>
            <option value="pass-desc">Highest Pass Rate</option>
            <option value="pass-asc">Lowest Pass Rate</option>
            <option value="total-desc">Most Tests</option>
        </select>
    </div>
    
    <!-- Results Grid -->
    <div class="results-grid" id="resultsGrid"></div>
    
    <script>
        const allReports = {reports_json};
        let filteredReports = [...allReports];
        let currentQuickFilter = 'all';
        
        function formatDate(dateStr) {{
            if (!dateStr || dateStr === 'unknown') return 'Unknown';
            try {{
                const year = dateStr.substring(0, 4);
                const month = dateStr.substring(4, 6);
                const day = dateStr.substring(6, 8);
                const hour = dateStr.substring(9, 11);
                const min = dateStr.substring(11, 13);
                return `${{day}}/${{month}}/${{year}} ${{hour}}:${{min}}`;
            }} catch (e) {{
                return dateStr;
            }}
        }}
        
        function getPassRateClass(rate) {{
            if (rate >= 80) return 'high';
            if (rate >= 50) return 'medium';
            return 'low';
        }}
        
        function renderLatest() {{
            // Get selected proposition for latest filter
            const selectedProp = document.getElementById('latestProposition').value;
            const filteredReports = allReports.filter(r => r.proposition === selectedProp);
            
            // Get latest Core and Badger for both Develop and Release
            const latestDevCore = filteredReports.find(r => r.category === 'develop' && r.test_type === 'Core Sanity');
            const latestDevBadger = filteredReports.find(r => r.category === 'develop' && r.test_type === 'Badger Sanity');
            const latestRelCore = filteredReports.find(r => r.category === 'release' && r.test_type === 'Core Sanity');
            const latestRelBadger = filteredReports.find(r => r.category === 'release' && r.test_type === 'Badger Sanity');
            
            const getRateClass = (rate) => rate >= 50 ? 'high' : 'low';
            
            if (latestDevCore || latestDevBadger) {{
                const branch = (latestDevCore || latestDevBadger).branch;
                document.getElementById('latest-develop').innerHTML = `
                    <div class="branch-name">${{branch}}</div>
                    ${{latestDevCore ? `<div class="test-row"><span class="test-name">Core Sanity</span><span class="test-rate ${{getRateClass(latestDevCore.pass_rate)}}">${{latestDevCore.pass_rate}}%</span></div>` : ''}}
                    ${{latestDevBadger ? `<div class="test-row"><span class="test-name">Badger Sanity</span><span class="test-rate ${{getRateClass(latestDevBadger.pass_rate)}}">${{latestDevBadger.pass_rate}}%</span></div>` : ''}}
                    <div style="margin-top:8px;">
                        ${{latestDevCore ? `<a href="${{latestDevCore.html_path}}" target="_blank">Core</a>` : ''}}
                        ${{latestDevCore && latestDevBadger ? ' | ' : ''}}
                        ${{latestDevBadger ? `<a href="${{latestDevBadger.html_path}}" target="_blank">Badger</a>` : ''}}
                    </div>
                `;
            }} else {{
                document.getElementById('latest-develop').innerHTML = '<div style="opacity:0.7;font-size:12px;">No data for this proposition</div>';
            }}
            
            if (latestRelCore || latestRelBadger) {{
                const branch = (latestRelCore || latestRelBadger).branch;
                document.getElementById('latest-release').innerHTML = `
                    <div class="branch-name">${{branch}}</div>
                    ${{latestRelCore ? `<div class="test-row"><span class="test-name">Core Sanity</span><span class="test-rate ${{getRateClass(latestRelCore.pass_rate)}}">${{latestRelCore.pass_rate}}%</span></div>` : ''}}
                    ${{latestRelBadger ? `<div class="test-row"><span class="test-name">Badger Sanity</span><span class="test-rate ${{getRateClass(latestRelBadger.pass_rate)}}">${{latestRelBadger.pass_rate}}%</span></div>` : ''}}
                    <div style="margin-top:8px;">
                        ${{latestRelCore ? `<a href="${{latestRelCore.html_path}}" target="_blank">Core</a>` : ''}}
                        ${{latestRelCore && latestRelBadger ? ' | ' : ''}}
                        ${{latestRelBadger ? `<a href="${{latestRelBadger.html_path}}" target="_blank">Badger</a>` : ''}}
                    </div>
                `;
            }} else {{
                document.getElementById('latest-release').innerHTML = '<div style="opacity:0.7;font-size:12px;">No data for this proposition</div>';
            }}
        }}
        
        function renderResults() {{
            const grid = document.getElementById('resultsGrid');
            const count = document.getElementById('resultsCount');
            
            // Group reports by branch + category + proposition
            const grouped = {{}};
            filteredReports.forEach(r => {{
                const key = `${{r.category}}-${{r.branch}}-${{r.proposition}}`;
                if (!grouped[key]) {{
                    grouped[key] = {{ category: r.category, branch: r.branch, proposition: r.proposition, date: r.date, image: r.image, rdk_version: r.rdk_version, core: null, badger: null }};
                }}
                if (r.test_type === 'Core Sanity') grouped[key].core = r;
                else grouped[key].badger = r;
                // Use latest date
                if (r.date > grouped[key].date) grouped[key].date = r.date;
            }});
            
            const groupedList = Object.values(grouped);
            count.textContent = `Showing ${{groupedList.length}} branches (${{filteredReports.length}} reports)`;
            
            if (groupedList.length === 0) {{
                grid.innerHTML = '<div class="no-results">No reports found matching your criteria</div>';
                return;
            }}
            
            grid.innerHTML = groupedList.map(g => {{
                const core = g.core;
                const badger = g.badger;
                return `
                <div class="result-card">
                    <div class="result-header">
                        <div>
                            <h3 class="result-title">${{g.branch}}</h3>
                            <span class="badge ${{g.category}}">${{g.category}}</span>
                        </div>
                    </div>
                    <div class="result-meta">
                        <span>📅 ${{formatDate(g.date)}}</span>
                        <span>📦 ${{g.proposition}}</span>
                    </div>
                    
                    ${{core ? `
                    <div class="test-section">
                        <div class="test-section-header">
                            <a href="${{core.html_path}}" target="_blank" class="badge coresanity" style="text-decoration:none;">Core Sanity</a>
                            <span class="pass-rate-inline ${{getPassRateClass(core.pass_rate)}}">${{core.pass_rate}}%</span>
                            <a href="${{core.html_path}}" target="_blank" class="view-link">View →</a>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar">
                                <div class="progress-passed" style="width: ${{core.total > 0 ? (core.passed/core.total*100) : 0}}%"></div>
                                <div class="progress-failed" style="width: ${{core.total > 0 ? (core.failed/core.total*100) : 0}}%"></div>
                                <div class="progress-skipped" style="width: ${{core.total > 0 ? (core.skipped/core.total*100) : 0}}%"></div>
                            </div>
                            <div class="progress-stats">
                                <span class="stat-passed">✓ ${{core.passed}}</span>
                                <span class="stat-failed">✗ ${{core.failed}}</span>
                                <span class="stat-skipped">○ ${{core.skipped}}</span>
                                <span>/ ${{core.total}}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}}
                    
                    ${{badger ? `
                    <div class="test-section">
                        <div class="test-section-header">
                            <a href="${{badger.html_path}}" target="_blank" class="badge badgersanity" style="text-decoration:none;">Badger Sanity</a>
                            <span class="pass-rate-inline ${{getPassRateClass(badger.pass_rate)}}">${{badger.pass_rate}}%</span>
                            <a href="${{badger.html_path}}" target="_blank" class="view-link">View →</a>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar">
                                <div class="progress-passed" style="width: ${{badger.total > 0 ? (badger.passed/badger.total*100) : 0}}%"></div>
                                <div class="progress-failed" style="width: ${{badger.total > 0 ? (badger.failed/badger.total*100) : 0}}%"></div>
                                <div class="progress-skipped" style="width: ${{badger.total > 0 ? (badger.skipped/badger.total*100) : 0}}%"></div>
                            </div>
                            <div class="progress-stats">
                                <span class="stat-passed">✓ ${{badger.passed}}</span>
                                <span class="stat-failed">✗ ${{badger.failed}}</span>
                                <span class="stat-skipped">○ ${{badger.skipped}}</span>
                                <span>/ ${{badger.total}}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}}
                    
                    <div class="result-details">
                        ${{g.image ? `<div class="detail-row"><span class="detail-label">Image:</span><span class="detail-value">${{g.image}}</span></div>` : ''}}
                        ${{g.rdk_version ? `<div class="detail-row"><span class="detail-label">RDK Ver:</span><span class="detail-value">${{g.rdk_version}}</span></div>` : ''}}
                    </div>
                </div>
            `}}).join('');
        }}
        
        function applyFilters() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const prop = document.getElementById('filterProposition').value;
            const testType = document.getElementById('filterTestType').value;
            const category = document.getElementById('filterCategory').value;
            
            filteredReports = allReports.filter(r => {{
                // Search filter
                if (search && !r.branch.toLowerCase().includes(search) && 
                    !r.proposition.toLowerCase().includes(search) &&
                    !r.image.toLowerCase().includes(search) &&
                    !r.rdk_version.toLowerCase().includes(search)) {{
                    return false;
                }}
                // Dropdown filters
                if (prop && r.proposition !== prop) return false;
                if (testType && r.test_type !== testType) return false;
                if (category && r.category !== category) return false;
                
                // Quick filters
                if (currentQuickFilter === 'passed' && r.pass_rate < 80) return false;
                if (currentQuickFilter === 'failed' && r.pass_rate >= 50) return false;
                if (currentQuickFilter === 'develop' && r.category !== 'develop') return false;
                if (currentQuickFilter === 'release' && r.category !== 'release') return false;
                
                return true;
            }});
            
            sortResults();
        }}
        
        function sortResults() {{
            const sort = document.getElementById('sortSelect').value;
            
            filteredReports.sort((a, b) => {{
                switch(sort) {{
                    case 'date-desc': return b.date.localeCompare(a.date);
                    case 'date-asc': return a.date.localeCompare(b.date);
                    case 'pass-desc': return b.pass_rate - a.pass_rate;
                    case 'pass-asc': return a.pass_rate - b.pass_rate;
                    case 'total-desc': return b.total - a.total;
                    default: return 0;
                }}
            }});
            
            renderResults();
        }}
        
        function quickFilter(type) {{
            currentQuickFilter = type;
            document.querySelectorAll('.quick-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.quick-btn.${{type}}`).classList.add('active');
            
            // Reset category dropdown if quick filter is develop/release
            if (type === 'develop' || type === 'release') {{
                document.getElementById('filterCategory').value = '';
            }}
            
            applyFilters();
        }}
        
        function copyToClipboard(text) {{
            const fullUrl = window.location.href.replace(/\\/[^\\/]*$/, '/') + text.replace('../', '');
            navigator.clipboard.writeText(fullUrl).then(() => {{
                alert('Link copied to clipboard!');
            }});
        }}
        
        // Event listeners
        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('filterProposition').addEventListener('change', applyFilters);
        document.getElementById('filterTestType').addEventListener('change', applyFilters);
        document.getElementById('filterCategory').addEventListener('change', applyFilters);
        
        // Initial render
        renderLatest();
        renderResults();
    </script>
</body>
</html>
'''

with open(search_tab_path, 'w') as f:
    f.write(search_html)
print(f"[SUCCESS] Updated search_tab.html with search functionality.")

# Generate graphs_tab.html
# Prepare data for charts - group by branch and date
chart_data = []
for r in all_reports:
    chart_data.append({
        'category': r['category'],
        'branch': r['branch'],
        'proposition': r['proposition'],
        'date': r['date'],
        'test_type': r['test_type'],
        'pass_rate': r['pass_rate'],
        'passed': r['passed'],
        'failed': r['failed'],
        'skipped': r['skipped'],
        'total': r['total']
    })

# Get unique propositions for filter
all_propositions = sorted(set(r['proposition'] for r in all_reports))
proposition_options = ''.join(f'<option value="{p}">{p}</option>' for p in all_propositions)

chart_data_json = json_module.dumps(chart_data)

graphs_tab_path = os.path.join(WORKSPACE, 'tabs', 'graphs_tab.html')
graphs_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Graphs</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f4f7f9; color: #1a2c42; margin: 0; padding: 16px; }}
        h2 {{ margin-top: 0; color: #1976d2; font-size: 18px; }}
        
        .filters {{ background: white; padding: 12px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); margin-bottom: 16px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
        select {{ padding: 8px 12px; border: 1px solid #e3e8ee; border-radius: 6px; font-size: 13px; }}
        label {{ font-size: 13px; font-weight: 600; color: #666; }}
        
        .checkbox-group {{ display: flex; gap: 16px; align-items: center; margin-left: 12px; padding-left: 12px; border-left: 1px solid #e3e8ee; }}
        .checkbox-item {{ display: flex; align-items: center; gap: 4px; cursor: pointer; }}
        .checkbox-item input {{ cursor: pointer; }}
        .checkbox-item.passed {{ color: #4caf50; }}
        .checkbox-item.failed {{ color: #f44336; }}
        .checkbox-item.skipped {{ color: #ff9800; }}
        
        .charts-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .chart-card {{ background: white; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .chart-card.full-width {{ grid-column: 1 / -1; }}
        .chart-title {{ font-size: 14px; font-weight: 600; color: #333; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
        .chart-wrapper {{ position: relative; height: 280px; }}
        .chart-wrapper.tall {{ height: 350px; }}
        
        .legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; font-size: 11px; }}
        .legend-item {{ display: flex; align-items: center; gap: 4px; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 2px; }}
        
        @media (max-width: 900px) {{
            .charts-container {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <h2>📊 Test Results Over Time</h2>
    
    <div class="filters">
        <label>Test Type:</label>
        <select id="filterTestType" onchange="updateCharts()">
            <option value="">All</option>
            <option value="Core Sanity">Core Sanity</option>
            <option value="Badger Sanity">Badger Sanity</option>
        </select>
        
        <label>Proposition:</label>
        <select id="filterProposition" onchange="updateCharts()">
            <option value="">All</option>
            {proposition_options}
        </select>
        
        <div class="checkbox-group">
            <label class="checkbox-item passed">
                <input type="checkbox" id="showPassed" checked onchange="updateCharts()"> Passed
            </label>
            <label class="checkbox-item failed">
                <input type="checkbox" id="showFailed" checked onchange="updateCharts()"> Failed
            </label>
            <label class="checkbox-item skipped">
                <input type="checkbox" id="showSkipped" checked onchange="updateCharts()"> Skipped
            </label>
        </div>
    </div>
    
    <div class="charts-container">
        <!-- Develop Line Graph -->
        <div class="chart-card full-width">
            <div class="chart-title">📁 Develop - Test Results by Branch (sorted by generation time)</div>
            <div class="chart-wrapper tall">
                <canvas id="developChart"></canvas>
            </div>
            <div class="legend">
                <span class="legend-item"><span class="legend-color" style="background:#4caf50"></span> Passed</span>
                <span class="legend-item"><span class="legend-color" style="background:#f44336"></span> Failed</span>
                <span class="legend-item"><span class="legend-color" style="background:#ff9800"></span> Skipped</span>
            </div>
        </div>
        
        <!-- Release Line Graph -->
        <div class="chart-card full-width">
            <div class="chart-title">🚀 Release - Test Results by Branch (sorted by generation time)</div>
            <div class="chart-wrapper tall">
                <canvas id="releaseChart"></canvas>
            </div>
            <div class="legend">
                <span class="legend-item"><span class="legend-color" style="background:#4caf50"></span> Passed</span>
                <span class="legend-item"><span class="legend-color" style="background:#f44336"></span> Failed</span>
                <span class="legend-item"><span class="legend-color" style="background:#ff9800"></span> Skipped</span>
            </div>
        </div>
    </div>
    
    <script>
        const allData = {chart_data_json};
        
        // Parse date string to Date object
        function parseDate(dateStr) {{
            if (!dateStr || dateStr.length < 8) return new Date();
            const year = parseInt(dateStr.substring(0, 4));
            const month = parseInt(dateStr.substring(4, 6)) - 1;
            const day = parseInt(dateStr.substring(6, 8));
            const hour = dateStr.length >= 11 ? parseInt(dateStr.substring(9, 11)) : 0;
            const min = dateStr.length >= 13 ? parseInt(dateStr.substring(11, 13)) : 0;
            return new Date(year, month, day, hour, min);
        }}
        
        // Format date for display
        function formatDate(dateStr) {{
            const d = parseDate(dateStr);
            return d.toLocaleDateString('en-GB', {{ day: '2-digit', month: 'short', year: 'numeric' }});
        }}
        
        // Color palette
        const colors = [
            '#1976d2', '#43a047', '#e53935', '#fb8c00', '#8e24aa',
            '#00acc1', '#3949ab', '#7cb342', '#f4511e', '#6d4c41'
        ];
        
        let developChart, releaseChart;
        
        function createCategoryLineChart(category, canvasId, chartRef) {{
            const testType = document.getElementById('filterTestType').value;
            const proposition = document.getElementById('filterProposition').value;
            let data = allData.filter(d => d.category === category);
            if (testType) data = data.filter(d => d.test_type === testType);
            if (proposition) data = data.filter(d => d.proposition === proposition);
            
            // Group by branch, aggregate passed/failed/skipped, track latest date for sorting
            const branchMap = {{}};
            data.forEach(d => {{
                if (!branchMap[d.branch]) {{
                    branchMap[d.branch] = {{ passed: 0, failed: 0, skipped: 0, latestDate: d.date }};
                }}
                branchMap[d.branch].passed += d.passed;
                branchMap[d.branch].failed += d.failed;
                branchMap[d.branch].skipped += d.skipped;
                if (d.date > branchMap[d.branch].latestDate) {{
                    branchMap[d.branch].latestDate = d.date;
                }}
            }});
            
            // Sort branches by latest date (oldest first, so most recent on right)
            const sortedBranches = Object.keys(branchMap).sort((a, b) => 
                branchMap[a].latestDate.localeCompare(branchMap[b].latestDate)
            );
            
            const passedData = sortedBranches.map(b => branchMap[b].passed);
            const failedData = sortedBranches.map(b => branchMap[b].failed);
            const skippedData = sortedBranches.map(b => branchMap[b].skipped);
            
            // Check which datasets to show
            const showPassed = document.getElementById('showPassed').checked;
            const showFailed = document.getElementById('showFailed').checked;
            const showSkipped = document.getElementById('showSkipped').checked;
            
            const datasets = [];
            if (showPassed) {{
                datasets.push({{
                    label: 'Passed',
                    data: passedData,
                    borderColor: '#4caf50',
                    backgroundColor: '#4caf5033',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#4caf50'
                }});
            }}
            if (showFailed) {{
                datasets.push({{
                    label: 'Failed',
                    data: failedData,
                    borderColor: '#f44336',
                    backgroundColor: '#f4433633',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#f44336'
                }});
            }}
            if (showSkipped) {{
                datasets.push({{
                    label: 'Skipped',
                    data: skippedData,
                    borderColor: '#ff9800',
                    backgroundColor: '#ff980033',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#ff9800'
                }});
            }}
            
            const ctx = document.getElementById(canvasId).getContext('2d');
            if (chartRef) chartRef.destroy();
            return new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: sortedBranches,
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            title: {{ display: true, text: 'Branch (sorted by generation time →)' }}
                        }},
                        y: {{
                            beginAtZero: true,
                            title: {{ display: true, text: 'Test Count' }}
                        }}
                    }},
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                afterTitle: (ctx) => {{
                                    const branch = ctx[0].label;
                                    const info = branchMap[branch];
                                    return `Generated: ${{formatDate(info.latestDate)}}`;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}
        
        function updateCharts() {{
            developChart = createCategoryLineChart('develop', 'developChart', developChart);
            releaseChart = createCategoryLineChart('release', 'releaseChart', releaseChart);
        }}
        
        // Initial render
        updateCharts();
    </script>
</body>
</html>
'''

with open(graphs_tab_path, 'w') as f:
    f.write(graphs_html)
print(f"[SUCCESS] Updated graphs_tab.html with charts.")
