using System.Collections.Concurrent;
using System.Net;
using System.Text.RegularExpressions;

namespace Dicode.ConfigChecker.Core;

public sealed partial class ChannelCollector(HttpClient? client = null)
{
    private readonly HttpClient _client = client ?? CreateClient();

    public async Task<IReadOnlyList<Candidate>> CollectAsync(IEnumerable<string> channels, int perChannelLimit, int parallelism, IProgress<ProgressInfo>? progress = null, CancellationToken cancellationToken = default)
        => await CollectRankedAsync([], channels, new CollectOptions(perChannelLimit, perChannelLimit, parallelism), progress, cancellationToken);

    public async Task<IReadOnlyList<Candidate>> CollectRankedAsync(IEnumerable<string> priorityOne, IEnumerable<string> priorityTwo, CollectOptions options, IProgress<ProgressInfo>? progress = null, CancellationToken cancellationToken = default)
    {
        var ranked = priorityOne.Select(x => (Channel: NormalizeChannel(x), Limit: options.PriorityOneLimit, Rank: 1))
            .Concat(priorityTwo.Select(x => (Channel: NormalizeChannel(x), Limit: options.PriorityTwoLimit, Rank: 2)))
            .Where(x => x.Channel is not null)
            .GroupBy(x => x.Channel!, StringComparer.OrdinalIgnoreCase)
            .Select(x => x.OrderBy(y => y.Rank).First())
            .ToArray();
        var found = new ConcurrentDictionary<string, Candidate>(StringComparer.OrdinalIgnoreCase);
        var completed = 0;
        await Parallel.ForEachAsync(ranked, new ParallelOptions { MaxDegreeOfParallelism = Math.Clamp(options.Parallelism, 1, 64), CancellationToken = cancellationToken }, async (entry, token) =>
        {
            var count = 0;
            try
            {
                var html = await FetchPreviewAsync(entry.Channel!, token);
                foreach (Match match in ProfileRegex().Matches(WebUtility.HtmlDecode(html).Replace("\\u0026", "&")))
                {
                    var raw = match.Value.TrimEnd(')', ']', '}', '"', '\'', '>', '،', ',', '.', ';');
                    var candidate = ProfileParser.Parse(raw, entry.Channel!);
                    if (candidate is null) continue;
                    var key = candidate.Protocol == "vmess" ? candidate.Raw : candidate.Raw.Split('#')[0];
                    if (found.TryAdd(key, candidate) && ++count >= Math.Clamp(entry.Limit, 1, 1000)) break;
                }
            }
            catch { }
            var done = Interlocked.Increment(ref completed);
            progress?.Report(new(done, ranked.Length, $"رتبه {entry.Rank} • @{entry.Channel}  +{count}"));
        });
        return found.Values.ToList();
    }

    private async Task<string> FetchPreviewAsync(string channel, CancellationToken cancellationToken)
    {
        Exception? first = null;
        foreach (var host in new[] { "t.me", "telegram.me" })
        {
            try
            {
                var body = await _client.GetStringAsync($"https://{host}/s/{channel}", cancellationToken);
                if (body.Contains("tgme_widget_message", StringComparison.OrdinalIgnoreCase) || ProfileRegex().IsMatch(body)) return body;
            }
            catch (Exception ex) { first ??= ex; }
        }
        throw first ?? new HttpRequestException("Preview page was empty.");
    }

    public static string? NormalizeChannel(string value)
    {
        value = value.Trim();
        if (value.Contains("/+", StringComparison.OrdinalIgnoreCase)) return null;
        value = Regex.Replace(value, "^https?://", "", RegexOptions.IgnoreCase);
        value = Regex.Replace(value, "^(?:t|telegram)\\.me/(?:s/)?", "", RegexOptions.IgnoreCase).Split('/', '?')[0];
        return Regex.IsMatch(value, "^[A-Za-z0-9_]{4,}$") ? value : null;
    }

    private static HttpClient CreateClient()
    {
        var client = new HttpClient { Timeout = TimeSpan.FromSeconds(15) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 DicodeConfigChecker/2.0");
        client.DefaultRequestHeaders.AcceptLanguage.ParseAdd("fa,en-US;q=0.8,en;q=0.7");
        return client;
    }

    [GeneratedRegex("(?:vmess|vless|trojan|ss|hysteria2|hy2|tuic)://[^\\s<>\\\"'`]+|(?:tg://(?:proxy|socks)|https://t\\.me/(?:proxy|socks))\\?[^\\s<>\\\"'`]+", RegexOptions.IgnoreCase)]
    private static partial Regex ProfileRegex();
}
