namespace ApexAI.Core;

/// <summary>
/// Holds the desktop client's auth state: a short-lived access token in memory plus the persisted
/// refresh token. Transparently refreshes the access token and retries an upload once on 401.
/// </summary>
public sealed class ClientSession
{
    private readonly ApiClient _api;
    private readonly TokenStore _store;

    private string? _accessToken;
    private DateTimeOffset _accessExpiry;
    private string? _refreshToken;

    public string? Email { get; private set; }
    public bool IsLinked => _refreshToken is not null;

    public ClientSession(ApiClient api, TokenStore store)
    {
        _api = api;
        _store = store;
        var stored = store.Load();
        _refreshToken = stored?.RefreshToken;
        Email = stored?.Email;
    }

    public async Task LoginAsync(string email, string password, CancellationToken ct = default)
    {
        var tokens = await _api.LoginAsync(email, password, ct);
        ApplyTokens(tokens, email);
    }

    public async Task RegisterAsync(string email, string password, CancellationToken ct = default)
    {
        var tokens = await _api.RegisterAsync(email, password, ct);
        ApplyTokens(tokens, email);
    }

    private void ApplyTokens(AuthTokens tokens, string email)
    {
        _accessToken = tokens.AccessToken;
        _accessExpiry = DateTimeOffset.UtcNow.AddSeconds(Math.Max(tokens.ExpiresIn - 30, 30));
        _refreshToken = tokens.RefreshToken;
        Email = email;
        _store.Save(new StoredAuth(tokens.RefreshToken, email));
    }

    public async Task<string> EnsureAccessTokenAsync(CancellationToken ct = default)
    {
        if (_accessToken is not null && DateTimeOffset.UtcNow < _accessExpiry)
            return _accessToken;
        if (_refreshToken is null)
            throw new InvalidOperationException("Client is not linked — log in first.");

        _accessToken = await _api.RefreshAsync(_refreshToken, ct);
        _accessExpiry = DateTimeOffset.UtcNow.AddMinutes(14);
        return _accessToken;
    }

    public async Task UploadLapAsync(LapMeta meta, byte[] gzipTrace, CancellationToken ct = default)
    {
        var token = await EnsureAccessTokenAsync(ct);
        try
        {
            await _api.UploadLapAsync(token, meta, gzipTrace, ct);
        }
        catch (ApiException ex) when (ex.StatusCode == 401)
        {
            _accessToken = null; // force a refresh and retry once
            token = await EnsureAccessTokenAsync(ct);
            await _api.UploadLapAsync(token, meta, gzipTrace, ct);
        }
    }

    public void Logout()
    {
        _accessToken = null;
        _refreshToken = null;
        Email = null;
        _store.Clear();
    }
}
