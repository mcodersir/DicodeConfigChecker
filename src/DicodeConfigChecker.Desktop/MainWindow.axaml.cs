using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Platform.Storage;
using Avalonia.Styling;
using Dicode.ConfigChecker.Core;
using System.Diagnostics;

namespace Dicode.ConfigChecker.Desktop;

public partial class MainWindow : Window
{
    private readonly RuntimeLocator _runtimes = new();
    private readonly SubscriptionPublisher _publisher = new();
    private CancellationTokenSource? _operation;
    private IReadOnlyList<Candidate> _collected = [];
    private IReadOnlyList<DelayResult> _results = [];
    private AppSettings _settings = new();

    public MainWindow()
    {
        InitializeComponent();
        LoadState();
        Loaded += async (_, _) => await ShowRuntimeStatusAsync();
        Closing += (_, _) => SaveState();
    }

    private void LoadState()
    {
        _settings = UserData.LoadSettings();
        PriorityOneChannels.Text = _settings.PriorityOneChannels;
        PriorityTwoChannels.Text = string.IsNullOrWhiteSpace(_settings.PriorityTwoChannels) ? LoadBundledChannels() : _settings.PriorityTwoChannels;
        PriorityOneLimit.Value = _settings.PriorityOneLimit; PriorityTwoLimit.Value = _settings.PriorityTwoLimit;
        FetchWorkers.Value = _settings.FetchParallelism; TestWorkers.Value = _settings.TestParallelism;
        PageSize.Value = _settings.PageSize; Attempts.Value = _settings.Attempts; MinimumSuccess.Value = _settings.MinimumSuccesses;
        TestUrl.Text = _settings.TestUrl; CheckConfigs.IsChecked = _settings.CheckConfigs; CheckProxies.IsChecked = _settings.CheckTelegramProxies;
        RenameConfigs.IsChecked = _settings.RenameConfigs; NamePrefix.Text = _settings.NamePrefix;
        GitHubToken.Text = _settings.GitHubToken; SubscriptionRepo.Text = _settings.SubscriptionRepository;
        ThemeBox.SelectedIndex = (int)_settings.Theme; ApplyTheme(_settings.Theme); RefreshSubscriptionUrls(); RefreshOutputs();
    }

    private AppSettings ReadSettings() => new(
        PriorityOneChannels.Text ?? "", PriorityTwoChannels.Text ?? "", Number(PriorityOneLimit, 30), Number(PriorityTwoLimit, 20),
        Number(FetchWorkers, 8), Number(TestWorkers, 16), Number(PageSize, 32), Number(Attempts, 4),
        Math.Min(Number(MinimumSuccess, 3), Number(Attempts, 4)), TestUrl.Text?.Trim() ?? "", CheckConfigs.IsChecked == true,
        CheckProxies.IsChecked == true, RenameConfigs.IsChecked == true, NamePrefix.Text?.Trim() ?? "t.me/dicodeir", true,
        (AppTheme)Math.Clamp(ThemeBox.SelectedIndex, 0, 2), GitHubToken.Text?.Trim() ?? "", SubscriptionRepo.Text?.Trim() ?? "");

    private void SaveState() { _settings = ReadSettings(); UserData.SaveSettings(_settings); File.WriteAllText(UserData.ChannelsFile, string.Join(Environment.NewLine, Lines(_settings.PriorityOneChannels).Concat(Lines(_settings.PriorityTwoChannels)))); }
    private void SaveSettings_Click(object? sender, RoutedEventArgs e) { SaveState(); SetStatus("تنظیمات ذخیره شد."); }

    private async Task ShowRuntimeStatusAsync()
    {
        var first = await _runtimes.VersionAsync(RuntimeKind.Xray); var second = await _runtimes.VersionAsync(RuntimeKind.SingBox);
        RuntimeStatus.Text = $"Core A: {Short(first)}\nCore B: {Short(second)}";
    }

