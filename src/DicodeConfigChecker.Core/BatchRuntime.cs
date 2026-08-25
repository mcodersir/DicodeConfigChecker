using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Dicode.ConfigChecker.Core;

internal sealed class BatchRuntime : IAsyncDisposable
{
    private readonly Process _process;
    private readonly string _configPath;
    public IReadOnlyDictionary<Candidate, int> Ports { get; }

    private BatchRuntime(Process process, string configPath, IReadOnlyDictionary<Candidate, int> ports)
    {
        _process = process; _configPath = configPath; Ports = ports;
    }

    public static async Task<BatchRuntime> StartAsync(RuntimeKind kind, string executable, IReadOnlyList<Candidate> candidates, TimeSpan timeout, CancellationToken cancellationToken)
    {
        var ports = candidates.ToDictionary(x => x, _ => FreePort());
        var config = kind == RuntimeKind.Xray ? XrayConfig(candidates, ports) : SingBoxConfig(candidates, ports);
        var configPath = Path.Combine(Path.GetTempPath(), $"dicode-check-{Guid.NewGuid():N}.json");
        await File.WriteAllTextAsync(configPath, config.ToJsonString(new JsonSerializerOptions { WriteIndented = false }), cancellationToken);
        var arguments = kind == RuntimeKind.Xray ? $"run -config \"{configPath}\"" : $"run -c \"{configPath}\"";
        var process = Process.Start(new ProcessStartInfo(executable, arguments)
        {
            UseShellExecute = false, CreateNoWindow = true, RedirectStandardError = false, RedirectStandardOutput = false,
            WorkingDirectory = Path.GetDirectoryName(executable) ?? AppContext.BaseDirectory
        }) ?? throw new InvalidOperationException("Runtime process could not be started.");
        var session = new BatchRuntime(process, configPath, ports);
        try
        {
            using var startup = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            startup.CancelAfter(timeout);
            await Task.WhenAll(ports.Values.Select(port => WaitForPortAsync(port, process, startup.Token)));
            return session;
        }
        catch
        {
            await session.DisposeAsync();
            throw;
        }
    }

    private static JsonObject XrayConfig(IReadOnlyList<Candidate> candidates, IReadOnlyDictionary<Candidate, int> ports)
    {
        var inbounds = new JsonArray(); var outbounds = new JsonArray(); var rules = new JsonArray();
        for (var i = 0; i < candidates.Count; i++)
        {
            var inboundTag = $"in-{i}"; var outboundTag = $"out-{i}";
            inbounds.Add(new JsonObject { ["tag"] = inboundTag, ["listen"] = "127.0.0.1", ["port"] = ports[candidates[i]], ["protocol"] = "socks", ["settings"] = new JsonObject { ["auth"] = "noauth", ["udp"] = true } });
            var outbound = candidates[i].Outbound!.DeepClone().AsObject(); outbound["tag"] = outboundTag; outbounds.Add(outbound);
            rules.Add(new JsonObject { ["type"] = "field", ["inboundTag"] = new JsonArray(inboundTag), ["outboundTag"] = outboundTag });
        }
        outbounds.Add(new JsonObject { ["tag"] = "direct", ["protocol"] = "freedom" });
        return new JsonObject { ["log"] = new JsonObject { ["loglevel"] = "warning" }, ["inbounds"] = inbounds, ["outbounds"] = outbounds, ["routing"] = new JsonObject { ["domainStrategy"] = "IPIfNonMatch", ["rules"] = rules } };
    }

    private static JsonObject SingBoxConfig(IReadOnlyList<Candidate> candidates, IReadOnlyDictionary<Candidate, int> ports)
    {
        var inbounds = new JsonArray(); var outbounds = new JsonArray(); var rules = new JsonArray();
        for (var i = 0; i < candidates.Count; i++)
        {
            var inboundTag = $"in-{i}"; var outboundTag = $"out-{i}";
            inbounds.Add(new JsonObject { ["type"] = "mixed", ["tag"] = inboundTag, ["listen"] = "127.0.0.1", ["listen_port"] = ports[candidates[i]] });
            var outbound = candidates[i].Outbound!.DeepClone().AsObject(); outbound["tag"] = outboundTag; outbounds.Add(outbound);
            rules.Add(new JsonObject { ["inbound"] = new JsonArray(inboundTag), ["action"] = "route", ["outbound"] = outboundTag });
        }
        outbounds.Add(new JsonObject { ["type"] = "direct", ["tag"] = "direct" });
        return new JsonObject { ["log"] = new JsonObject { ["level"] = "warn", ["timestamp"] = false }, ["inbounds"] = inbounds, ["outbounds"] = outbounds, ["route"] = new JsonObject { ["rules"] = rules, ["final"] = "direct" } };
    }

    private static int FreePort()
    {
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port; listener.Stop(); return port;
    }

    private static async Task WaitForPortAsync(int port, Process process, CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            if (process.HasExited) throw new InvalidOperationException($"Runtime exited with code {process.ExitCode}.");
            try { using var socket = new TcpClient(); await socket.ConnectAsync(IPAddress.Loopback, port, cancellationToken); return; }
            catch (SocketException) { await Task.Delay(40, cancellationToken); }
        }
        cancellationToken.ThrowIfCancellationRequested();
    }

    public async ValueTask DisposeAsync()
    {
        try
        {
            if (!_process.HasExited) { _process.Kill(true); await _process.WaitForExitAsync(); }
        }
        catch { }
        _process.Dispose();
        try { File.Delete(_configPath); } catch { }
    }
}
