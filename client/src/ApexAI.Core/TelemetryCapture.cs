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

    // Live state, surfaced via Snapshot for an on-screen HUD.
    private long _packets;
    private int _lapsCaptured;
    private CarTelemetrySample _lastTelemetry;
    private LapDataSample _lastLap;

    public event Action<CompletedLap>? LapCompleted;

    /// <summary>Immutable live snapshot of capture state (safe to read from a HUD thread).</summary>
    public LiveTelemetry Snapshot => new(
        _packets,
        _lastTelemetry.SpeedKmh,
        _lastTelemetry.Gear,
        _lastTelemetry.Throttle * 100.0,
        _lastTelemetry.Brake * 100.0,
        _lastLap.CurrentLapNum,
        _lastLap.CurrentLapTimeMs,
        _lastLap.LapDistanceM,
        _assembler.CurrentSampleCount,
        _lapsCaptured);

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
        _packets++;

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
                {
                    _lastTelemetry = tel;
                    _assembler.OnCarTelemetry(tel);
                }
                break;
            case PacketIds.LapData:
                if (F1PacketParser.TryParseLapData(data, header, out var lap))
                {
                    _lastLap = lap;
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
        _lapsCaptured++;
        LapCompleted?.Invoke(lap);
    }
}

/// <summary>Immutable live snapshot of capture state for a console/UI HUD.</summary>
public readonly record struct LiveTelemetry(
    long PacketCount,
    int SpeedKmh,
    int Gear,
    double ThrottlePct,
    double BrakePct,
    int CurrentLapNum,
    uint CurrentLapTimeMs,
    double LapDistanceM,
    int SamplesThisLap,
    int LapsCaptured);