    private async void Collect_Click(object? sender, RoutedEventArgs e)
    {
        if (_operation is not null) return;
        SaveState();
        if (!_settings.CheckConfigs && !_settings.CheckTelegramProxies) { SetStatus("حداقل یکی از خروجی‌های کانفیگ یا پروکسی را فعال کنید."); return; }
        _operation = new(); ToggleBusy(true); _collected = []; _results = []; RefreshMetrics(); DisconnectHint.IsVisible = false; LogBox.Text = "";
        try
        {
            Log("دریافت کانال‌های رتبه اول و دوم شروع شد.");
            var progress = new Progress<ProgressInfo>(p => { RunProgress.Value = Percent(p.Completed, p.Total); SetStatus($"دریافت: {p.Completed} از {p.Total}"); Log(p.Message); });
            var all = await new ChannelCollector().CollectRankedAsync(Lines(_settings.PriorityOneChannels), Lines(_settings.PriorityTwoChannels), new(_settings.PriorityOneLimit, _settings.PriorityTwoLimit, _settings.FetchParallelism), progress, _operation.Token);
            _collected = all.Where(x => x.IsTelegramProxy ? _settings.CheckTelegramProxies : _settings.CheckConfigs).ToArray();
            CollectedMetric.Text = _collected.Count.ToString(); RunProgress.Value = 100; TestButton.IsEnabled = _collected.Count > 0;
            DisconnectHint.IsVisible = _collected.Count > 0; SetStatus($"دریافت تمام شد؛ {_collected.Count} مورد یکتا آمادهٔ تست است.");
        }
        catch (OperationCanceledException) { SetStatus("دریافت متوقف شد؛ داده‌های دریافت‌شدهٔ کامل حفظ شدند."); }
        catch (Exception ex) { SetStatus("خطای دریافت: " + ex.Message); Log("ERROR " + ex); }
        finally { EndOperation(); }
    }

    private async void Test_Click(object? sender, RoutedEventArgs e)
    {
        if (_operation is not null || _collected.Count == 0) return;
        SaveState();
        if (!Uri.TryCreate(_settings.TestUrl, UriKind.Absolute, out var url) || url.Scheme is not ("http" or "https")) { SetStatus("URL تست واقعی معتبر نیست."); return; }
        _operation = new(); ToggleBusy(true); DisconnectHint.IsVisible = false; var complete = new List<DelayResult>(); var total = _collected.Count; var done = 0;
        try
        {
            foreach (var page in _collected.Chunk(Math.Clamp(_settings.PageSize, 1, 128)))
            {
                var pageProgress = new Progress<ProgressInfo>(p => { RunProgress.Value = Percent(done + p.Completed, total); SetStatus($"تست واقعی: {done + p.Completed} از {total}"); });
                var service = new LatencyTestService(_runtimes);
                var result = await service.TestAsync(page, new(url, _settings.Attempts, _settings.MinimumSuccesses, _settings.PageSize, _settings.TestParallelism), pageProgress, _operation.Token);
                complete.AddRange(result); done += page.Length; _results = complete.ToArray(); RefreshMetrics();
            }
            SetStatus($"تست تمام شد؛ {_results.Count(x => x.IsAlive)} سالم از {_results.Count}.");
        }
        catch (OperationCanceledException) { SetStatus($"تست موقتاً متوقف شد؛ {complete.Count} نتیجه حفظ شد. برای ادامه دوباره مرحلهٔ دوم را بزنید."); }
        catch (Exception ex) { SetStatus("خطای تست: " + ex.Message); Log("ERROR " + ex); }
        finally
        {
            if (complete.Count > 0)
            {
                _results = complete.OrderBy(x => !x.IsAlive).ThenBy(x => x.MedianMs ?? int.MaxValue).ToArray();
                await WriteOutputsAsync(); RefreshOutputs();
                if (!string.IsNullOrWhiteSpace(_settings.GitHubToken)) await PublishSubscriptionAsync(false);
            }
            EndOperation();
        }
    }

