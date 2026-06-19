using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace ApexAI.Core;

/// <summary>Typed HTTP client for the ApexAI backend (auth + lap upload).</summary>
public sealed class ApiClient : IDisposable
{
    private readonly HttpClient _http;

    public ApiClient(string apiBase)
    {
        // BaseAddress must end with "/" and request paths must be relative (no leading "/"),
        // otherwise a path prefix like "/papi" is dropped when the URIs are combined.
        var normalized = apiBase.EndsWith('/') ? apiBase : apiBase + "/";
        _http = new HttpClient { BaseAddress = new Uri(normalized), Timeout = TimeSpan.FromSeconds(30) };
    }

    public async Task<AuthTokens> LoginAsync(string email, string password, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync(
            "auth/login", new { email, password }, ApiJson.Options, ct);
        await EnsureSuccessAsync(resp, ct);
        return (await resp.Content.ReadFromJsonAsync<AuthTokens>(ApiJson.Options, ct))!;
    }

    public async Task<AuthTokens> RegisterAsync(string email, string password, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync(
            "auth/register", new { email, password }, ApiJson.Options, ct);
        await EnsureSuccessAsync(resp, ct);
        return (await resp.Content.ReadFromJsonAsync<AuthTokens>(ApiJson.Options, ct))!;
    }

    public async Task<string> RefreshAsync(string refreshToken, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync(
            "auth/refresh", new { refresh_token = refreshToken }, ApiJson.Options, ct);
        await EnsureSuccessAsync(resp, ct);
        var token = await resp.Content.ReadFromJsonAsync<AccessTokenResponse>(ApiJson.Options, ct);
        return token!.AccessToken;
    }

    public async Task UploadLapAsync(
        string accessToken, LapMeta meta, byte[] gzipTrace, CancellationToken ct = default)
    {
        using var form = new MultipartFormDataContent();
        form.Add(
            new StringContent(JsonSerializer.Serialize(meta, ApiJson.Options), Encoding.UTF8),
            "meta");
        var trace = new ByteArrayContent(gzipTrace);
        trace.Headers.ContentType = new MediaTypeHeaderValue("application/gzip");
        form.Add(trace, "trace", "lap.json.gz");

        using var request = new HttpRequestMessage(HttpMethod.Post, "laps") { Content = form };
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);

        var resp = await _http.SendAsync(request, ct);
        await EnsureSuccessAsync(resp, ct);
    }

    private static async Task EnsureSuccessAsync(HttpResponseMessage resp, CancellationToken ct)
    {
        if (resp.IsSuccessStatusCode)
            return;

        string body = await resp.Content.ReadAsStringAsync(ct);
        string code = "error";
        string message = resp.ReasonPhrase ?? "Request failed";
        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("error", out var error))
            {
                code = error.GetProperty("code").GetString() ?? code;
                message = error.GetProperty("message").GetString() ?? message;
            }
        }
        catch (JsonException)
        {
            // non-JSON error body; keep the reason phrase
        }
        throw new ApiException((int)resp.StatusCode, code, message);
    }

    public void Dispose() => _http.Dispose();
}
