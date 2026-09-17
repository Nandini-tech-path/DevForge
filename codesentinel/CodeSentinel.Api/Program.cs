using CodeSentinel.Api.Models;
using System.Net.Http.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();
builder.Services.AddHttpClient("Analyzer", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["Analyzer:BaseUrl"] ?? "http://127.0.0.1:8000");
    client.Timeout = TimeSpan.FromSeconds(90);
});
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
        policy.WithOrigins(
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174")
            .AllowAnyHeader()
            .AllowAnyMethod());
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseCors();

app.MapGet("/api/health", () =>
{
    return Results.Ok(new HealthResponse("ok", "CodeSentinel API", DateTimeOffset.UtcNow));
})
.WithName("GetHealth")
.WithTags("System");

var reports = new Dictionary<string, AnalyzeResponse>();

var supportedLanguages = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    "python",
    "javascript",
    "java",
    "c",
    "cpp",
    "c++"
};

app.MapPost("/api/analyze", async (AnalyzeRequest request, IHttpClientFactory clients, CancellationToken cancellationToken) =>
{
    if (string.IsNullOrWhiteSpace(request.Code))
        return Results.BadRequest(new { detail = "Enter source code before analyzing." });
    if (!supportedLanguages.Contains(request.Language ?? string.Empty))
        return Results.BadRequest(new { detail = "Only Python, JavaScript, Java, C, and C++ are supported." });

    var client = clients.CreateClient("Analyzer");
    try
    {
        var upstream = await client.PostAsJsonAsync("/api/review", new { code = request.Code, filename = request.FileName }, cancellationToken);
        if (!upstream.IsSuccessStatusCode)
            return Results.Problem("The analysis engine could not review this file.", statusCode: 502);
        var source = await upstream.Content.ReadFromJsonAsync<PythonReport>(cancellationToken: cancellationToken);
        if (source is null) return Results.Problem("The analysis engine returned an empty response.", statusCode: 502);
        var response = MapReport(source, request.Language, request.FileName);
        reports[response.ReviewId] = response;
        return Results.Ok(response);
    }
    catch (HttpRequestException)
    {
        return Results.Problem("The analysis engine is unavailable. Start the analyzer service and try again.", statusCode: 503);
    }
})
.WithName("AnalyzeCode")
.WithTags("Analysis");

app.MapPost("/api/fix", (FixRequest request) =>
{
    if (!reports.TryGetValue(request.ReviewId, out var report))
        return Results.NotFound(new { detail = "Review not found." });
    var finding = report.Issues.FirstOrDefault(issue => issue.Id == request.FindingId);
    if (finding is null) return Results.NotFound(new { detail = "Finding not found." });
    var fixedCode = ApplyKnownFix(request.Code, finding);
    return Results.Ok(new FixResponse(request.ReviewId, finding.Id, request.Code, fixedCode, finding.Suggestion));
})
.WithName("GenerateFix")
.WithTags("Fixes");

app.MapPost("/api/rescan", async (RescanRequest request, IHttpClientFactory clients, CancellationToken cancellationToken) =>
{
    if (!reports.TryGetValue(request.ReviewId, out var previous))
        return Results.NotFound(new { detail = "Review not found." });
    var client = clients.CreateClient("Analyzer");
    var upstream = await client.PostAsJsonAsync("/api/review", new { code = request.Code, filename = "rescan" }, cancellationToken);
    if (!upstream.IsSuccessStatusCode) return Results.Problem("The analysis engine could not rescan this code.", statusCode: 502);
    var source = await upstream.Content.ReadFromJsonAsync<PythonReport>(cancellationToken: cancellationToken);
    if (source is null) return Results.Problem("The analysis engine returned an empty response.", statusCode: 502);
    var current = MapReport(source, request.Language, "rescan");
    reports[current.ReviewId] = current;
    var previousById = previous.Issues.ToDictionary(issue => issue.Id);
    var currentById = current.Issues.ToDictionary(issue => issue.Id);
    var resolved = previous.Issues.Where(issue => !currentById.ContainsKey(issue.Id)).ToArray();
    var remaining = current.Issues.Where(issue => previousById.ContainsKey(issue.Id)).ToArray();
    var newIssues = current.Issues.Where(issue => !previousById.ContainsKey(issue.Id)).ToArray();
    return Results.Ok(new RescanResponse(request.ReviewId, previous, current, resolved, remaining, newIssues));
})
.WithName("RescanCode")
.WithTags("Analysis");

app.MapGet("/api/report/{id}", (string id) => reports.TryGetValue(id, out var report) ? Results.Ok(report) : Results.NotFound())
    .WithName("GetReport")
    .WithTags("Reports");

app.Run();

static AnalyzeResponse MapReport(PythonReport source, string language, string fileName)
{
    var issues = source.Issues.Select(issue => new FindingDto(
        issue.Id, TitleCase(issue.Category), issue.Title, TitleCase(issue.Severity), issue.Confidence,
        issue.Line, issue.Line, issue.Description, issue.Description, issue.LineSnippet ?? "No source excerpt available.",
        issue.Suggestion, null, TitleCase(issue.Source), "Open")).ToArray();
    var counts = issues.GroupBy(issue => issue.Severity).ToDictionary(group => group.Key, group => group.Count());
    var summary = new AnalysisSummary(
        counts.GetValueOrDefault("Critical"), counts.GetValueOrDefault("High"), counts.GetValueOrDefault("Medium"),
        counts.GetValueOrDefault("Low"), counts.GetValueOrDefault("Info"));
    return new AnalyzeResponse(Guid.NewGuid().ToString("N"), language, fileName, summary, issues);
}

static string ApplyKnownFix(string code, FindingDto finding)
{
    var lines = code.Split('\n');
    if (finding.Line is null || finding.Line < 1 || finding.Line > lines.Length) return code;
    var index = finding.Line.Value - 1;
    lines[index] = finding.Id switch
    {
        "PY-SEC-002" => "    subprocess.run([\"tool\", user_input], check=True)",
        "PY-SEC-004" => "    query = \"SELECT * FROM users WHERE id = ?\"  # bind user input separately",
        "PY-SEC-005" => "API_KEY = os.environ.get(\"API_KEY\")",
        "PY-SEC-001" => lines[index].Replace("eval(", "ast.literal_eval(").Replace("exec(", "ast.literal_eval("),
        "JS-SEC-001" => lines[index].Replace("eval(", "JSON.parse("),
        _ => lines[index]
    };
    return string.Join('\n', lines);
}

static string TitleCase(string value) => string.IsNullOrEmpty(value) ? value : char.ToUpperInvariant(value[0]) + value[1..].Replace('_', ' ');

sealed class PythonReport
{
    public List<PythonIssue> Issues { get; set; } = [];
}

sealed class PythonIssue
{
    public string Id { get; set; } = "";
    public string Category { get; set; } = "";
    public string Severity { get; set; } = "";
    public string Title { get; set; } = "";
    public string Description { get; set; } = "";
    public string Suggestion { get; set; } = "";
    public int? Line { get; set; }
    public string? LineSnippet { get; set; }
    public string Source { get; set; } = "";
    public double Confidence { get; set; } = .8;
}
