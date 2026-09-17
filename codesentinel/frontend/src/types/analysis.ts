export type Language = 'python' | 'javascript' | 'java' | 'c' | 'cpp'
export type Severity = 'Critical' | 'High' | 'Medium' | 'Low' | 'Info'

export interface Finding {
  id: string
  category: string
  type: string
  severity: Severity
  confidence: number
  line: number | null
  endLine: number | null
  message: string
  explanation: string
  evidence: string
  suggestion: string
  fixedCode: string | null
  source: string
  status: string
}

export interface AnalysisSummary {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

export interface AnalysisResult {
  reviewId: string
  language: Language
  fileName: string
  summary: AnalysisSummary
  issues: Finding[]
}

export interface FixResult {
  reviewId: string
  findingId: string
  originalCode: string
  fixedCode: string
  why: string
}

export interface RescanResult {
  reviewId: string
  previous: AnalysisResult
  current: AnalysisResult
  resolved: Finding[]
  remaining: Finding[]
  newIssues: Finding[]
}

export interface HealthResponse {
  status: string
  service: string
  timestamp: string
}
