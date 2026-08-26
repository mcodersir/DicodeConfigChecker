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
    int Attempts = 3,
    int MinimumSuccesses = 2,
    int PageSize = 32,
    int Parallelism = 32,
    TimeSpan? RequestTimeout = null,
    TimeSpan? StartupTimeout = null)
{
    public TimeSpan EffectiveRequestTimeout => RequestTimeout ?? TimeSpan.FromSeconds(6);
    public TimeSpan EffectiveStartupTimeout => StartupTimeout ?? TimeSpan.FromSeconds(5);
}

public sealed record CollectOptions(
    int PriorityOneLimit = 30,
    int PriorityTwoLimit = 20,
    int Parallelism = 10);

public enum AppTheme { System, Light, Dark }

public sealed record OutputOptions(
    bool IncludeConfigs = true,
    bool IncludeTelegramProxies = true,
    bool RenameConfigs = true,
    string NamePrefix = "t.me/dicodeir");

public sealed record AppSettings(
    string PriorityOneChannels = "t.me/dicodeir\nt.me/persianvpnhub",
    string PriorityTwoChannels = "",
    int PriorityOneLimit = 30,
    int PriorityTwoLimit = 20,
    int FetchParallelism = 10,
    int TestParallelism = 32,
    int PageSize = 32,
    int Attempts = 3,
    int MinimumSuccesses = 2,
    string TestUrl = "https://www.gstatic.com/generate_204",
    bool CheckConfigs = true,
    bool CheckTelegramProxies = true,
    bool RenameConfigs = true,
    string NamePrefix = "t.me/dicodeir",
    bool TcpPrefilter = true,
    AppTheme Theme = AppTheme.System,
    string GitHubToken = "",
    string SubscriptionRepository = "");

public sealed record ProgressInfo(int Completed, int Total, string Message);

public sealed record RunSummary(
    DateTimeOffset GeneratedAt,
    TimeSpan Elapsed,
    IReadOnlyList<DelayResult> Results,
    string CoreVersion,
    string AppVersion = "2.0.0");
