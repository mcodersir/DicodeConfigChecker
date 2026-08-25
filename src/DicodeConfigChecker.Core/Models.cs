using System.Text.Json.Nodes;

namespace Dicode.ConfigChecker.Core;

public enum RuntimeKind { Xray, SingBox, Direct }

public sealed record Candidate(
    string Raw,
    string Source,
    string Protocol,
    string Host,
    int Port,
    RuntimeKind Runtime,
    JsonObject? Outbound,
    bool IsTelegramProxy = false);

public sealed record DelayResult(
    Candidate Candidate,
    bool IsAlive,
    int? MedianMs,
    int? MinimumMs,
    int? AverageMs,
    int Attempts,
    int Successes,
    string Tester,
    string Error);

public sealed record TestOptions(
    Uri TestUrl,
    int Attempts = 2,
    int MinimumSuccesses = 1,
    int PageSize = 32,
    int Parallelism = 16,
    TimeSpan? RequestTimeout = null,
    TimeSpan? StartupTimeout = null)
{
    public TimeSpan EffectiveRequestTimeout => RequestTimeout ?? TimeSpan.FromSeconds(8);
    public TimeSpan EffectiveStartupTimeout => StartupTimeout ?? TimeSpan.FromSeconds(6);
}

public sealed record ProgressInfo(int Completed, int Total, string Message);

public sealed record RunSummary(
    DateTimeOffset GeneratedAt,
    TimeSpan Elapsed,
    IReadOnlyList<DelayResult> Results,
    string CoreVersion,
    string AppVersion = "2.0.0");
