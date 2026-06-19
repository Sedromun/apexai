using System.Net.Sockets;
using ApexAI.Telemetry.F1;
using ApexAI.Telemetry.Trace;

namespace ApexAI.Core;

/// <summary>
/// Listens for F1 24/25 UDP packets, drives the <see cref="LapAssembler"/>, and enqueues each
/// completed lap (with session metadata) for upload.
/// </summary>
public sealed class TelemetryCapture
{
    private readonly int _port;
    private readonly UploadQueue _queue;
    private readonly LapAssembler _assembler = new(60);

    private SessionInfo _session;
    private bool _haveSession;
    private ushort _format = F1PacketParser.FormatF1_25;
    private ulong _sessionUid;

    public event Action<CompletedLap>? LapCompleted;

    public TelemetryCapture(int port, UploadQueue queue)
    {
        _port = port;
        _queue = queue;
    }

    public async Task RunAsync(CancellationToken ct)
    {
        using var udp = new UdpClient(_port);
        while (!ct.IsCancellationRequested)
        {
            UdpReceiveResult result;
            try
            {
                result = await udp.ReceiveAsync(ct);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (SocketException)
            {
                continue; // transient receive error — keep listening
            }
            HandlePacket(result.Buffer);
        }
    }

    /// <summary>Process a single raw packet (public so it can be driven from a replay/test).</summary>
    public void HandlePacket(ReadOnlySpan<byte> data)
    {
        if (!F1PacketParser.TryParseHeader(data, out var header))
            return;
        _format = header.PacketFormat;
        _sessionUid = header.SessionUid;

        switch (header.PacketId)
        {
            case PacketIds.Session:
                if (F1PacketParser.TryParseSession(data, header, out var info))
                {
                    _session = info;
                    _haveSession = true;
                }
                break;
            case PacketIds.CarTelemetry:
                if (F1PacketParser.TryParseCarTelemetry(data, header, out var tel))
                    _assembler.OnCarTelemetry(tel);
                break;
            case PacketIds.LapData:
                if (F1PacketParser.TryParseLapData(data, header, out var lap))
                {
                    var done = _assembler.OnLapData(lap);
                    if (done is not null)
                        Enqueue(done);
                }
                break;
        }
    }

    private void Enqueue(CompletedLap lap)
    {
        var meta = new LapMeta(
            ClientLapUuid: Guid.NewGuid().ToString("N"),
            ClientSessionUuid: $"f1-{_sessionUid}",
            Game: F1PacketParser.GameId(_format),
            Track: _haveSession ? _session.TrackName : null,
            CarOrTeam: null,
            SessionType: _haveSession ? _session.SessionTypeName : null,
            Weather: _haveSession ? _session.WeatherName : null,
            LapTimeMs: lap.LapTimeMs,
            Valid: lap.Valid,
            RecordedAt: DateTimeOffset.UtcNow,
            SampleCount: lap.SampleCount);

        _queue.Enqueue(meta, lap.Trace.ToGzipJson());
        LapCompleted?.Invoke(lap);
    }
}
