using System.Diagnostics;
using System.Runtime.InteropServices;

namespace Dicode.ConfigChecker.Core;

public sealed class RuntimeLocator(string? root = null)
{
    private readonly string _root = root ?? Path.Combine(AppContext.BaseDirectory, "runtimes");

    public string? Find(RuntimeKind kind)
    {
        var name = kind == RuntimeKind.Xray ? "core-a" : "core-b";
        var executable = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? $"{name}.exe" : name;
        var candidates = new[]
        {
            Path.Combine(_root, executable),
            Path.Combine(AppContext.BaseDirectory, executable),
            Environment.GetEnvironmentVariable(kind == RuntimeKind.Xray ? "DICODE_CORE_A" : "DICODE_CORE_B")
        };
        return candidates.FirstOrDefault(path => !string.IsNullOrWhiteSpace(path) && File.Exists(path));
    }

    public async Task<string> VersionAsync(RuntimeKind kind, CancellationToken cancellationToken = default)
    {
        var path = Find(kind);
        if (path is null) return "not-installed";
        try
        {
            using var process = Process.Start(new ProcessStartInfo(path, "version") { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true });
            if (process is null) return "unknown";
            var output = await process.StandardOutput.ReadLineAsync(cancellationToken) ?? await process.StandardError.ReadLineAsync(cancellationToken);
            await process.WaitForExitAsync(cancellationToken);
            return string.IsNullOrWhiteSpace(output) ? "unknown" : output.Trim();
        }
        catch { return "unknown"; }
    }
}
