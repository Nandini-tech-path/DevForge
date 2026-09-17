import type { FixResult } from '../types/analysis'

export function FixViewer({ fix, onApply, onReject }: { fix: FixResult; onApply: () => void; onReject: () => void }) {
  return (
    <section className="fix-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">SECURE FIX</p>
          <h3>Suggested improvement</h3>
        </div>

        <div className="fix-actions">
          <button onClick={onReject}>Reject</button>
          <button className="primary-button" onClick={onApply}>Apply Fix</button>
        </div>
      </div>

      <div className="diff-grid">
        <div className="diff-block">
          <span>Original Code</span>
          <pre>{fix.originalCode}</pre>
        </div>

        <div className="diff-block">
          <span>Secure Fix</span>
          <pre>{fix.fixedCode}</pre>
        </div>
      </div>

      <p className="why-fix"><b>Why this fix works:</b> {fix.why}</p>
    </section>
  )
}
