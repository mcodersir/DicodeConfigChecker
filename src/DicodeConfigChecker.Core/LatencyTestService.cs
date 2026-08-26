using System.Diagnostics;
using System.Net;
using System.Net.Sockets;

namespace Dicode.ConfigChecker.Core;

public sealed class LatencyTestService(RuntimeLocator runtimes)
{
    public async Task<IReadOnlyList<DelayResult>> TestAsync(IEnumerable<Candidate> input, TestOptions options, IProgress<ProgressInfo>? progress = null, CancellationToken cancellationToken = default)
    {
        var candidates = input.DistinctBy(x => x.Protocol == "vmess" ? x.Raw : x.Raw.Split('#')[0], StringComparer.OrdinalIgnoreCase).ToList();
        var output = new List<DelayResult>(candidates.Count);
        var completed = 0;

        // Direct (Telegram) candidates — TCP test, no runtime needed.
        var directCandidates = candidates.Where(x => x.Runtime == RuntimeKind.Direct).ToArray();
        if (directCandidates.Length > 0)
        {
            using var directGate = new SemaphoreSlim(Math.Clamp(options.Parallelism, 1, 128));
            var direct = await Task.WhenAll(directCandidates.Select(async item =>
            {
                await directGate.WaitAsync(cancellationToken);
                try { return await TcpTestAsync(item, options, cancellationToken); }
                finally { directGate.Release(); }
            }));
            output.AddRange(direct);
            completed += direct.Length;
            progress?.Report(new(completed, candidates.Count, $"تست مستقیم {completed} از {candidates.Count}"));
        }

        // Runtime-backed candidates — one process per RuntimeKind with ALL candidates.
        foreach (var group in candidates.Where(x => x.Runtime != RuntimeKind.Direct).GroupBy(x => x.Runtime))
        {
            var executable = runtimes.Find(group.Key);
            if (executable is null)
            {
                foreach (var item in group) output.Add(Failed(item, $"{group.Key} runtime is not installed"));
                completed += group.Count();
                progress?.Report(new(completed, candidates.Count, $"{group.Key} runtime missing"));
                continue;
            }

            var runtimeCandidates = group.ToArray();
            BatchRuntime? session = null;
            try
            {
                session = await BatchRuntime.StartAsync(group.Key, executable, runtimeCandidates, options.EffectiveStartupTimeout, cancellationToken);
            }
            catch (Exception ex)
            {
                foreach (var item in runtimeCandidates) output.Add(Failed(item, ex.Message));
                completed += runtimeCandidates.Length;
                progress?.Report(new(completed, candidates.Count, $"{group.Key} startup failed"));
                continue;
            }

            // Test all candidates for this runtime concurrently.
            using var gate = new SemaphoreSlim(Math.Clamp(options.Parallelism, 1, 128));
            var pageResults = await Task.WhenAll(runtimeCandidates.Select(async candidate =>
            {
                await gate.WaitAsync(cancellationToken);
                try { return await RealHttpTestAsync(candidate, session.Ports[candidate], options, cancellationToken); }
                finally { gate.Release(); }
            }));
            output.AddRange(pageResults);
            completed += runtimeCandidates.Length;
            progress?.Report(new(completed, candidates.Count, $"تست واقعی {completed} از {candidates.Count}"));

            // Retry only failed candidates once.
            var failed = pageResults.Where(x => !x.IsAlive).Select(x => x.Candidate).ToArray();
            if (failed.Length > 0)
            {
                try
                {
                    using var retryGate = new SemaphoreSlim(Math.Clamp(options.Parallelism, 1, 128));
                    var retries = await Task.WhenAll(failed.Select(async candidate =>
                    {
                        await retryGate.WaitAsync(cancellationToken);
                        try { return await RealHttpTestAsync(candidate, session.Ports[candidate], options with { Attempts = 1 }, cancellationToken); }
                        finally { retryGate.Release(); }
                    }));
                    var retrySuccesses = new HashSet<Candidate>(retries.Where(x => x.IsAlive).Select(x => x.Candidate));
                    output = output.Select(x => !x.IsAlive && retrySuccesses.Contains(x.Candidate)
                        ? retries.First(r => r.Candidate == x.Candidate && r.IsAlive)
                        : x).ToList();
                }
                catch { }
            }

            await session.DisposeAsync();
            session = null;
        }

        return output.OrderBy(x => !x.IsAlive).ThenBy(x => x.MedianMs ?? int.MaxValue).ToList();
    }

    private async Task<DelayResult> RealHttpTestAsync(Candidate candidate, int socksPort, TestOptions options, CancellationToken cancellationToken)
    {
        var samples = new List<int>(); string error = "request failed";
        using var handler = new SocketsHttpHandler
        {
            Proxy = new WebProxy($"socks5://127.0.0.1:{socksPort}"),
            UseProxy = true,
            ConnectTimeout = options.EffectiveRequestTimeout,
            PooledConnectionLifetime = TimeSpan.Zero,
            ConnectCallback = async (context, token) =>
            {
                // Happy Eyeballs: resolve both IPv4 and IPv6, race connections.
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(token);
                cts.CancelAfter(context.InitialRequestTimeout);
                var hosts = await Dns.GetHostAddressesAsync(context.DnsEndPoint.Host, cts.Token).ConfigureAwait(false);
                if (hosts.Length == 0)
                    throw new SocketException((int)SocketError.HostNotFound);

                // Prefer IPv4 first, then IPv6 — simple Happy Eyeballs ordering.
                var ordered = hosts.OrderBy(h => h.AddressFamily == AddressFamily.InterNetwork ? 0 : 1).ToArray();
                Socket? winner = null;
                Exception? lastError = null;
                foreach (var addr in ordered)
                {
                    try
                    {
                        var s = new Socket(addr.AddressFamily, SocketType.Stream, ProtocolType.Tcp) { NoDelay = true };
                        await s.ConnectAsync(addr, context.DnsEndPoint.Port, cts.Token).ConfigureAwait(false);
                        winner = s;
                        break;
                    }
                    catch (Exception ex) { lastError = ex; }
                }
                if (winner is null) throw lastError ?? new SocketException((int)SocketError.ConnectionRefused);
                return (Stream)new NetworkStream(winner, ownsSocket: true);
            }
        };
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