    private async Task WriteOutputsAsync()
    {
        var summary = new RunSummary(DateTimeOffset.UtcNow, TimeSpan.Zero, _results, RuntimeStatus.Text ?? "");
        await ReportWriter.WriteAsync(UserData.OutputDirectory, summary, new(_settings.CheckConfigs, _settings.CheckTelegramProxies, _settings.RenameConfigs, _settings.NamePrefix));
    }

    private void Stop_Click(object? sender, RoutedEventArgs e) => _operation?.Cancel();
    private void EndOperation() { _operation?.Dispose(); _operation = null; ToggleBusy(false); TestButton.IsEnabled = _collected.Count > 0; }
    private void ToggleBusy(bool busy) { CollectButton.IsEnabled = !busy; TestButton.IsEnabled = !busy && _collected.Count > 0; StopButton.IsEnabled = busy; }

    private async void ConnectSubscription_Click(object? sender, RoutedEventArgs e) => await PublishSubscriptionAsync(true);
    private async void PublishSubscription_Click(object? sender, RoutedEventArgs e) => await PublishSubscriptionAsync(true);
    private async Task PublishSubscriptionAsync(bool manual)
    {
        SaveState();
        if (string.IsNullOrWhiteSpace(_settings.GitHubToken)) { SetStatus("ابتدا Classic PAT با دسترسی public_repo را وارد کنید."); return; }
        try
        {
            SetStatus("در حال انتشار اتمیک ساب GitHub…");
            var info = await _publisher.EnsureAndPublishAsync(_settings.GitHubToken, _settings.SubscriptionRepository, ReadOutput("sub.txt"), ReadOutput("proxy.txt"));
            SubscriptionRepo.Text = info.Reference; _settings = ReadSettings() with { SubscriptionRepository = info.Reference }; UserData.SaveSettings(_settings); RefreshSubscriptionUrls();
            SetStatus(info.Changed ? "sub.txt و proxy.txt منتشر و راستی‌آزمایی شدند." : "محتوا تکراری بود؛ انتشار اضافه انجام نشد.");
        }
        catch (Exception ex) { SetStatus("انتشار در صف تلاش بعدی ماند: " + ex.Message); if (manual) Log("PUBLISH " + ex); }
    }

    private void RefreshSubscriptionUrls()
    {
        var repo = SubscriptionRepo.Text?.Trim() ?? ""; if (!repo.Contains('/')) { SubUrl.Text = ProxyUrl.Text = ""; return; }
        var branch = "main"; SubUrl.Text = $"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/sub.txt"; ProxyUrl.Text = $"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/proxy.txt";
    }

    private void RefreshOutputs()
    {
        ConfigOutput.Text = ReadOutput("sub.txt"); ProxyOutput.Text = ReadOutput("proxy.txt");
        ConfigCount.Text = $"{Lines(ConfigOutput.Text ?? "").Count()} کانفیگ سالم"; ProxyCount.Text = $"{Lines(ProxyOutput.Text ?? "").Count()} پروکسی سالم";
    }

    private void RefreshMetrics()
    {
        CollectedMetric.Text = _collected.Count.ToString(); ConfigMetric.Text = _results.Count(x => x.IsAlive && !x.Candidate.IsTelegramProxy).ToString();
        ProxyMetric.Text = _results.Count(x => x.IsAlive && x.Candidate.IsTelegramProxy).ToString(); FailedMetric.Text = _results.Count(x => !x.IsAlive).ToString();
    }

    private void SaveChannels_Click(object? sender, RoutedEventArgs e)
    {
        PriorityOneChannels.Text = string.Join(Environment.NewLine, Lines(PriorityOneChannels.Text ?? "").Distinct(StringComparer.OrdinalIgnoreCase));
        PriorityTwoChannels.Text = string.Join(Environment.NewLine, Lines(PriorityTwoChannels.Text ?? "").Except(Lines(PriorityOneChannels.Text ?? ""), StringComparer.OrdinalIgnoreCase).Distinct(StringComparer.OrdinalIgnoreCase));
        SaveState(); SetStatus("فهرست کانال‌ها پاک‌سازی و ذخیره شد.");
    }
    private void ResetChannels_Click(object? sender, RoutedEventArgs e) { PriorityTwoChannels.Text = LoadBundledChannels(); SaveChannels_Click(sender, e); }

