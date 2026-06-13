"""
/dashboard — single-file HTML dashboard, no build step needed.

Polls /api/stats every 2 seconds and renders:
  - Live counters per algorithm (allowed / denied / throttle %)
  - Rolling line chart: allowed vs denied over the last 60 data points
  - Per-algorithm bar chart: throttle rate %
  - p99 latency badges
"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rate Limiter Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #0f1117;
    --surface:   #1a1d27;
    --border:    #2a2d3e;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --green:     #22c55e;
    --red:       #ef4444;
    --blue:      #3b82f6;
    --yellow:    #f59e0b;
    --purple:    #a855f7;
    --fw:        #3b82f6;
    --sw:        #22c55e;
    --tb:        #f59e0b;
    --lb:        #a855f7;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    min-height: 100vh;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }

  header h1 { font-size: 16px; font-weight: 600; letter-spacing: 0.01em; }
  header h1 span { color: var(--blue); }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--muted);
  }

  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
  }

  main { padding: 24px; display: flex; flex-direction: column; gap: 24px; }

  /* ── Top stats ── */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
  }

  .stat-label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 28px;
    font-weight: 600;
    line-height: 1;
  }

  .stat-value.green { color: var(--green); }
  .stat-value.red   { color: var(--red); }
  .stat-value.blue  { color: var(--blue); }

  /* ── Algorithm cards ── */
  .algo-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }

  .algo-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    border-top: 3px solid var(--border);
  }

  .algo-card.fw { border-top-color: var(--fw); }
  .algo-card.sw { border-top-color: var(--sw); }
  .algo-card.tb { border-top-color: var(--tb); }
  .algo-card.lb { border-top-color: var(--lb); }

  .algo-name {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin-bottom: 12px;
  }

  .algo-metrics { display: flex; flex-direction: column; gap: 8px; }

  .metric-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
  }

  .metric-row .label { color: var(--muted); }
  .metric-row .val   { font-weight: 500; }
  .metric-row .val.green { color: var(--green); }
  .metric-row .val.red   { color: var(--red); }
  .metric-row .val.muted { color: var(--muted); }

  .throttle-bar {
    height: 4px;
    background: var(--border);
    border-radius: 99px;
    overflow: hidden;
    margin-top: 6px;
  }

  .throttle-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.5s ease;
    background: var(--red);
  }

  /* ── Charts ── */
  .charts-row {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 16px;
  }

  .chart-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
  }

  .chart-title {
    font-size: 13px;
    font-weight: 500;
    color: var(--muted);
    margin-bottom: 16px;
  }

  .chart-wrap { position: relative; height: 220px; }

  /* ── Footer ── */
  footer {
    text-align: center;
    padding: 16px;
    font-size: 11px;
    color: var(--muted);
    border-top: 1px solid var(--border);
  }
</style>
</head>
<body>

<header>
  <h1>Rate Limiter <span>Dashboard</span></h1>
  <div class="status">
    <div class="dot" id="dot"></div>
    <span id="last-update">Connecting…</span>
  </div>
</header>

<main>
  <!-- Top stats -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-label">Total Requests</div>
      <div class="stat-value blue" id="s-total">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Allowed</div>
      <div class="stat-value green" id="s-allowed">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Denied (429)</div>
      <div class="stat-value red" id="s-denied">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Throttle Rate</div>
      <div class="stat-value" id="s-throttle">—</div>
    </div>
  </div>

  <!-- Per-algorithm cards -->
  <div class="algo-grid">
    <div class="algo-card fw">
      <div class="algo-name">Fixed Window</div>
      <div class="algo-metrics" id="m-fixed_window"></div>
    </div>
    <div class="algo-card sw">
      <div class="algo-name">Sliding Window</div>
      <div class="algo-metrics" id="m-sliding_window"></div>
    </div>
    <div class="algo-card tb">
      <div class="algo-name">Token Bucket</div>
      <div class="algo-metrics" id="m-token_bucket"></div>
    </div>
    <div class="algo-card lb">
      <div class="algo-name">Leaky Bucket</div>
      <div class="algo-metrics" id="m-leaky_bucket"></div>
    </div>
  </div>

  <!-- Charts -->
  <div class="charts-row">
    <div class="chart-card">
      <div class="chart-title">Allowed vs Denied — rolling window (last 60 polls)</div>
      <div class="chart-wrap"><canvas id="lineChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Throttle rate % by algorithm</div>
      <div class="chart-wrap"><canvas id="barChart"></canvas></div>
    </div>
  </div>
</main>

<footer>Polling /api/stats every 2s &nbsp;·&nbsp; Rate Limiter v0.1.0</footer>

<script>
  const ALGORITHMS = ['fixed_window', 'sliding_window', 'token_bucket', 'leaky_bucket'];
  const ALGO_LABELS = {
    fixed_window:   'Fixed Window',
    sliding_window: 'Sliding Window',
    token_bucket:   'Token Bucket',
    leaky_bucket:   'Leaky Bucket',
  };
  const ALGO_COLORS = {
    fixed_window:   '#3b82f6',
    sliding_window: '#22c55e',
    token_bucket:   '#f59e0b',
    leaky_bucket:   '#a855f7',
  };
  const MAX_POINTS = 60;

  // Rolling history for line chart
  const history = { labels: [], allowed: [], denied: [] };
  let prevTotal = { allowed: 0, denied: 0 };

  // ── Line chart ───────────────────────────────────────────────────────────────
  const lineCtx = document.getElementById('lineChart').getContext('2d');
  const lineChart = new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Allowed',
          data: [],
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: 'Denied',
          data: [],
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      plugins: { legend: { labels: { color: '#94a3b8', font: { size: 11 } } } },
      scales: {
        x: {
          ticks: { color: '#475569', maxTicksLimit: 8, font: { size: 10 } },
          grid:  { color: '#1e2130' },
        },
        y: {
          ticks: { color: '#475569', font: { size: 10 } },
          grid:  { color: '#1e2130' },
          beginAtZero: true,
        },
      },
    },
  });

  // ── Bar chart ────────────────────────────────────────────────────────────────
  const barCtx = document.getElementById('barChart').getContext('2d');
  const barChart = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: ALGORITHMS.map(a => ALGO_LABELS[a]),
      datasets: [{
        label: 'Throttle %',
        data: [0, 0, 0, 0],
        backgroundColor: ALGORITHMS.map(a => ALGO_COLORS[a] + 'cc'),
        borderColor:     ALGORITHMS.map(a => ALGO_COLORS[a]),
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: '#475569', font: { size: 10 } },
          grid:  { color: '#1e2130' },
        },
        y: {
          min: 0,
          max: 100,
          ticks: {
            color: '#475569',
            font: { size: 10 },
            callback: v => v + '%',
          },
          grid: { color: '#1e2130' },
        },
      },
    },
  });

  // ── Render algo card ──────────────────────────────────────────────────────────
  function renderAlgoCard(algo, data) {
    const el = document.getElementById('m-' + algo);
    if (!el) return;
    const pct = data.throttle_rate;
    el.innerHTML = `
      <div class="metric-row">
        <span class="label">Allowed</span>
        <span class="val green">${data.allowed.toLocaleString()}</span>
      </div>
      <div class="metric-row">
        <span class="label">Denied</span>
        <span class="val red">${data.denied.toLocaleString()}</span>
      </div>
      <div class="metric-row">
        <span class="label">p99 latency</span>
        <span class="val muted">${data.p99_ms}ms</span>
      </div>
      <div class="throttle-bar">
        <div class="throttle-fill" style="width:${Math.min(100, pct)}%"></div>
      </div>
      <div class="metric-row" style="margin-top:4px">
        <span class="label">Throttle rate</span>
        <span class="val" style="color:${pct > 50 ? '#ef4444' : pct > 20 ? '#f59e0b' : '#22c55e'}">${pct}%</span>
      </div>
    `;
  }

  // ── Poll /api/stats ───────────────────────────────────────────────────────────
  async function poll() {
    try {
      const res  = await fetch('/api/stats');
      const data = await res.json();

      // Top stats
      const total    = data.total_requests;
      const allowed  = data.total_allowed;
      const denied   = data.total_denied;
      const throttle = total > 0 ? (denied / total * 100).toFixed(1) : '0.0';

      document.getElementById('s-total').textContent   = total.toLocaleString();
      document.getElementById('s-allowed').textContent = allowed.toLocaleString();
      document.getElementById('s-denied').textContent  = denied.toLocaleString();
      const tEl = document.getElementById('s-throttle');
      tEl.textContent = throttle + '%';
      tEl.style.color = parseFloat(throttle) > 50 ? '#ef4444'
                      : parseFloat(throttle) > 20 ? '#f59e0b'
                      : '#22c55e';

      // Algorithm cards
      for (const algo of ALGORITHMS) {
        if (data.algorithms[algo]) renderAlgoCard(algo, data.algorithms[algo]);
      }

      // Line chart: delta since last poll
      const now = new Date().toLocaleTimeString('en', { hour12: false });
      const deltaAllowed = allowed - prevTotal.allowed;
      const deltaDenied  = denied  - prevTotal.denied;
      prevTotal = { allowed, denied };

      history.labels.push(now);
      history.allowed.push(deltaAllowed);
      history.denied.push(deltaDenied);
      if (history.labels.length > MAX_POINTS) {
        history.labels.shift();
        history.allowed.shift();
        history.denied.shift();
      }
      lineChart.data.labels            = [...history.labels];
      lineChart.data.datasets[0].data  = [...history.allowed];
      lineChart.data.datasets[1].data  = [...history.denied];
      lineChart.update('none');

      // Bar chart
      barChart.data.datasets[0].data = ALGORITHMS.map(a =>
        data.algorithms[a]?.throttle_rate ?? 0
      );
      barChart.update('none');

      // Status dot
      document.getElementById('dot').style.background = '#22c55e';
      document.getElementById('last-update').textContent =
        'Last update: ' + now;

    } catch (e) {
      document.getElementById('dot').style.background = '#ef4444';
      document.getElementById('last-update').textContent = 'Connection lost';
    }
  }

  poll();
  setInterval(poll, 2000);
</script>
</body>
</html>
"""


async def dashboard_route():
    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=HTML)
