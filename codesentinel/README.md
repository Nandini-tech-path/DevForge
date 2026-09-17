# CodeSentinel AI

Phase 1 establishes a production-oriented boundary around the existing review
prototype:

- `CodeSentinel.Api`: ASP.NET Core Web API on .NET 9
- `frontend`: React + TypeScript + Vite dashboard
- `analyzer`: isolated static-analysis module boundary
- `ai-agent`: isolated Azure OpenAI integration boundary
- `docs`: API contract and architecture notes

Run the API with `dotnet run --project CodeSentinel.Api` and the frontend with
`npm run dev --prefix frontend` from this directory.