using Dicode.ConfigChecker.Core;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Windows;

namespace Dicode.ConfigChecker.Desktop;

public partial class MainWindow : Window
{
    private readonly RuntimeLocator _runtimes = new();
    private readonly ObservableCollection<ResultRow> _rows = [];
    private CancellationTokenSource? _run;
    private string OutputDirectory => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "DicodeConfigChecker");

    public MainWindow()
    {
        InitializeComponent(); ResultsGrid.ItemsSource = _rows;
        var channelPath = Path.Combine(AppContext.BaseDirectory, "channels.txt");
        if (File.Exists(channelPath)) ChannelsBox.Text = File.ReadAllText(channelPath);
        Loaded += async (_, _) => await ShowRuntimeStatusAsync();
    }

    private async Task ShowRuntimeStatusAsync()
    {
        var a = await _runtimes.VersionAsync(RuntimeKind.Xray); var b = await _runtimes.VersionAsync(RuntimeKind.SingBox);
        RuntimeStatus.Text = $"Core A: {Short(a)}  •  Core B: {Short(b)}";
    }

    private async void Start_Click(object sender, RoutedEventArgs e)
    {
        if (_run is not null) return;
        if (!Uri.TryCreate(TestUrlBox.Text.Trim(), UriKind.Absolute, out var testUrl)) { MessageBox.Show("آدرس تست معتبر نیست."); return; }
        _run = new CancellationTokenSource(); ToggleRunning(true); _rows.Clear(); AliveText.Text = BestText.Text = "—";
        try
        {
            var channels = ChannelsBox.Text.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            var collectProgress = new Progress<ProgressInfo>(p => UpdateProgress(p, "جمع‌آوری"));
            var candidates = await new ChannelCollector().CollectAsync(channels, 10, Int(WorkersBox.Text, 16), collectProgress, _run.Token);
            StatusText.Text = $"{candidates.Count} مورد یکتا؛ شروع تست واقعی";
            var options = new TestOptions(testUrl, Int(AttemptsBox.Text, 2), 1, Int(PageSizeBox.Text, 32), Int(WorkersBox.Text, 16));
            var started = Stopwatch.StartNew();
            var testProgress = new Progress<ProgressInfo>(p => UpdateProgress(p, "تست"));
            var results = await new LatencyTestService(_runtimes).TestAsync(candidates, options, testProgress, _run.Token);
            started.Stop();
            foreach (var result in results) _rows.Add(ResultRow.From(result));
            var summary = new RunSummary(DateTimeOffset.UtcNow, started.Elapsed, results, RuntimeStatus.Text);
            await ReportWriter.WriteAsync(OutputDirectory, summary, _run.Token);
            AliveText.Text = results.Count(x => x.IsAlive).ToString(); BestText.Text = results.Where(x => x.IsAlive).MinBy(x => x.MedianMs)?.MedianMs?.ToString() ?? "—";
            RunProgress.Value = 100; StatusText.Text = $"تمام شد؛ {results.Count(x => x.IsAlive)} سالم از {results.Count}";
        }
        catch (OperationCanceledException) { StatusText.Text = "عملیات متوقف شد"; }
        catch (Exception ex) { StatusText.Text = "خطا"; MessageBox.Show(ex.Message, "خطا", MessageBoxButton.OK, MessageBoxImage.Error); }
        finally { _run?.Dispose(); _run = null; ToggleRunning(false); }
    }

    private void UpdateProgress(ProgressInfo info, string phase)
    {
        RunProgress.Value = info.Total == 0 ? 0 : info.Completed * 100d / info.Total;
        StatusText.Text = $"{phase}: {info.Message}";
    }
    private void ToggleRunning(bool running) { StartButton.IsEnabled = !running; CancelButton.IsEnabled = running; ChannelsBox.IsReadOnly = running; }
    private void Cancel_Click(object sender, RoutedEventArgs e) => _run?.Cancel();
    private void OpenOutput_Click(object sender, RoutedEventArgs e) { Directory.CreateDirectory(OutputDirectory); Process.Start(new ProcessStartInfo(OutputDirectory) { UseShellExecute = true }); }
    private static int Int(string value, int fallback) => int.TryParse(value, out var result) ? result : fallback;
    private static string Short(string value) => value.Length > 28 ? value[..28] + "…" : value;
}

public sealed record ResultRow(string Status, string Protocol, string Address, string Median, string Minimum, string Success, string Tester)
{
    public static ResultRow From(DelayResult result) => new(result.IsAlive ? "سالم" : "ناموفق", result.Candidate.Protocol.ToUpperInvariant(), $"{result.Candidate.Host}:{result.Candidate.Port}", result.MedianMs?.ToString() ?? "—", result.MinimumMs?.ToString() ?? "—", $"{result.Successes}/{result.Attempts}", result.Tester);
}
