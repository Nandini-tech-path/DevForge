import type { AnalysisResult } from '../types/analysis'

export function AnalysisSummary({ result }: { result: AnalysisResult }) {
  const items = [['Critical', result.summary.critical], ['High', result.summary.high], ['Medium', result.summary.medium], ['Low', result.summary.low]]
  return <section className="summary-panel"><div><p className="eyebrow">ANALYSIS COMPLETE</p><h2>{result.summary.critical + result.summary.high + result.summary.medium + result.summary.low + result.summary.info} findings</h2><p className="muted">{result.fileName} · {result.language}</p></div><div className="severity-grid">{items.map(([label, count]) => <div className={`severity-count ${String(label).toLowerCase()}`} key={label}><strong>{count}</strong><span>{label}</span></div>)}</div></section>
}
