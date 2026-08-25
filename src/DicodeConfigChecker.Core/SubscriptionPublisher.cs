using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Dicode.ConfigChecker.Core;

public sealed record SubscriptionInfo(string Owner, string Repository, string Branch, bool Created, bool Changed)
{
    public string Reference => $"{Owner}/{Repository}";
    public string RawUrl(string file) => $"https://raw.githubusercontent.com/{Owner}/{Repository}/refs/heads/{Branch}/{file}";
}

public sealed class SubscriptionPublisher
{
    public async Task<SubscriptionInfo> EnsureAndPublishAsync(string token, string repositoryReference, string subText, string proxyText, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(token)) throw new ArgumentException("توکن GitHub وارد نشده است.");
        using var client = CreateClient(token);
        var user = await SendAsync(client, HttpMethod.Get, "user", null, cancellationToken);
        var owner = user["login"]?.GetValue<string>() ?? throw new InvalidOperationException("حساب GitHub شناسایی نشد.");
        var created = false;
        var repository = ParseRepository(repositoryReference, owner);
        if (repository is null)
        {
            repository = $"Dicode-{Guid.NewGuid():N}"[..18] + "DIC";
            await SendAsync(client, HttpMethod.Post, "user/repos", new JsonObject { ["name"] = repository, ["private"] = false, ["auto_init"] = true, ["description"] = "Personal Dicode Config Checker subscription output" }, cancellationToken);
            created = true;
        }
        var repo = await RetryAsync(() => SendAsync(client, HttpMethod.Get, $"repos/{owner}/{repository}", null, cancellationToken), cancellationToken);
        var branch = repo["default_branch"]?.GetValue<string>() ?? "main";
        var currentSub = await ReadFileAsync(client, owner, repository, branch, "sub.txt", cancellationToken);
        var currentProxy = await ReadFileAsync(client, owner, repository, branch, "proxy.txt", cancellationToken);
        var changed = currentSub != subText || currentProxy != proxyText;
        if (changed) await AtomicPublishAsync(client, owner, repository, branch, subText, proxyText, cancellationToken);
        return new(owner, repository, branch, created, changed);
    }

    private static async Task AtomicPublishAsync(HttpClient client, string owner, string repository, string branch, string subText, string proxyText, CancellationToken cancellationToken)
    {
        var reference = await RetryAsync(() => SendAsync(client, HttpMethod.Get, $"repos/{owner}/{repository}/git/ref/heads/{Uri.EscapeDataString(branch)}", null, cancellationToken), cancellationToken);
        var parent = reference["object"]?["sha"]?.GetValue<string>() ?? throw new InvalidOperationException("شاخهٔ ساب آماده نیست.");
        var commit = await SendAsync(client, HttpMethod.Get, $"repos/{owner}/{repository}/git/commits/{parent}", null, cancellationToken);
        var baseTree = commit["tree"]?["sha"]?.GetValue<string>() ?? throw new InvalidOperationException("درخت پایه خوانده نشد.");
        var entries = new JsonArray();
        foreach (var (path, text) in new[] { ("sub.txt", subText), ("proxy.txt", proxyText) })
        {
            var blob = await SendAsync(client, HttpMethod.Post, $"repos/{owner}/{repository}/git/blobs", new JsonObject { ["content"] = Convert.ToBase64String(Encoding.UTF8.GetBytes(text)), ["encoding"] = "base64" }, cancellationToken);
            entries.Add(new JsonObject { ["path"] = path, ["mode"] = "100644", ["type"] = "blob", ["sha"] = blob["sha"]?.GetValue<string>() });
        }
        var tree = await SendAsync(client, HttpMethod.Post, $"repos/{owner}/{repository}/git/trees", new JsonObject { ["base_tree"] = baseTree, ["tree"] = entries }, cancellationToken);
        var next = await SendAsync(client, HttpMethod.Post, $"repos/{owner}/{repository}/git/commits", new JsonObject { ["message"] = "Update Dicode subscription outputs", ["tree"] = tree["sha"]?.GetValue<string>(), ["parents"] = new JsonArray(parent) }, cancellationToken);
        await SendAsync(client, HttpMethod.Patch, $"repos/{owner}/{repository}/git/refs/heads/{Uri.EscapeDataString(branch)}", new JsonObject { ["sha"] = next["sha"]?.GetValue<string>(), ["force"] = false }, cancellationToken);
        if (await ReadFileAsync(client, owner, repository, branch, "sub.txt", cancellationToken) != subText || await ReadFileAsync(client, owner, repository, branch, "proxy.txt", cancellationToken) != proxyText)
            throw new InvalidOperationException("راستی‌آزمایی انتشار ساب ناموفق بود.");
    }

    private static async Task<string?> ReadFileAsync(HttpClient client, string owner, string repository, string branch, string file, CancellationToken cancellationToken)
    {
        try
        {
            var node = await SendAsync(client, HttpMethod.Get, $"repos/{owner}/{repository}/contents/{file}?ref={Uri.EscapeDataString(branch)}", null, cancellationToken);
            var content = node["content"]?.GetValue<string>()?.Replace("\n", "");
            return string.IsNullOrEmpty(content) ? "" : Encoding.UTF8.GetString(Convert.FromBase64String(content));
        }
        catch (HttpRequestException ex) when (ex.StatusCode == HttpStatusCode.NotFound) { return null; }
    }

    private static HttpClient CreateClient(string token)
    {
        var client = new HttpClient { BaseAddress = new Uri("https://api.github.com/"), Timeout = TimeSpan.FromSeconds(20) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("DicodeConfigChecker/2.0");
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token.Trim());
        client.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
        client.DefaultRequestHeaders.Add("X-GitHub-Api-Version", "2022-11-28");
        return client;
    }

    private static async Task<JsonObject> SendAsync(HttpClient client, HttpMethod method, string path, JsonObject? payload, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(method, path);
        if (payload is not null) request.Content = new StringContent(payload.ToJsonString(), Encoding.UTF8, "application/json");
        using var response = await client.SendAsync(request, cancellationToken);
        var text = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode) throw new HttpRequestException($"GitHub API {(int)response.StatusCode}: {text[..Math.Min(300, text.Length)]}", null, response.StatusCode);
        return JsonNode.Parse(text)?.AsObject() ?? [];
    }

    private static async Task<JsonObject> RetryAsync(Func<Task<JsonObject>> action, CancellationToken cancellationToken)
    {
        Exception? last = null;
        for (var attempt = 0; attempt < 4; attempt++)
        {
            try { return await action(); }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException) { last = ex; await Task.Delay(TimeSpan.FromMilliseconds(400 * Math.Pow(2, attempt)), cancellationToken); }
        }
        throw new InvalidOperationException("اتصال GitHub موقتاً در دسترس نیست؛ خروجی محلی حفظ شد.", last);
    }

    private static string? ParseRepository(string value, string owner)
    {
        var parts = value.Trim().TrimEnd('/').Split('/');
        if (parts.Length < 2) return null;
        var candidateOwner = parts[^2]; var name = parts[^1].Replace(".git", "", StringComparison.OrdinalIgnoreCase);
        return candidateOwner.Equals(owner, StringComparison.OrdinalIgnoreCase) && name.Length > 0 ? name : null;
    }
}
