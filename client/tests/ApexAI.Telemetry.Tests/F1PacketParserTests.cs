using ApexAI.Telemetry.F1;
using Xunit;

namespace ApexAI.Telemetry.Tests;

public class F1PacketParserTests
{
    [Fact]
    public void ParsesHeader()
    {
        var packet = TestPackets.CarTelemetry(3, 250, 1f, 0f, 0f, 0, 6, 11500, 1);
        Assert.True(F1PacketParser.TryParseHeader(packet, out var header));
        Assert.Equal(F1PacketParser.FormatF1_24, header.PacketFormat);
        Assert.Equal(PacketIds.CarTelemetry, header.PacketId);
        Assert.Equal(3, header.PlayerCarIndex);
    }

    [Fact]
    public void RejectsUnknownFormat()
    {
        var packet = TestPackets.CarTelemetry(0, 100, 1f, 0f, 0f, 0, 4, 9000, 0, format: 2019);
        Assert.False(F1PacketParser.TryParseHeader(packet, out _));
    }

    [Fact]
    public void ParsesPlayerCarTelemetry()
    {
        // Player at index 5 — verifies per-car indexing, not just the first block.
        var packet = TestPackets.CarTelemetry(5, 312, 0.95f, -0.25f, 0.10f, 40, 7, 11800, 1);
        Assert.True(F1PacketParser.TryParseHeader(packet, out var header));
        Assert.True(F1PacketParser.TryParseCarTelemetry(packet, header, out var t));

        Assert.Equal(312, t.SpeedKmh);
        Assert.Equal(0.95f, t.Throttle, 3);
        Assert.Equal(-0.25f, t.Steer, 3);
        Assert.Equal(0.10f, t.Brake, 3);
        Assert.Equal(40, t.Clutch);
        Assert.Equal((sbyte)7, t.Gear);
        Assert.Equal(11800, t.EngineRpm);
        Assert.Equal(1, t.Drs);
    }

    [Fact]
    public void ParsesNegativeGear()
    {
        var packet = TestPackets.CarTelemetry(0, 0, 0f, 0f, 1f, 0, gear: -1, 0, 0);
        F1PacketParser.TryParseHeader(packet, out var header);
        Assert.True(F1PacketParser.TryParseCarTelemetry(packet, header, out var t));
        Assert.Equal((sbyte)-1, t.Gear); // reverse
    }

    [Fact]
    public void ParsesPlayerLapData()
    {
        var packet = TestPackets.LapData(5, currentMs: 45000, lastMs: 89000, distance: 1234.5f,
            lapNum: 3, invalid: true);
        Assert.True(F1PacketParser.TryParseHeader(packet, out var header));
        Assert.True(F1PacketParser.TryParseLapData(packet, header, out var lap));

        Assert.Equal(45000u, lap.CurrentLapTimeMs);
        Assert.Equal(89000u, lap.LastLapTimeMs);
        Assert.Equal(1234.5f, lap.LapDistanceM, 2);
        Assert.Equal(3, lap.CurrentLapNum);
        Assert.True(lap.CurrentLapInvalid);
    }

    [Fact]
    public void ParsesSession()
    {
        var packet = TestPackets.Session(trackId: 10, sessionType: 13, weather: 0); // Spa, time trial
        Assert.True(F1PacketParser.TryParseHeader(packet, out var header));
        Assert.True(F1PacketParser.TryParseSession(packet, header, out var info));

        Assert.Equal((sbyte)10, info.TrackId);
        Assert.Equal("Spa", info.TrackName);
        Assert.Equal("time_trial", info.SessionTypeName);
    }

    [Fact]
    public void WrongPacketTypeIsRejected()
    {
        var session = TestPackets.Session(0, 1, 0);
        F1PacketParser.TryParseHeader(session, out var header);
        Assert.False(F1PacketParser.TryParseCarTelemetry(session, header, out _));
    }
}
