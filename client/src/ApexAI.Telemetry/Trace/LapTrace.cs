using System.IO.Compression;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ApexAI.Telemetry.Trace;

/// <summary>
/// Canonical "lap-trace/1": columnar channels — the contract shared with the backend.
/// Serialized as gzip-compressed JSON for upload (tens of KB per lap).
/// </summary>
public sealed class LapTrace
{
    public const string Schema = "lap-trace/1";

    [JsonPropertyName("schema")]
    public string SchemaVersion { get; init; } = Schema;

    [JsonPropertyName("hz")]
    public int Hz { get; init; } = 60;

    [JsonPropertyName("channels")]
    public required Dictionary<string, IReadOnlyList<double>> Channels { get; init; }

    [JsonIgnore]
    public int Points => Channels.TryGetValue("t_ms", out var t) ? t.Count : 0;

    public byte[] ToGzipJson()
    {
        byte[] json = JsonSerializer.SerializeToUtf8Bytes(this);
        using var output = new MemoryStream();
        using (var gzip = new GZipStream(output, CompressionLevel.Optimal, leaveOpen: true))
        {
            gzip.Write(json, 0, json.Length);
        }
        return output.ToArray();
    }
}
