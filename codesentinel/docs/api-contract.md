# API Contract

Phase 1 exposes `GET /api/health`. The planned typed endpoints are:

- `POST /api/analyze`
- `POST /api/fix`
- `POST /api/rescan`
- `GET /api/report/{id}`
- `GET /api/health`

`AnalyzeRequest` and `AnalyzeResponse` define the initial C# DTO boundary for
the later analyzer and AI integration.