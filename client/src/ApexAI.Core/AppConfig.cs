namespace ApexAI.Core;

/// <summary>Client configuration (overridable via environment variables).</summary>
public sealed record AppConfig(string ApiBase, int UdpPort)
{
    public static AppConfig Default => new(
        ApiBase: Environment.GetEnvironmentVariable("APEXAI_API_BASE")
            ?? "https://apex-ai.clique-vpn.ru/papi",
        UdpPort: int.TryParse(Environment.GetEnvironmentVariable("APEXAI_UDP_PORT"), out var p)
            ? p
            : 20777); // F1 default UDP telemetry port
}
