import type { AnalysisResult, FixResult, Finding, HealthResponse, Language, RescanResult } from '../types/analysis'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:5197'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...init?.headers }, ...init })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function getHealth() { return request<HealthResponse>('/api/health') }

export function analyzeCode(language: Language, fileName: string, code: string) {
  return request<AnalysisResult>('/api/analyze', { method: 'POST', body: JSON.stringify({ language, fileName, code }) })
}

export function generateFix(reviewId: string, finding: Finding, language: Language, code: string) {
  return request<FixResult>('/api/fix', { method: 'POST', body: JSON.stringify({ reviewId, findingId: finding.id, language, code }) })
}

export function rescanCode(reviewId: string, language: Language, code: string) {
  return request<RescanResult>('/api/rescan', { method: 'POST', body: JSON.stringify({ reviewId, language, code }) })
}

export function getReport(reviewId: string) { return request<AnalysisResult>(`/api/report/${reviewId}`) }
