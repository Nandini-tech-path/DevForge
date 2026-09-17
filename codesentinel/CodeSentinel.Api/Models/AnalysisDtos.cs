namespace CodeSentinel.Api.Models;

public sealed record AnalyzeRequest(string Language, string FileName, string Code);

public sealed record AnalysisSummary(int Critical, int High, int Medium, int Low, int Info);

public sealed record FindingDto(
    string Id,
    string Category,
    string Type,
    string Severity,
    double Confidence,
    int? Line,
    int? EndLine,
    string Message,
    string Explanation,
    string Evidence,
    string Suggestion,
    string? FixedCode,
    string Source,
    string Status);

public sealed record AnalyzeResponse(
    string ReviewId,
    string Language,
    string FileName,
    AnalysisSummary Summary,
    IReadOnlyList<FindingDto> Issues);

public sealed record FixRequest(string ReviewId, string FindingId, string Language, string Code);

public sealed record FixResponse(
    string ReviewId,
    string FindingId,
    string OriginalCode,
    string FixedCode,
    string Why);

public sealed record RescanRequest(string ReviewId, string Language, string Code);

public sealed record RescanResponse(
    string ReviewId,
    AnalyzeResponse Previous,
    AnalyzeResponse Current,
    IReadOnlyList<FindingDto> Resolved,
    IReadOnlyList<FindingDto> Remaining,
    IReadOnlyList<FindingDto> NewIssues);