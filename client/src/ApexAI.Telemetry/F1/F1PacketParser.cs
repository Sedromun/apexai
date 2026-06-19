using System.Buffers.Binary;

namespace ApexAI.Telemetry.F1;

/// <summary>
/// Parses the F1 24/25 UDP packets we need to assemble a lap trace.
///
/// Per-car array stride is derived from the packet length — <c>(length - HeaderSize) / 22</c> —
/// so the parser tolerates the small per-entry size differences between game versions. The fields
/// we read all sit at stable, early offsets within each per-car block.
/// </summary>
public static class F1PacketParser
{
    public const int HeaderSize = 29;
    public const int CarCount = 22;
    public const ushort FormatF1_24 = 2024;
    public const ushort FormatF1_25 = 2025;

    public static bool TryParseHeader(ReadOnlySpan<byte> data, out PacketHeader header)
    {
        header = default;
        if (data.Length < HeaderSize)
            return false;

        ushort format = BinaryPrimitives.ReadUInt16LittleEndian(data);
        if (format != FormatF1_24 && format != FormatF1_25)
            return false;

        header = new PacketHeader(
            PacketFormat: format,
            GameYear: data[2],
            PacketId: data[6],
            SessionUid: BinaryPrimitives.ReadUInt64LittleEndian(data.Slice(7, 8)),
            SessionTime: BinaryPrimitives.ReadSingleLittleEndian(data.Slice(15, 4)),
            FrameIdentifier: BinaryPrimitives.ReadUInt32LittleEndian(data.Slice(19, 4)),
            PlayerCarIndex: data[27]);
        return true;
    }

    private static bool TryPlayerBlock(
        ReadOnlySpan<byte> data, in PacketHeader header, int minFieldBytes, out ReadOnlySpan<byte> block)
    {
        block = default;
        int stride = (data.Length - HeaderSize) / CarCount;
        if (stride < minFieldBytes)
            return false;
        int offset = HeaderSize + header.PlayerCarIndex * stride;
        if (offset + minFieldBytes > data.Length)
            return false;
        block = data.Slice(offset, stride);
        return true;
    }

    public static bool TryParseCarTelemetry(
        ReadOnlySpan<byte> data, in PacketHeader header, out CarTelemetrySample sample)
    {
        sample = default;
        if (header.PacketId != PacketIds.CarTelemetry)
            return false;
        if (!TryPlayerBlock(data, header, 19, out var b))
            return false;

        sample = new CarTelemetrySample(
            SpeedKmh: BinaryPrimitives.ReadUInt16LittleEndian(b),
            Throttle: BinaryPrimitives.ReadSingleLittleEndian(b.Slice(2, 4)),
            Steer: BinaryPrimitives.ReadSingleLittleEndian(b.Slice(6, 4)),
            Brake: BinaryPrimitives.ReadSingleLittleEndian(b.Slice(10, 4)),
            Clutch: b[14],
            Gear: (sbyte)b[15],
            EngineRpm: BinaryPrimitives.ReadUInt16LittleEndian(b.Slice(16, 2)),
            Drs: b[18]);
        return true;
    }

    public static bool TryParseLapData(
        ReadOnlySpan<byte> data, in PacketHeader header, out LapDataSample sample)
    {
        sample = default;
        if (header.PacketId != PacketIds.LapData)
            return false;
        if (!TryPlayerBlock(data, header, 38, out var b))
            return false;

        sample = new LapDataSample(
            CurrentLapTimeMs: BinaryPrimitives.ReadUInt32LittleEndian(b.Slice(4, 4)),
            LastLapTimeMs: BinaryPrimitives.ReadUInt32LittleEndian(b.Slice(0, 4)),
            LapDistanceM: BinaryPrimitives.ReadSingleLittleEndian(b.Slice(20, 4)),
            CurrentLapNum: b[33],
            CurrentLapInvalid: b[37] != 0);
        return true;
    }

    public static bool TryParseSession(
        ReadOnlySpan<byte> data, in PacketHeader header, out SessionInfo info)
    {
        info = default;
        if (header.PacketId != PacketIds.Session)
            return false;
        if (data.Length < HeaderSize + 8)
            return false;

        var b = data.Slice(HeaderSize);
        info = new SessionInfo(TrackId: (sbyte)b[7], SessionType: b[6], Weather: b[0]);
        return true;
    }

    /// <summary>Maps the packet format to our backend game id (`f1_24` / `f1_25`).</summary>
    public static string GameId(ushort packetFormat) =>
        packetFormat == FormatF1_25 ? "f1_25" : "f1_24";
}
