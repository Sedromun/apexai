using ApexAI.Telemetry.F1;
using ApexAI.Telemetry.Trace;

namespace ApexAI.Cli;

/// <summary>
/// Generates a synthetic lap by driving the real <see cref="LapAssembler"/> with fabricated
/// samples — exercises the whole capture→trace pipeline without a running game. Used by `demo`.
/// </summary>
internal static class DemoLap
{
    public static CompletedLap Generate()
    {
        var assembler = new LapAssembler(60);
        double speed = 280;
        double distance = 0;
        int timeMs = 0;
        const int samples = 5000;

        for (int i = 0; i < samples; i++)
        {
            double target = 110 + 190 * Math.Abs(Math.Sin(i / 240.0));
            speed += Math.Clamp(target - speed, -9, 5);

            float throttle = speed < target ? 1f : 0f;
            float brake = speed > target + 2 ? (float)Math.Min(1.0, (speed - target) / 18.0) : 0f;
            float steer = (float)(Math.Sin(i / 240.0) * 0.6);
            sbyte gear = (sbyte)Math.Clamp((int)(speed / 40), 1, 8);
            ushort rpm = (ushort)(9000 + (int)(speed % 40 / 40 * 2500));

            assembler.OnCarTelemetry(
                new CarTelemetrySample((ushort)speed, throttle, steer, brake, 0, gear, rpm, 0));
            assembler.OnLapData(new LapDataSample((uint)timeMs, 0, (float)distance, 1, false));

            distance += speed / 3.6 / 60.0;
            timeMs += 1000 / 60;
        }

        return assembler.OnLapData(new LapDataSample(0, (uint)timeMs, 0f, 2, false))!;
    }
}
