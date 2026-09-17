import type { Finding } from '../types/analysis'

export function FindingList({ findings, selected, onSelect }: { findings: Finding[]; selected: Finding | null; onSelect: (finding: Finding) => void }) {
  return <div className="finding-list">{findings.length === 0 ? <p className="muted">No findings returned.</p> : findings.map((finding) => <button className={`finding-row ${selected?.id === finding.id ? 'selected' : ''}`} key={`${finding.id}-${finding.line}`} onClick={() => onSelect(finding)}><span className={`severity-dot ${finding.severity.toLowerCase()}`} /><span className="finding-main"><strong>{finding.type}</strong><small>{finding.category} · {finding.line ? `Line ${finding.line}` : 'File-level'}</small></span><span className="finding-severity">{finding.severity}</span></button>)}</div>
}
