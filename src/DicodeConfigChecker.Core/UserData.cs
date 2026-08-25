using System.Text.Json;

namespace Dicode.ConfigChecker.Core;

public static class UserData
{
    public static string Root
    {
        get
        {
            var overridden = Environment.GetEnvironmentVariable("DICODE_DATA_DIR");
            if (!string.IsNullOrWhiteSpace(overridden)) return Ensure(overridden);
            var basePath = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (OperatingSystem.IsLinux()) basePath = Environment.GetEnvironmentVariable("XDG_CONFIG_HOME") ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".config");
            if (OperatingSystem.IsMacOS()) basePath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Library", "Application Support");
            return Ensure(Path.Combine(basePath, "DicodeConfigChecker"));
        }
    }

    public static string OutputDirectory => Ensure(Path.Combine(Root, "outputs"));
    public static string SettingsFile => Path.Combine(Root, "settings.json");
    public static string ChannelsFile => Path.Combine(Root, "channels.txt");

    public static AppSettings LoadSettings()
    {
        try { return JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(SettingsFile)) ?? new(); }
        catch { return new(); }
    }

    public static void SaveSettings(AppSettings value) => File.WriteAllText(SettingsFile, JsonSerializer.Serialize(value, new JsonSerializerOptions { WriteIndented = true }));
    private static string Ensure(string path) { Directory.CreateDirectory(path); return path; }
}
