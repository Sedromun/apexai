namespace ApexAI.Telemetry.Trace;

/// <summary>A finished lap ready to upload: the trace plus the metadata derived from it.</summary>
public sealed record CompletedLap(LapTrace Trace, int LapTimeMs, bool Valid, int SampleCount);
