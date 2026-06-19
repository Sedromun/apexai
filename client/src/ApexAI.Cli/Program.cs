using ApexAI.Cli;
using ApexAI.Core;

var config = AppConfig.Default;
string command = args.Length > 0 ? args[0] : "help";

using var api = new ApiClient(config.ApiBase);
var session = new ClientSession(api, new TokenStore());

try
{
    switch (command)
    {
        case "login":
            await LoginAsync();
            Console.WriteLine($"Linked as {session.Email}. Refresh token stored.");
            return 0;

        case "demo":
        {
            await LoginAsync();
            var queue = new UploadQueue(session);
            var lap = DemoLap.Generate();
            var meta = new LapMeta(
                ClientLapUuid: Guid.NewGuid().ToString("N"),
                ClientSessionUuid: "demo-cli-session",
                Game: "f1_25",
                Track: "Sim Circuit",
                CarOrTeam: "Demo Car",
                SessionType: "time_trial",
                Weather: "clear",
                LapTimeMs: lap.LapTimeMs,
                Valid: lap.Valid,
                RecordedAt: DateTimeOffset.UtcNow,
                SampleCount: lap.SampleCount);

            queue.Enqueue(meta, lap.Trace.ToGzipJson());
            int sent = await queue.FlushAsync();
            Console.WriteLine(
                $"Lap {lap.LapTimeMs / 1000.0:F3}s ({lap.SampleCount} pts): uploaded {sent}, pending {queue.PendingCount}");
            return 0;
        }

        case "capture":
        {
            if (!session.IsLinked)
            {
                Console.Error.WriteLine("Not linked. Run: apexai login --email <e> --password <p>");
                return 1;
            }
            var queue = new UploadQueue(session);
            var capture = new TelemetryCapture(config.UdpPort, queue);
            capture.LapCompleted += lap =>
                Console.WriteLine($"Lap {lap.LapTimeMs / 1000.0:F3}s captured (valid={lap.Valid}), queued.");

            using var cts = new CancellationTokenSource();
            Console.CancelKeyPress += (_, e) =>
            {
                e.Cancel = true;
                cts.Cancel();
            };
            Console.WriteLine($"Listening for F1 UDP on :{config.UdpPort}. Ctrl+C to stop.");
            var flusher = FlushLoop(queue, cts.Token);
            await capture.RunAsync(cts.Token);
            await flusher;
            return 0;
        }

        default:
            Console.WriteLine(
                "ApexAI desktop client (CLI)\n"
                + "  login    --email <e> --password <p>   link this machine\n"
                + "  demo     --email <e> --password <p>   generate + upload a synthetic lap\n"
                + "  capture                               listen to F1 UDP and upload laps");
            return 0;
    }
}
catch (ApiException ex)
{
    Console.Error.WriteLine($"API error [{ex.StatusCode} {ex.Code}]: {ex.Message}");
    return 1;
}

async Task LoginAsync()
{
    var (email, password) = Credentials();
    try
    {
        await session.LoginAsync(email, password);
    }
    catch (ApiException ex) when (ex.StatusCode == 401)
    {
        // First-run convenience: create the account if the credentials don't exist yet.
        await session.RegisterAsync(email, password);
    }
}

(string Email, string Password) Credentials()
{
    string? email = ArgValue("--email") ?? Environment.GetEnvironmentVariable("APEXAI_EMAIL");
    string? password = ArgValue("--password") ?? Environment.GetEnvironmentVariable("APEXAI_PASSWORD");
    if (string.IsNullOrEmpty(email) || string.IsNullOrEmpty(password))
        throw new ApiException(
            400, "no_credentials",
            "Provide --email and --password (or APEXAI_EMAIL / APEXAI_PASSWORD).");
    return (email, password);
}

string? ArgValue(string name)
{
    int i = Array.IndexOf(args, name);
    return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
}

static async Task FlushLoop(UploadQueue queue, CancellationToken ct)
{
    while (!ct.IsCancellationRequested)
    {
        try
        {
            await Task.Delay(5000, ct);
            await queue.FlushAsync(ct);
        }
        catch (OperationCanceledException)
        {
            break;
        }
    }
}
