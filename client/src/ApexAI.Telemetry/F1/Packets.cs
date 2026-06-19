namespace ApexAI.Telemetry.F1;

/// <summary>The common 29-byte header at the start of every F1 24/25 UDP packet.</summary>
public readonly record struct PacketHeader(
    ushort PacketFormat,
    byte GameYear,
    byte PacketId,
    ulong SessionUid,
    float SessionTime,
    uint FrameIdentifier,
    byte PlayerCarIndex);

/// <summary>Player car telemetry sampled at ~60 Hz (subset we record).</summary>
public readonly record struct CarTelemetrySample(
    ushort SpeedKmh,
    float Throttle,
    float Steer,
    float Brake,
    byte Clutch,
    sbyte Gear,
    ushort EngineRpm,
    byte Drs);

/// <summary>Player lap data sampled at ~60 Hz (subset we record).</summary>
public readonly record struct LapDataSample(
    uint CurrentLapTimeMs,
    uint LastLapTimeMs,
    float LapDistanceM,
    byte CurrentLapNum,
    bool CurrentLapInvalid);

/// <summary>Session metadata used to label a lap (track, session type, weather).</summary>
public readonly record struct SessionInfo(sbyte TrackId, byte SessionType, byte Weather)
{
    public string TrackName => Lookups.TrackName(TrackId);
    public string SessionTypeName => Lookups.SessionTypeName(SessionType);
    public string WeatherName => Lookups.WeatherName(Weather);
}
