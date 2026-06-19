using System.Text.Json;
using System.Text.Json.Serialization;

namespace ApexAI.Core;

/// <summary>Shared JSON options: snake_case to match the backend API, omit null fields.</summary>
public static class ApiJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
}

public sealed record AuthTokens(string AccessToken, string RefreshToken, int ExpiresIn);

public sealed record AccessTokenResponse(string AccessToken, int ExpiresIn);

/// <summary>Lap metadata sent as the JSON `meta` part of `POST /laps` (matches backend LapMeta).</summary>
public sealed record LapMeta(
    string ClientLapUuid,
    string? ClientSessionUuid,
    string Game,
    string? Track,
    string? CarOrTeam,
    string? SessionType,
    string? Weather,
    int LapTimeMs,
    bool Valid,
    DateTimeOffset RecordedAt,
    int SampleCount);

/// <summary>Persisted desktop-client auth (refresh token survives restarts).</summary>
public sealed record StoredAuth(string RefreshToken, string Email);

/// <summary>A non-2xx API response, carrying the backend error envelope's code.</summary>
public sealed class ApiException(int statusCode, string code, string message) : Exception(message)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}
