namespace CodeSentinel.Api.Models;

public sealed record HealthResponse(string Status, string Service, DateTimeOffset Timestamp);