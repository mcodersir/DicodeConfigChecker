using System.Text;
using System.Text.Json;

namespace Dicode.ConfigChecker.Core;

public static class ReportWriter
{
    public static async Task<IReadOnlyList<string>> WriteAsync(string directory, RunSummary summary, OutputOptions? options = null, CancellationToken cancellationToken = default)
    {
        options ??= new OutputOptions();
        Directory.CreateDirectory(directory);
        var alive = summary.Results.Where(x => x.IsAlive).ToList();
        var configs = options.IncludeConfigs
            ? alive.Where(x => !x.Candidate.IsTelegramProxy).Select((x, i) => options.RenameConfigs ? ConfigRenamer.Rename(x.Candidate.Raw, $"{options.NamePrefix}-{i + 1}") : x.Candidate.Raw).ToArray()
            : [];
        var proxies = options.IncludeTelegramProxies ? alive.Where(x => x.Candidate.IsTelegramProxy).Select(x => x.Candidate.Raw).ToArray() : [];
        var configReport = BuildReadable(summary.Results.Where(x => !x.Candidate.IsTelegramProxy));
        var proxyReport = BuildReadable(summary.Results.Where(x => x.Candidate.IsTelegramProxy));
        var files = new Dictionary<string, string>
        {
            ["sub.txt"] = string.Join(Environment.NewLine, configs),
            ["proxy.txt"] = string.Join(Environment.NewLine, proxies),
            ["sub_base64.txt"] = Convert.ToBase64String(Encoding.UTF8.GetBytes(string.Join('\n', configs))),
            ["proxy_base64.txt"] = Convert.ToBase64String(Encoding.UTF8.GetBytes(string.Join('\n', proxies))),
            ["alive_report.txt"] = configReport,
            ["proxy_report.txt"] = proxyReport,
            ["report.json"] = JsonSerializer.Serialize(summary, new JsonSerializerOptions { WriteIndented = true })
        };
        foreach (var file in files) await File.WriteAllTextAsync(Path.Combine(directory, file.Key), file.Value, new UTF8Encoding(false), cancellationToken);
        return files.Keys.Select(x => Path.Combine(directory, x)).ToArray();
    }

    private static string BuildReadable(IEnumerable<DelayResult> results) => string.Join(Environment.NewLine,
        results.Select(x => $"{(x.IsAlive ? "OK" : "FAIL")} | {x.Candidate.Protocol} | {x.Candidate.Host}:{x.Candidate.Port} | median={x.MedianMs?.ToString() ?? "-"}ms | success={x.Successes}/{x.Attempts} | {x.Tester} | {x.Candidate.Source}"));
}
