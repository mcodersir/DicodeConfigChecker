using System.Diagnostics;
using System.Net;
using System.Net.Sockets;

namespace Dicode.ConfigChecker.Core;

public sealed class LatencyTestService(RuntimeLocator runtimes)
{
    public async Task<IReadOnlyList<DelayResult>> TestAsync(IEnumerable<Candidate> input, TestOptions options, IProgress<ProgressInfo>? progress = null, CancellationToken cancellationToken = default)
    {
        var candidates = input.DistinctBy(x => x.Protocol == "vmess" ? x.Raw : x.Raw.Split('#')[0], StringComparer.OrdinalIgnoreCase).ToList();
        var output = new List<DelayResult>(candidates.Count); var completed = 0;
        foreach (var group in candidates.GroupBy(x => x.Runtime))
        {
            if (group.Key == RuntimeKind.Direct)
            {
                using var directGate = new SemaphoreSlim(Math.Clamp(options.Parallelism, 1, 128));
                var direct = await Task.WhenAll(group.Select(async item =>
                {
                    await directGate.WaitAsync(cancellationToken);
                    try { return await TcpTestAsync(item, options, cancellationToken); }
                    finally { directGate.Release(); }
                }));
                output.AddRange(direct); completed += direct.Length; progress?.Report(new(completed, candidates.Count, $"{completed}/{candidates.Count}"));
                continue;
            }
            var executable = runtimes.Find(group.Key);
            if (executable is null)
            {
                foreach (var item in group) output.Add(Failed(item, $"{group.Key} runtime is not installed"));
                completed += group.Count(); progress?.Report(new(completed, candidates.Count, $"{group.Key} runtime missing")); continue;
            }
            foreach (var page in group.Chunk(Math.Clamp(options.PageSize, 1, 128)))
            {
                cancellationToken.ThrowIfCancellationRequested();
                IReadOnlyList<DelayResult> pageResults;
                try { pageResults = await TestPageAsync(group.Key, executable, page, options, cancellationToken); }
                catch (Exception ex) { pageResults = page.Select(x => Failed(x, ex.Message)).ToList(); }

                var failed = pageResults.Where(x => !x.IsAlive).Select(x => x.Candidate).ToArray();
                if (failed.Length > 0)
                {
                    try
                    {
                        var retries = await TestPageAsync(group.Key, executable, failed, options with { Attempts = 1 }, cancellationToken);
                        pageResults = pageResults.Select(first => retries.FirstOrDefault(x => x.Candidate == first.Candidate && x.IsAlive) ?? first).ToList();
                    }
                    catch { }
                }
                output.AddRange(pageResults); completed += page.Length;
                progress?.Report(new(completed, candidates.Count, $"تست واقعی {completed} از {candidates.Count}"));
            }
        }
        return output.OrderBy(x => !x.IsAlive).ThenBy(x => x.MedianMs ?? int.MaxValue).ToList();
    }

    private static async Task<IReadOnlyList<DelayResult>> TestPageAsync(RuntimeKind kind, string executable, IReadOnlyList<Candidate> page, TestOptions options, CancellationToken cancellationToken)
    {
        await using var session = await BatchRuntime.StartAsync(kind, executable, page, options.EffectiveStartupTimeout, cancellationToken);
        using var gate = new SemaphoreSlim(Math.Clamp(options.Parallelism, 1, 128));
        return await Task.WhenAll(page.Select(async candidate =>
        {
            await gate.WaitAsync(cancellationToken);
            try { return await RealHttpTestAsync(candidate, session.Ports[candidate], options, cancellationToken); }
            finally { gate.Release(); }
        }));
    }

    private static async Task<DelayResult> RealHttpTestAsync(Candidate candidate, int socksPort, TestOptions options, CancellationToken cancellationToken)
    {
        var samples = new List<int>(); string error = "request failed";
        using var handler = new SocketsHttpHandler { Proxy = new WebProxy($"socks5://127.0.0.1:{socksPort}"), UseProxy = true, ConnectTimeout = options.EffectiveRequestTimeout, PooledConnectionLifetime = TimeSpan.Zero };
        using var client = new HttpClient(handler) { Timeout = options.EffectiveRequestTimeout };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("DicodeConfigChecker/2.0");
        for (var attempt = 0; attempt < Math.Clamp(options.Attempts, 1, 5); attempt++)
        {
            var watch = Stopwatch.StartNew();
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Get, options.TestUrl);
                using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
                watch.Stop();
                if ((int)response.StatusCode is >= 200 and < 500) samples.Add((int)Math.Max(1, watch.ElapsedMilliseconds)); else error = $"HTTP {(int)response.StatusCode}";
            }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException) { error = ex.GetType().Name; }
        }
        return Result(candidate, samples, options, $"{kindName(candidate.Runtime)}-http", error);
    }

    private static async Task<DelayResult> TcpTestAsync(Candidate candidate, TestOptions options, CancellationToken cancellationToken)
    {
        var samples = new List<int>(); string error = "unreachable";
        for (var attempt = 0; attempt < Math.Clamp(options.Attempts, 1, 5); attempt++)
        {
            var watch = Stopwatch.StartNew();
            try
            {
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken); timeout.CancelAfter(options.EffectiveRequestTimeout);
                using var socket = new TcpClient(); await socket.ConnectAsync(candidate.Host, candidate.Port, timeout.Token); watch.Stop(); samples.Add((int)Math.Max(1, watch.ElapsedMilliseconds));
            }
            catch (Exception ex) { error = ex.GetType().Name; }
        }
        return Result(candidate, samples, options, "telegram-tcp", error);
    }

    private static DelayResult Result(Candidate candidate, List<int> samples, TestOptions options, string tester, string error)
    {
        samples.Sort(); var ok = samples.Count >= Math.Clamp(options.MinimumSuccesses, 1, options.Attempts);
        return new(candidate, ok, ok ? samples[samples.Count / 2] : null, ok ? samples[0] : null, ok ? (int)samples.Average() : null, options.Attempts, samples.Count, tester, ok ? "" : error);
    }
    private static DelayResult Failed(Candidate item, string error) => new(item, false, null, null, null, 0, 0, item.Runtime.ToString().ToLowerInvariant(), error);
    private static string kindName(RuntimeKind kind) => kind == RuntimeKind.Xray ? "core-a" : "core-b";
}
