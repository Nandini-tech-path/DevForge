import { useEffect, useState, type ChangeEvent } from 'react'
import './App.css'
import { AnalysisSummary } from './components/AnalysisSummary'
import { CodeEditor } from './components/CodeEditor'
import { FindingList } from './components/FindingList'
import { FixViewer } from './components/FixViewer'
import { analyzeCode, generateFix, getHealth, rescanCode } from './services/api'
import type { AnalysisResult, Finding, FixResult, HealthResponse, Language, RescanResult } from './types/analysis'

const EXAMPLE = `import os\n\nAPI_KEY = "sk-live-demo-secret"\n\ndef get_user(conn, user_id):\n    query = "SELECT * FROM users WHERE id = " + user_id\n    return conn.execute(query)\n\ndef run_backup(target_dir):\n    os.system("tar -cf backup.tar " + target_dir)\n`

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [language, setLanguage] = useState<Language>('python')
  const [fileName, setFileName] = useState('snippet.py')
  const [sourceCode, setSourceCode] = useState('')
  const [originalCode, setOriginalCode] = useState('')
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
  const [fix, setFix] = useState<FixResult | null>(null)
  const [rescan, setRescan] = useState<RescanResult | null>(null)
  const [busy, setBusy] = useState<'analyze' | 'fix' | 'rescan' | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealthError(true))
  }, [])

  const loadExample = () => {
    setSourceCode(EXAMPLE)
    setOriginalCode('')
    setFileName('vulnerable_sample.py')
    setLanguage('python')
    setAnalysis(null)
    setSelectedFinding(null)
    setFix(null)
    setRescan(null)
    setError(null)
  }

  const clear = () => {
    setSourceCode('')
    setOriginalCode('')
    setAnalysis(null)
    setSelectedFinding(null)
    setFix(null)
    setRescan(null)
    setError(null)
  }

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const extension = file.name.split('.').pop()?.toLowerCase()
    const mapping: Record<string, Language> = {
      py: 'python',
      js: 'javascript',
      jsx: 'javascript',
      java: 'java',
      c: 'c',
      cpp: 'cpp',
      cc: 'cpp',
      h: 'c',
    }
    const mappedLanguage = mapping[extension ?? '']
    if (!mappedLanguage) {
      setError('Unsupported file type. Upload a Python, JavaScript, Java, C, or C++ source file.')
      return
    }
    setFileName(file.name)
    setLanguage(mappedLanguage)
    setSourceCode(await file.text())
    setAnalysis(null)
    setSelectedFinding(null)
    setFix(null)
    setRescan(null)
    setError(null)
  }

  const analyze = async () => {
    if (!sourceCode.trim()) {
      setError('Enter or upload source code before analyzing.')
      return
    }
    setBusy('analyze')
    setError(null)
    setFix(null)
    setRescan(null)
    try {
      const result = await analyzeCode(language, fileName, sourceCode)
      setAnalysis(result)
      setOriginalCode(sourceCode)
      setSelectedFinding(result.issues[0] ?? null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Analysis failed.')
    } finally {
      setBusy(null)
    }
  }

  const createFix = async () => {
    if (!analysis || !selectedFinding) return
    setBusy('fix')
    setError(null)
    try {
      setFix(await generateFix(analysis.reviewId, selectedFinding, language, sourceCode))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Fix generation failed.')
    } finally {
      setBusy(null)
    }
  }

  const applyFix = () => {
    if (!fix) return
    setSourceCode(fix.fixedCode)
    setFix(null)
    setRescan(null)
  }

  const rescanFixed = async () => {
    if (!analysis) return
    setBusy('rescan')
    setError(null)
    try {
      const result = await rescanCode(analysis.reviewId, language, sourceCode)
      setRescan(result)
      setAnalysis(result.current)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Re-scan failed.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-wrap">
          <div className="brand-mark" aria-hidden="true">◈</div>
          <div>
            <p className="eyebrow">AI CODE SECURITY</p>
            <h1>CodeSentinel <span>AI</span></h1>
          </div>
        </div>

        <div className={`status-pill ${health ? 'online' : 'offline'}`}>
          <span className="status-dot" />
          {health ? 'System Ready' : healthError ? 'Backend Offline' : 'Connecting...'}
        </div>
      </header>

      <main className="workspace-shell">
        <section className="hero-panel">
          <div className="hero-copy">
            <span className="eyebrow accent">AI CODE SECURITY</span>
            <h2>Secure Your Code with AI</h2>
            <p>CodeSentinel detects vulnerabilities, bugs, and maintainability issues before they reach production.</p>
          </div>
          <div className="hero-stats">
            <div>
              <strong>Static + AI</strong>
              <span>Hybrid review</span>
            </div>
            <div>
              <strong>Live Scan</strong>
              <span>Analyze in seconds</span>
            </div>
          </div>
        </section>

        <section className="workspace-card">
          <div className="toolbar">
            <div className="toolbar-left">
              <label className="field-label">
                <span>Language</span>
                <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="c">C</option>
                  <option value="cpp">C++</option>
                </select>
              </label>

              <button className="secondary-button" onClick={loadExample}>Load Example</button>

              <label className="upload-button">
                <span>Upload</span>
                <input type="file" accept=".py,.js,.jsx,.java,.c,.cc,.cpp,.h" onChange={upload} />
              </label>

              <button className="secondary-button" onClick={clear}>Clear</button>
            </div>

            <button className="primary-button" onClick={analyze} disabled={busy !== null}>
              {busy === 'analyze' ? 'Analyzing...' : 'Analyze Code'}
            </button>
          </div>

          <CodeEditor
            code={sourceCode}
            fileName={fileName}
            language={language}
            selectedLine={selectedFinding?.line ?? null}
            onChange={setSourceCode}
          />
        </section>

        {error && <div className="error-banner" role="alert">{error}</div>}

        {!analysis && !error && (
          <section className="empty-state">
            <div className="empty-copy">
              <p className="eyebrow">READY TO ANALYZE</p>
              <h3>Review your code for issues before deployment.</h3>
            </div>
            <button className="primary-button" onClick={loadExample}>Load vulnerable example</button>
          </section>
        )}

        {analysis && (
          <>
            <AnalysisSummary result={analysis} />

            <div className="results-grid">
              <section className="panel-card">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">FINDINGS</p>
                    <h3>Review results</h3>
                  </div>
                  <span className="muted-text">{analysis.issues.length} total</span>
                </div>

                <FindingList
                  findings={analysis.issues}
                  selected={selectedFinding}
                  onSelect={(finding) => {
                    setSelectedFinding(finding)
                    setFix(null)
                  }}
                />
              </section>

              <aside className="panel-card details-panel">
                {selectedFinding ? (
                  <>
                    <p className="eyebrow">FINDING DETAILS</p>
                    <h3>{selectedFinding.type}</h3>
                    <div className={`detail-severity ${selectedFinding.severity.toLowerCase()}`}>
                      {selectedFinding.severity} · {Math.round(selectedFinding.confidence * 100)}% confidence
                    </div>

                    <dl className="detail-list">
                      <div>
                        <dt>Location</dt>
                        <dd>{selectedFinding.line ? `Line ${selectedFinding.line}` : 'File-level'}</dd>
                      </div>
                      <div>
                        <dt>Evidence</dt>
                        <dd><code>{selectedFinding.evidence}</code></dd>
                      </div>
                      <div>
                        <dt>Explanation</dt>
                        <dd>{selectedFinding.explanation}</dd>
                      </div>
                      <div>
                        <dt>Why it matters</dt>
                        <dd>{selectedFinding.message}</dd>
                      </div>
                      <div>
                        <dt>Suggested improvement</dt>
                        <dd>{selectedFinding.suggestion}</dd>
                      </div>
                      <div>
                        <dt>Source</dt>
                        <dd>{selectedFinding.source}</dd>
                      </div>
                    </dl>

                    <button className="primary-button full-width" onClick={createFix} disabled={busy !== null}>
                      {busy === 'fix' ? 'Generating...' : 'Generate Secure Fix'}
                    </button>
                  </>
                ) : (
                  <p className="empty-copy small">Select a finding to inspect its evidence and remediation.</p>
                )}
              </aside>
            </div>
          </>
        )}

        {fix && <FixViewer fix={fix} onApply={applyFix} onReject={() => setFix(null)} />}

        {analysis && originalCode !== sourceCode && !fix && (
          <section className="rescan-bar">
            <div>
              <p className="eyebrow">CODE MODIFIED</p>
              <strong>Verify the fix with a fresh re-scan.</strong>
            </div>
            <button className="primary-button" onClick={rescanFixed} disabled={busy !== null}>
              {busy === 'rescan' ? 'Re-scanning...' : 'Re-scan Code'}
            </button>
          </section>
        )}

        {rescan && (
          <section className="panel-card rescan-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">RE-SCAN COMPLETE</p>
                <h3>Verification results</h3>
              </div>
              <span className="muted-text">{rescan.previous.issues.length} → {rescan.current.issues.length} findings</span>
            </div>

            <div className="rescan-stats">
              <div>
                <strong>{rescan.resolved.length}</strong>
                <span>Resolved</span>
              </div>
              <div>
                <strong>{rescan.remaining.length}</strong>
                <span>Remaining</span>
              </div>
              <div>
                <strong>{rescan.newIssues.length}</strong>
                <span>New issues</span>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
