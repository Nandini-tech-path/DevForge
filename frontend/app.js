const els = {
  filename: document.getElementById("filename"),
  fileInput: document.getElementById("fileInput"),
  codeInput: document.getElementById("codeInput"),
  runBtn: document.getElementById("runBtn"),
  exampleBtn: document.getElementById("exampleBtn"),
  charCount: document.getElementById("charCount"),
  engineStatus: document.getElementById("engineStatus"),
  emptyState: document.getElementById("emptyState"),
  resultsRoot: document.getElementById("resultsRoot"),
  riskScore: document.getElementById("riskScore"),
  severityCounts: document.getElementById("severityCounts"),
  verdict: document.getElementById("verdict"),
  metricsRow: document.getElementById("metricsRow"),
  filterGroup: document.getElementById("filterGroup"),
  issueList: document.getElementById("issueList"),
  downloadJson: document.getElementById("downloadJson"),
  downloadMd: document.getElementById("downloadMd"),
};

const SEVERITIES = ["critical", "high", "medium", "low", "info"];
let lastReport = null;
let activeFilter = "all";

const EXAMPLE_CODE = `import os
import pickle
import hashlib

API_KEY = "sk-live-9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c"

def load_user_prefs(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def run_backup(target_dir):
    os.system("tar -cvf backup.tar " + target_dir)

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def get_user(conn, user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return conn.execute(query)

def process(items=[]):
    for i in items:
        try:
            items.append(i * 2)
        except:
            pass
    return items
`;

els.codeInput.addEventListener("input", () => {
  els.charCount.textContent = `${els.codeInput.value.length} chars`;
});

els.exampleBtn.addEventListener("click", () => {
  els.codeInput.value = EXAMPLE_CODE;
  els.filename.value = "vulnerable_sample.py";
  els.codeInput.dispatchEvent(new Event("input"));
});

els.fileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  els.codeInput.value = text;
  els.filename.value = file.name;
  els.codeInput.dispatchEvent(new Event("input"));
});

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.llm_available) {
      els.engineStatus.textContent = `engine online · ${data.model}`;
      els.engineStatus.className = "engine-status ok";
    } else {
      els.engineStatus.textContent = "static-only mode (no API key set)";
      els.engineStatus.className = "engine-status warn";
    }
  } catch {
    els.engineStatus.textContent = "engine unreachable";
    els.engineStatus.className = "engine-status warn";
  }
}
checkHealth();

els.runBtn.addEventListener("click", runReview);

async function runReview() {
  const code = els.codeInput.value;
  if (!code.trim()) return;

  els.runBtn.disabled = true;
  els.runBtn.textContent = "Reviewing…";

  try {
    const res = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, filename: els.filename.value || "snippet.txt" }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    lastReport = await res.json();
    activeFilter = "all";
    renderReport(lastReport);
  } catch (e) {
    alert(`Review failed: ${e.message}`);
  } finally {
    els.runBtn.disabled = false;
    els.runBtn.textContent = "Run review";
  }
}

function renderReport(report) {
  els.emptyState.classList.add("hidden");
  els.resultsRoot.classList.remove("hidden");

  els.riskScore.textContent = report.summary.risk_score;
  els.verdict.textContent = report.summary.verdict;

  els.severityCounts.innerHTML = SEVERITIES.map((sev) => {
    const count = report.summary.by_severity[sev] || 0;
    return `<span class="sev-pill"><span class="sev-dot" style="background:var(--${sevVar(sev)})"></span>${sev} ${count}</span>`;
  }).join("");

  const m = report.metrics;
  const metricItems = [
    ["LOC", m.lines_of_code],
    ["Comment ratio", `${(m.comment_ratio * 100).toFixed(1)}%`],
    ["Functions", m.function_count],
    ["Longest fn (lines)", m.longest_function_lines],
    ["Cyclomatic cx.", m.approx_cyclomatic_complexity],
    ["Max nesting", m.max_nesting_depth],
  ];
  els.metricsRow.innerHTML = metricItems
    .map(([label, value]) => `<div class="metric-card"><div class="metric-value">${value}</div><div class="metric-label">${label}</div></div>`)
    .join("");

  els.filterGroup.innerHTML = ["all", ...SEVERITIES]
    .map((f) => `<button class="filter-chip ${f === activeFilter ? "active" : ""}" data-filter="${f}">${f}</button>`)
    .join("");
  els.filterGroup.querySelectorAll(".filter-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeFilter = btn.dataset.filter;
      renderIssues(report);
      els.filterGroup.querySelectorAll(".filter-chip").forEach((b) => b.classList.toggle("active", b === btn));
    });
  });

  renderIssues(report);
}

function renderIssues(report) {
  const issues = report.issues.filter((i) => activeFilter === "all" || i.severity === activeFilter);

  if (issues.length === 0) {
    els.issueList.innerHTML = `<p style="color:var(--text-dim);font-size:13px;">No issues in this filter. ✅</p>`;
    return;
  }

  els.issueList.innerHTML = issues
    .map((issue) => `
      <div class="issue-card sev-${issue.severity}">
        <div class="issue-top">
          <span class="issue-badge sev-${issue.severity}">${issue.severity}</span>
          <span class="issue-title">${escapeHtml(issue.title)}</span>
          <span class="issue-meta">${issue.category} · ${issue.source} · ${issue.id}${issue.line ? ` · line ${issue.line}` : ""}</span>
        </div>
        <div class="issue-body">
          <span class="label">Why it matters</span>
          ${escapeHtml(issue.description)}
          <span class="label">Suggested fix</span>
          ${escapeHtml(issue.suggestion)}
          ${issue.line_snippet ? `<div class="issue-snippet">${escapeHtml(issue.line_snippet)}</div>` : ""}
        </div>
      </div>
    `)
    .join("");
}

function sevVar(sev) {
  return { critical: "crit", high: "high", medium: "med", low: "low", info: "info" }[sev];
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

els.downloadJson.addEventListener("click", () => {
  if (!lastReport) return;
  downloadBlob(JSON.stringify(lastReport, null, 2), `${lastReport.filename}.review.json`, "application/json");
});

els.downloadMd.addEventListener("click", async () => {
  if (!lastReport) return;
  const res = await fetch("/api/review/markdown", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: els.codeInput.value, filename: els.filename.value }),
  });
  const text = await res.text();
  downloadBlob(text, `${lastReport.filename}.review.md`, "text/markdown");
});

function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
