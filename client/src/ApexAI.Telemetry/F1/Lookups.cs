namespace ApexAI.Telemetry.F1;

/// <summary>Human-readable names for F1 24/25 id enums (track, team, session, weather).</summary>
public static class Lookups
{
    private static readonly Dictionary<int, string> Tracks = new()
    {
        [0] = "Melbourne",
        [1] = "Paul Ricard",
        [2] = "Shanghai",
        [3] = "Sakhir (Bahrain)",
        [4] = "Catalunya",
        [5] = "Monaco",
        [6] = "Montreal",
        [7] = "Silverstone",
        [8] = "Hockenheim",
        [9] = "Hungaroring",
        [10] = "Spa",
        [11] = "Monza",
        [12] = "Singapore",
        [13] = "Suzuka",
        [14] = "Abu Dhabi",
        [15] = "Texas (COTA)",
        [16] = "Brazil (Interlagos)",
        [17] = "Austria (Red Bull Ring)",
        [18] = "Sochi",
        [19] = "Mexico",
        [20] = "Baku",
        [21] = "Sakhir Short",
        [22] = "Silverstone Short",
        [23] = "Texas Short",
        [24] = "Suzuka Short",
        [25] = "Hanoi",
        [26] = "Zandvoort",
        [27] = "Imola",
        [28] = "Portimao",
        [29] = "Jeddah",
        [30] = "Miami",
        [31] = "Las Vegas",
        [32] = "Losail (Qatar)",
    };

    private static readonly Dictionary<int, string> Teams = new()
    {
        [0] = "Mercedes",
        [1] = "Ferrari",
        [2] = "Red Bull Racing",
        [3] = "Williams",
        [4] = "Aston Martin",
        [5] = "Alpine",
        [6] = "RB",
        [7] = "Haas",
        [8] = "McLaren",
        [9] = "Sauber",
    };

    private static readonly Dictionary<int, string> SessionTypes = new()
    {
        [1] = "practice",
        [2] = "practice",
        [3] = "practice",
        [4] = "qualifying",
        [5] = "qualifying",
        [6] = "qualifying",
        [7] = "qualifying",
        [10] = "race",
        [11] = "race",
        [12] = "race",
        [13] = "time_trial",
    };

    private static readonly Dictionary<int, string> Weather = new()
    {
        [0] = "clear",
        [1] = "light_cloud",
        [2] = "overcast",
        [3] = "light_rain",
        [4] = "heavy_rain",
        [5] = "storm",
    };

    public static string TrackName(int trackId) =>
        Tracks.TryGetValue(trackId, out var name) ? name : $"Track {trackId}";

    public static string TeamName(int teamId) =>
        Teams.TryGetValue(teamId, out var name) ? name : $"Team {teamId}";

    public static string SessionTypeName(int sessionType) =>
        SessionTypes.TryGetValue(sessionType, out var name) ? name : "session";

    public static string WeatherName(int weather) =>
        Weather.TryGetValue(weather, out var name) ? name : "unknown";
}
