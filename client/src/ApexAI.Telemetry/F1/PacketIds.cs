namespace ApexAI.Telemetry.F1;

/// <summary>F1 24/25 UDP packet type identifiers (PacketHeader.PacketId).</summary>
public static class PacketIds
{
    public const byte Motion = 0;
    public const byte Session = 1;
    public const byte LapData = 2;
    public const byte Event = 3;
    public const byte Participants = 4;
    public const byte CarTelemetry = 6;
}
