using ApexAI.Telemetry.F1;
using ApexAI.Telemetry.Trace;
using Xunit;

namespace ApexAI.Telemetry.Tests;

public class LapAssemblerTests
{
    private static CarTelemetrySample Tel(ushort speed = 200, sbyte gear = 5) =>
        new(speed, 0.8f, 0.1f, 0.0f, 0, gear, 11000, 0);

    [Fact]
    public void CompletesLapOnRollover()
    {
        var asm = new LapAssembler(60);
        asm.OnCarTelemetry(Tel());

        for (int i = 0; i < 600; i++)
        {
            asm.OnCarTelemetry(Tel((ushort)(150 + i % 150)));
            var mid = asm.OnLapData(new LapDataSample(
                CurrentLapTimeMs: (uint)(i * 150),
                LastLapTimeMs: 0,
                LapDistanceM: i * 8.3f,
                CurrentLapNum: 1,
                CurrentLapInvalid: false));
            Assert.Null(mid);
        }

        var done = asm.OnLapData(new LapDataSample(0, 90000, 0f, 2, false));

        Assert.NotNull(done);
        Assert.Equal(90000, done!.LapTimeMs);
        Assert.True(done.Valid);
        Assert.Equal(600, done.SampleCount);
        Assert.Equal(600, done.Trace.Points);
        Assert.All(done.Trace.Channels.Values, ch => Assert.Equal(600, ch.Count));
    }

    [Fact]
    public void MarksLapInvalidWhenFlagged()
    {
        var asm = new LapAssembler(60);
        asm.OnCarTelemetry(Tel());
        for (int i = 0; i < 400; i++)
            asm.OnLapData(new LapDataSample((uint)(i * 150), 0, i * 10f, 1, CurrentLapInvalid: i == 100));

        var done = asm.OnLapData(new LapDataSample(0, 60000, 0f, 2, false));
        Assert.NotNull(done);
        Assert.False(done!.Valid);
    }

    [Fact]
    public void IgnoresTooShortLap()
    {
        var asm = new LapAssembler(60);
        asm.OnCarTelemetry(Tel());
        for (int i = 0; i < 100; i++)
            asm.OnLapData(new LapDataSample((uint)(i * 150), 0, i * 10f, 1, false));

        var done = asm.OnLapData(new LapDataSample(0, 60000, 0f, 2, false));
        Assert.Null(done); // 100 samples < minimum
    }

    [Fact]
    public void SkipsSamplesBeforeStartLine()
    {
        var asm = new LapAssembler(60);
        asm.OnCarTelemetry(Tel());
        // negative distance (out-lap before the line) must not be recorded
        for (int i = 0; i < 50; i++)
            asm.OnLapData(new LapDataSample((uint)(i * 150), 0, -100f, 1, false));
        for (int i = 0; i < 400; i++)
            asm.OnLapData(new LapDataSample((uint)(i * 150), 0, i * 10f, 1, false));

        var done = asm.OnLapData(new LapDataSample(0, 80000, 0f, 2, false));
        Assert.NotNull(done);
        Assert.Equal(400, done!.SampleCount); // only the 400 post-line samples
    }
}
