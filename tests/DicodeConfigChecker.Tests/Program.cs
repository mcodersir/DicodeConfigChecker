using Dicode.ConfigChecker.Core;
using System.Text;

var tests = new (string Name, Action Test)[]
{
    ("vless", () => Expect(ProfileParser.Parse("vless://11111111-1111-1111-1111-111111111111@example.com:443?security=tls&type=ws&host=cdn.example.com&path=%2Fws#demo"), "vless", "example.com", 443, RuntimeKind.Xray)),
    ("vmess", () =>
    {
        var payload = Convert.ToBase64String(Encoding.UTF8.GetBytes("{\"v\":\"2\",\"add\":\"node.example.com\",\"port\":\"8443\",\"id\":\"11111111-1111-1111-1111-111111111111\",\"net\":\"ws\",\"tls\":\"tls\"}"));
        Expect(ProfileParser.Parse("vmess://" + payload), "vmess", "node.example.com", 8443, RuntimeKind.Xray);
    }),
    ("shadowsocks", () =>
    {
        var payload = Convert.ToBase64String(Encoding.UTF8.GetBytes("aes-256-gcm:secret@example.net:8388"));
        Expect(ProfileParser.Parse("ss://" + payload), "ss", "example.net", 8388, RuntimeKind.Xray);
    }),
    ("hysteria2", () => Expect(ProfileParser.Parse("hysteria2://secret@hy.example.org:443?sni=hy.example.org"), "hysteria2", "hy.example.org", 443, RuntimeKind.SingBox)),
    ("telegram", () =>
    {
        var item = ProfileParser.Parse("tg://proxy?server=1.1.1.1&port=443&secret=abc") ?? throw new Exception("not parsed");
        if (!item.IsTelegramProxy || item.Port != 443) throw new Exception("wrong telegram profile");
    }),
    ("channel normalization", () =>
    {
        if (ChannelCollector.NormalizeChannel("https://t.me/s/example_channel") != "example_channel") throw new Exception("normalization failed");
        if (ChannelCollector.NormalizeChannel("https://t.me/+private") is not null) throw new Exception("private invite accepted");
    })
};

var failures = 0;
foreach (var (name, test) in tests)
{
    try { test(); Console.WriteLine($"PASS {name}"); }
    catch (Exception ex) { failures++; Console.Error.WriteLine($"FAIL {name}: {ex.Message}"); }
}
return failures == 0 ? 0 : 1;

static void Expect(Candidate? item, string protocol, string host, int port, RuntimeKind runtime)
{
    if (item is null) throw new Exception("not parsed");
    if (item.Protocol != protocol || item.Host != host || item.Port != port || item.Runtime != runtime)
        throw new Exception($"unexpected {item}");
    if (runtime != RuntimeKind.Direct && item.Outbound is null) throw new Exception("outbound missing");
}
