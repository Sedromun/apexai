using System.IO.Compression;
using System.Text.Json;
using ApexAI.Telemetry.Trace;
using Xunit;

namespace ApexAI.Telemetry.Tests;

public class LapTraceTests
{
    [Fact]
    public void GzipJsonMatchesBackendSchema()
    {
        var trace = new LapTrace
        {
            Hz = 60,
            Channels = new Dictionary<string, IReadOnlyList<double>>
            {
                ["t_ms"] = new double[] { 0, 16, 33 },
                ["lap_dist_m"] = new double[] { 0, 1, 2 },
                ["speed_kmh"] = new double[] { 100, 101, 102 },
                ["throttle"] = new double[] { 1, 1, 1 },
                ["brake"] = new double[] { 0, 0, 0 },
                ["steer"] = new double[] { 0, 0, 0 },
                ["gear"] = new double[] { 3, 3, 3 },
                ["rpm"] = new double[] { 10000, 10000, 10000 },
            },
        };

        byte[] gzip = trace.ToGzipJson();
        Assert.True(gzip.Length > 0);

        using var input = new MemoryStream(gzip);
        using var decompress = new GZipStream(input, CompressionMode.Decompress);
        using var reader = new StreamReader(decompress);
        string json = reader.ReadToEnd();

        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        Assert.Equal("lap-trace/1", root.GetProperty("schema").GetString());
        Assert.Equal(60, root.GetProperty("hz").GetInt32());

        var channels = root.GetProperty("channels");
        Assert.Equal(3, channels.GetProperty("t_ms").GetArrayLength());
        Assert.Equal(3, channels.GetProperty("speed_kmh").GetArrayLength());
        Assert.Equal(3, trace.Points);
    }
}
