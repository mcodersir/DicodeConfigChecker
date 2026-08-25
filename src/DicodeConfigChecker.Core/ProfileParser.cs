using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Dicode.ConfigChecker.Core;

public static class ProfileParser
{
    public static Candidate? Parse(string raw, string source = "manual")
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        raw = raw.Trim();
        try
        {
            if (raw.StartsWith("vmess://", StringComparison.OrdinalIgnoreCase)) return ParseVmess(raw, source);
            if (raw.StartsWith("vless://", StringComparison.OrdinalIgnoreCase)) return ParseUrl(raw, source, "vless", RuntimeKind.Xray);
            if (raw.StartsWith("trojan://", StringComparison.OrdinalIgnoreCase)) return ParseUrl(raw, source, "trojan", RuntimeKind.Xray);
            if (raw.StartsWith("ss://", StringComparison.OrdinalIgnoreCase)) return ParseShadowsocks(raw, source);
            if (raw.StartsWith("hysteria2://", StringComparison.OrdinalIgnoreCase) || raw.StartsWith("hy2://", StringComparison.OrdinalIgnoreCase))
                return ParseUrl(raw, source, "hysteria2", RuntimeKind.SingBox);
            if (raw.StartsWith("tuic://", StringComparison.OrdinalIgnoreCase)) return ParseUrl(raw, source, "tuic", RuntimeKind.SingBox);
            if (raw.StartsWith("tg://proxy?", StringComparison.OrdinalIgnoreCase) || raw.StartsWith("tg://socks?", StringComparison.OrdinalIgnoreCase)
                || raw.StartsWith("https://t.me/proxy?", StringComparison.OrdinalIgnoreCase) || raw.StartsWith("https://t.me/socks?", StringComparison.OrdinalIgnoreCase))
                return ParseTelegram(raw, source);
        }
        catch { }
        return null;
    }

    private static Candidate? ParseVmess(string raw, string source)
    {
        var json = JsonNode.Parse(DecodeBase64(raw[8..]))?.AsObject();
        if (json is null) return null;
        var host = Text(json, "add", "address", "server", "host");
        var port = Number(json, "port", 443);
        var id = Text(json, "id");
        if (!Valid(host, port) || string.IsNullOrWhiteSpace(id)) return null;
        var user = new JsonObject
        {
            ["id"] = id,
            ["alterId"] = Number(json, "aid", 0),
            ["security"] = Text(json, "scy", "security") is { Length: > 0 } security ? security : "auto"
        };
        var outbound = new JsonObject
        {
            ["protocol"] = "vmess",
            ["settings"] = new JsonObject { ["vnext"] = new JsonArray(new JsonObject { ["address"] = host, ["port"] = port, ["users"] = new JsonArray(user) }) },
            ["streamSettings"] = StreamSettings(
                Text(json, "net", "type") is { Length: > 0 } network ? network : "tcp",
                Text(json, "tls", "security"), Text(json, "host"), Text(json, "path"),
                Text(json, "sni", "peer"), Text(json, "fp"), Text(json, "alpn"), "", "", "")
        };
        return new(raw, source, "vmess", host, port, RuntimeKind.Xray, outbound);
    }

    private static Candidate? ParseUrl(string raw, string source, string protocol, RuntimeKind runtime)
    {
        var uri = new Uri(raw);
        var query = Query(uri.Query);
        var host = uri.Host;
        var port = uri.IsDefaultPort ? 443 : uri.Port;
        var credential = Uri.UnescapeDataString(uri.UserInfo.Split(':')[0]);
        if (!Valid(host, port) || string.IsNullOrWhiteSpace(credential)) return null;

        JsonObject outbound;
        if (runtime == RuntimeKind.Xray)
        {
            if (protocol == "vless")
            {
                var user = new JsonObject { ["id"] = credential, ["encryption"] = Get(query, "encryption", "none") };
                Put(user, "flow", Get(query, "flow"));
                outbound = new JsonObject { ["protocol"] = "vless", ["settings"] = new JsonObject { ["vnext"] = new JsonArray(new JsonObject { ["address"] = host, ["port"] = port, ["users"] = new JsonArray(user) }) } };
            }
            else
            {
                outbound = new JsonObject { ["protocol"] = "trojan", ["settings"] = new JsonObject { ["servers"] = new JsonArray(new JsonObject { ["address"] = host, ["port"] = port, ["password"] = credential }) } };
            }
            outbound["streamSettings"] = StreamSettings(Get(query, "type", Get(query, "net", "tcp")), Get(query, "security"), Get(query, "host"), Get(query, "path", Get(query, "serviceName")), Get(query, "sni", Get(query, "peer")), Get(query, "fp"), Get(query, "alpn"), Get(query, "pbk"), Get(query, "sid"), Get(query, "spx"));
        }
        else
        {
            outbound = protocol == "tuic"
                ? new JsonObject { ["type"] = "tuic", ["server"] = host, ["server_port"] = port, ["uuid"] = credential, ["password"] = Uri.UnescapeDataString(uri.UserInfo.Contains(':') ? uri.UserInfo[(uri.UserInfo.IndexOf(':') + 1)..] : ""), ["congestion_control"] = Get(query, "congestion_control", "bbr") }
                : new JsonObject { ["type"] = "hysteria2", ["server"] = host, ["server_port"] = port, ["password"] = Uri.UnescapeDataString(uri.UserInfo), ["up_mbps"] = 100, ["down_mbps"] = 100 };
            var tls = new JsonObject { ["enabled"] = true };
            Put(tls, "server_name", Get(query, "sni"));
            tls["insecure"] = Get(query, "insecure") is "1" or "true";
            outbound["tls"] = tls;
        }
        return new(raw, source, protocol, host, port, runtime, outbound);
    }

    private static Candidate? ParseShadowsocks(string raw, string source)
    {
        var body = raw[5..].Split('#', '?')[0];
        var decoded = Uri.UnescapeDataString(body);
        if (!decoded.Contains('@')) decoded = DecodeBase64(decoded);
        var at = decoded.LastIndexOf('@');
        var colon = decoded.LastIndexOf(':');
        if (at < 1 || colon <= at) return null;
        var user = decoded[..at];
        var split = user.IndexOf(':');
        if (split < 1 || !int.TryParse(decoded[(colon + 1)..], out var port)) return null;
        var host = decoded[(at + 1)..colon].Trim('[', ']');
        if (!Valid(host, port)) return null;
        var outbound = new JsonObject { ["protocol"] = "shadowsocks", ["settings"] = new JsonObject { ["servers"] = new JsonArray(new JsonObject { ["address"] = host, ["port"] = port, ["method"] = user[..split], ["password"] = user[(split + 1)..] }) } };
        return new(raw, source, "ss", host, port, RuntimeKind.Xray, outbound);
    }

    private static Candidate? ParseTelegram(string raw, string source)
    {
        var uri = new Uri(raw.Replace("tg://", "https://telegram.local/", StringComparison.OrdinalIgnoreCase));
        var q = Query(uri.Query);
        var host = Get(q, "server");
        if (!int.TryParse(Get(q, "port"), out var port) || !Valid(host, port)) return null;
        var socks = raw.Contains("socks", StringComparison.OrdinalIgnoreCase);
        return new(raw, source, socks ? "telegram-socks" : "telegram-mtproto", host, port, RuntimeKind.Direct, null, true);
    }

    private static JsonObject StreamSettings(string network, string security, string host, string path, string sni, string fingerprint, string alpn, string publicKey, string shortId, string spiderX)
    {
        network = network.Equals("splithttp", StringComparison.OrdinalIgnoreCase) ? "xhttp" : network.ToLowerInvariant();
        var stream = new JsonObject { ["network"] = network };
        if (!string.IsNullOrWhiteSpace(security) && security != "none")
        {
            stream["security"] = security;
            var securityNode = new JsonObject();
            Put(securityNode, "serverName", sni); Put(securityNode, "fingerprint", fingerprint);
            if (!string.IsNullOrWhiteSpace(alpn)) securityNode["alpn"] = new JsonArray(alpn.Split(',').Select(x => JsonValue.Create(x.Trim())).ToArray());
            if (security == "reality") { Put(securityNode, "publicKey", publicKey); Put(securityNode, "shortId", shortId); Put(securityNode, "spiderX", spiderX); stream["realitySettings"] = securityNode; }
            else stream["tlsSettings"] = securityNode;
        }
        switch (network)
        {
            case "ws": stream["wsSettings"] = Transport(host, path, true); break;
            case "grpc": stream["grpcSettings"] = new JsonObject { ["serviceName"] = path }; break;
            case "xhttp": stream["xhttpSettings"] = Transport(host, path, false); break;
            case "httpupgrade": stream["httpupgradeSettings"] = Transport(host, path, false); break;
            case "http": stream["httpSettings"] = new JsonObject { ["host"] = new JsonArray(host), ["path"] = path }; break;
        }
        return stream;
    }

    private static JsonObject Transport(string host, string path, bool headers)
    {
        var node = new JsonObject(); Put(node, "path", path);
        if (!string.IsNullOrWhiteSpace(host)) { if (headers) node["headers"] = new JsonObject { ["Host"] = host }; else node["host"] = host; }
        return node;
    }

    private static Dictionary<string, string> Query(string query) => query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries)
        .Select(x => x.Split('=', 2)).GroupBy(x => Uri.UnescapeDataString(x[0]), StringComparer.OrdinalIgnoreCase)
        .ToDictionary(x => x.Key, x => Uri.UnescapeDataString(x.First().Length > 1 ? x.First()[1] : ""), StringComparer.OrdinalIgnoreCase);
    private static string Get(Dictionary<string, string> q, string key, string fallback = "") => q.TryGetValue(key, out var value) && value.Length > 0 ? value : fallback;
    private static string Text(JsonObject o, params string[] keys) { foreach (var key in keys) if (o[key] is JsonNode n && n.ToString().Length > 0) return n.ToString(); return ""; }
    private static int Number(JsonObject o, string key, int fallback) => int.TryParse(o[key]?.ToString(), out var value) ? value : fallback;
    private static bool Valid(string host, int port) => !string.IsNullOrWhiteSpace(host) && port is > 0 and <= 65535;
    private static void Put(JsonObject target, string key, string value) { if (!string.IsNullOrWhiteSpace(value)) target[key] = value; }
    private static string DecodeBase64(string value)
    {
        value = value.Replace('-', '+').Replace('_', '/');
        value += new string('=', (4 - value.Length % 4) % 4);
        return Encoding.UTF8.GetString(Convert.FromBase64String(value));
    }
}
