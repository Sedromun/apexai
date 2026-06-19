using System.Buffers.Binary;
using ApexAI.Telemetry.F1;

namespace ApexAI.Telemetry.Tests;

/// <summary>Builds synthetic F1 24/25 UDP packets with known player values for parser tests.</summary>
internal static class TestPackets
{
    private static void WriteHeader(byte[] buf, ushort format, byte packetId, byte playerIdx)
    {
        BinaryPrimitives.WriteUInt16LittleEndian(buf.AsSpan(0, 2), format);
        buf[2] = 24; // gameYear
        buf[6] = packetId;
        buf[27] = playerIdx;
    }

    public static byte[] CarTelemetry(
        byte playerIdx, ushort speed, float throttle, float steer, float brake, byte clutch,
        sbyte gear, ushort rpm, byte drs, ushort format = F1PacketParser.FormatF1_24)
    {
        // header(29) + 22 * 60-byte car blocks + 3 trailing bytes
        var buf = new byte[29 + 22 * 60 + 3];
        WriteHeader(buf, format, PacketIds.CarTelemetry, playerIdx);
        var s = buf.AsSpan(29 + playerIdx * 60);
        BinaryPrimitives.WriteUInt16LittleEndian(s, speed);
        BinaryPrimitives.WriteSingleLittleEndian(s.Slice(2, 4), throttle);
        BinaryPrimitives.WriteSingleLittleEndian(s.Slice(6, 4), steer);
        BinaryPrimitives.WriteSingleLittleEndian(s.Slice(10, 4), brake);
        s[14] = clutch;
        s[15] = (byte)gear;
        BinaryPrimitives.WriteUInt16LittleEndian(s.Slice(16, 2), rpm);
        s[18] = drs;
        return buf;
    }

    public static byte[] LapData(
        byte playerIdx, uint currentMs, uint lastMs, float distance, byte lapNum, bool invalid,
        ushort format = F1PacketParser.FormatF1_24)
    {
        // header(29) + 22 * 57-byte lap blocks + 2 trailing bytes
        var buf = new byte[29 + 22 * 57 + 2];
        WriteHeader(buf, format, PacketIds.LapData, playerIdx);
        var s = buf.AsSpan(29 + playerIdx * 57);
        BinaryPrimitives.WriteUInt32LittleEndian(s.Slice(0, 4), lastMs);
        BinaryPrimitives.WriteUInt32LittleEndian(s.Slice(4, 4), currentMs);
        BinaryPrimitives.WriteSingleLittleEndian(s.Slice(20, 4), distance);
        s[33] = lapNum;
        s[37] = (byte)(invalid ? 1 : 0);
        return buf;
    }

    public static byte[] Session(sbyte trackId, byte sessionType, byte weather)
    {
        var buf = new byte[29 + 700];
        WriteHeader(buf, F1PacketParser.FormatF1_25, PacketIds.Session, 0);
        var s = buf.AsSpan(29);
        s[0] = weather;
        s[6] = sessionType;
        s[7] = (byte)trackId;
        return buf;
    }
}
