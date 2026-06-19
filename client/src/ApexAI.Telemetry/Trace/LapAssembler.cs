using ApexAI.Telemetry.F1;

namespace ApexAI.Telemetry.Trace;

/// <summary>
/// Accumulates ~60 Hz samples into laps. Sampling is driven by LapData (the authoritative lap time
/// and distance), each paired with the most recent CarTelemetry. A lap completes when the lap number
/// increments; the just-finished lap is returned as a <see cref="CompletedLap"/>.
/// </summary>
public sealed class LapAssembler
{
    private const int MinSamples = 300; // ~5 s @ 60 Hz — drop tiny out-lap fragments
    private const int MinLapTimeMs = 10_000; // drop implausibly short "laps"

    private readonly List<double> _t = new();
    private readonly List<double> _dist = new();
    private readonly List<double> _speed = new();
    private readonly List<double> _throttle = new();
    private readonly List<double> _brake = new();
    private readonly List<double> _steer = new();
    private readonly List<double> _gear = new();
    private readonly List<double> _rpm = new();

    private readonly int _hz;
    private CarTelemetrySample? _latestTelemetry;
    private int _currentLapNum = -1;
    private bool _invalid;

    public LapAssembler(int hz = 60) => _hz = hz;

    public void OnCarTelemetry(in CarTelemetrySample sample) => _latestTelemetry = sample;

    /// <summary>Feed a lap-data sample. Returns a completed lap when the lap rolls over, else null.</summary>
    public CompletedLap? OnLapData(in LapDataSample lap)
    {
        CompletedLap? completed = null;

        if (_currentLapNum == -1)
        {
            _currentLapNum = lap.CurrentLapNum;
        }
        else if (lap.CurrentLapNum != _currentLapNum)
        {
            completed = TryFinalize((int)lap.LastLapTimeMs);
            Reset();
            _currentLapNum = lap.CurrentLapNum;
        }

        if (lap.CurrentLapInvalid)
            _invalid = true;

        // Record only once on the timed lap (distance past the start line) and with telemetry in hand.
        if (lap.LapDistanceM >= 0 && _latestTelemetry is { } tel)
        {
            _t.Add(lap.CurrentLapTimeMs);
            _dist.Add(Math.Round(lap.LapDistanceM, 2));
            _speed.Add(tel.SpeedKmh);
            _throttle.Add(Math.Round(tel.Throttle, 3));
            _brake.Add(Math.Round(tel.Brake, 3));
            _steer.Add(Math.Round(tel.Steer, 3));
            _gear.Add(tel.Gear);
            _rpm.Add(tel.EngineRpm);
        }

        return completed;
    }

    private CompletedLap? TryFinalize(int lapTimeMs)
    {
        int n = _t.Count;
        if (n < MinSamples || lapTimeMs < MinLapTimeMs)
            return null;

        var trace = new LapTrace
        {
            Hz = _hz,
            Channels = new Dictionary<string, IReadOnlyList<double>>
            {
                ["t_ms"] = _t.ToArray(),
                ["lap_dist_m"] = _dist.ToArray(),
                ["speed_kmh"] = _speed.ToArray(),
                ["throttle"] = _throttle.ToArray(),
                ["brake"] = _brake.ToArray(),
                ["steer"] = _steer.ToArray(),
                ["gear"] = _gear.ToArray(),
                ["rpm"] = _rpm.ToArray(),
            },
        };
        return new CompletedLap(trace, lapTimeMs, !_invalid, n);
    }

    private void Reset()
    {
        _t.Clear();
        _dist.Clear();
        _speed.Clear();
        _throttle.Clear();
        _brake.Clear();
        _steer.Clear();
        _gear.Clear();
        _rpm.Clear();
        _invalid = false;
    }
}
