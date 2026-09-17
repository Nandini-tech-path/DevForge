interface Props {
  code: string
  fileName: string
  language: string
  selectedLine: number | null
  onChange: (code: string) => void
}

export function CodeEditor({ code, fileName, language, selectedLine, onChange }: Props) {
  const lines = code.split('\n')

  const languageLabel: Record<string, string> = {
    python: 'Python',
    javascript: 'JavaScript',
    java: 'Java',
    c: 'C',
    cpp: 'C++',
  }

  return (
    <div className="editor-shell">
      <div className="editor-toolbar">
        <span className="editor-file-name">{fileName}</span>
        <span className="editor-language-badge">{languageLabel[language] ?? 'Code'}</span>
      </div>

      <div className="editor-body">
        <div className="line-numbers" aria-hidden="true">
          {lines.map((_, index) => (
            <span className={selectedLine === index + 1 ? 'active-line' : ''} key={index}>
              {index + 1}
            </span>
          ))}
        </div>

        <textarea
          aria-label="Source code"
          value={code}
          onChange={(event) => onChange(event.target.value)}
          spellCheck={false}
        />
      </div>
    </div>
  )
}
