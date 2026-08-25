using System.Text;
using System.Text.Json.Nodes;

namespace Dicode.ConfigChecker.Core;

public static class ConfigRenamer
{
    public static string Rename(string raw, string name)
    {
        if (raw.StartsWith("vmess://", StringComparison.OrdinalIgnoreCase))
        {
            try
            {
                var payload = raw[8..].Replace('-', '+').Replace('_', '/');
                payload += new string('=', (4 - payload.Length % 4) % 4);
                var json = JsonNode.Parse(Encoding.UTF8.GetString(Convert.FromBase64String(payload)))?.AsObject();
                if (json is not null)
                {
                    json["ps"] = name;
                    return "vmess://" + Convert.ToBase64String(Encoding.UTF8.GetBytes(json.ToJsonString())).TrimEnd('=');
                }
            }
            catch { }
        }
        var clean = raw.Split('#')[0];
        return $"{clean}#{Uri.EscapeDataString(name)}";
    }
}