    private async void CopyConfigs_Click(object? sender, RoutedEventArgs e) => await CopyAsync(ConfigOutput.Text ?? "");
    private async void CopyProxies_Click(object? sender, RoutedEventArgs e) => await CopyAsync(ProxyOutput.Text ?? "");
    private async Task CopyAsync(string text)
    {
        var clipboard = TopLevel.GetTopLevel(this)?.Clipboard;
        if (clipboard is not null && !string.IsNullOrEmpty(text))
        {
            var data = new DataTransfer();
            data.Add(DataTransferItem.Create(DataFormat.Text, text));
            await clipboard.SetDataAsync(data);
        }
        SetStatus("در کلیپ‌بورد کپی شد.");
    }
    private void OpenOutput_Click(object? sender, RoutedEventArgs e) => OpenExternal(UserData.OutputDirectory);

    private void ThemeBox_Changed(object? sender, SelectionChangedEventArgs e) { var theme = (AppTheme)Math.Clamp(ThemeBox.SelectedIndex, 0, 2); ApplyTheme(theme); }
    private static void ApplyTheme(AppTheme theme) { if (Application.Current is not null) Application.Current.RequestedThemeVariant = theme switch { AppTheme.Light => ThemeVariant.Light, AppTheme.Dark => ThemeVariant.Dark, _ => ThemeVariant.Default }; }

    private void Dashboard_Click(object? sender, RoutedEventArgs e) => Show(DashboardPage);
    private void Settings_Click(object? sender, RoutedEventArgs e) => Show(SettingsPage);
    private void Channels_Click(object? sender, RoutedEventArgs e) => Show(ChannelsPage);
    private void Configs_Click(object? sender, RoutedEventArgs e) { RefreshOutputs(); Show(ConfigsPage); }
    private void Proxies_Click(object? sender, RoutedEventArgs e) { RefreshOutputs(); Show(ProxiesPage); }
    private void Show(Control page) { foreach (var item in new Control[] { DashboardPage, SettingsPage, ChannelsPage, ConfigsPage, ProxiesPage }) item.IsVisible = item == page; }

    private void SetStatus(string value) { StatusText.Text = value; Log(value); }
    private void Log(string value) { var line = $"[{DateTime.Now:HH:mm:ss}] {value}"; LogBox.Text = string.IsNullOrEmpty(LogBox.Text) ? line : LogBox.Text + Environment.NewLine + line; LogBox.CaretIndex = LogBox.Text.Length; }
    private static IEnumerable<string> Lines(string value) => value.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries).Select(x => x.Trim()).Where(x => x.Length > 0);
    private static int Number(NumericUpDown input, int fallback) => input.Value is decimal value ? (int)value : fallback;
    private static double Percent(int done, int total) => total == 0 ? 0 : done * 100d / total;
    private static string Short(string value) => value.Length > 32 ? value[..32] + "…" : value;
    private static string ReadOutput(string name) { var path = Path.Combine(UserData.OutputDirectory, name); return File.Exists(path) ? File.ReadAllText(path) : ""; }
    private static string LoadBundledChannels() { var path = Path.Combine(AppContext.BaseDirectory, "channels.txt"); return File.Exists(UserData.ChannelsFile) ? File.ReadAllText(UserData.ChannelsFile) : File.Exists(path) ? File.ReadAllText(path) : ""; }
    private static void OpenExternal(string target)
    {
        try
        {
            if (OperatingSystem.IsWindows()) Process.Start(new ProcessStartInfo(target) { UseShellExecute = true });
            else Process.Start(OperatingSystem.IsMacOS() ? "open" : "xdg-open", target);
        }
        catch { }
    }
}
