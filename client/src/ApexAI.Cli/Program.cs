using System.Text;
using ApexAI.Cli;
using ApexAI.Core;

// Best-effort UTF-8 so non-ASCII (e.g. emails) doesn't mojibake on Windows consoles.
try { Console.OutputEncoding = Encoding.UTF8; } catch { /* output redirected */ }

var config = AppConfig.Default;
using var api = new ApiClient(config.ApiBase);
var session = new ClientSession(api, new TokenStore());

// No arguments → the user almost certainly double-clicked the .exe in Explorer.
// Run a friendly interactive flow and keep the window open; a plain console app
// would otherwise run, print help, and vanish in a flash.
if (args.Length == 0)
    return await RunInteractiveAsync();

string command = args[0];
try
{
    switch (command)
    {
        case "login":
            await LoginAsync();
            Console.WriteLine($"Linked as {session.Email}. Refresh token stored.");
            return 0;

        case "demo":
            await LoginAsync();
            await SendDemoLapAsync();
            return 0;

        case "capture":
            if (!session.IsLinked)
            {
                Console.Error.WriteLine("Not linked. Run: apexai login --email <e> --password <p>");
                return 1;
            }
            await CaptureAsync();
            return 0;

        default:
            Console.WriteLine(
                "ApexAI desktop client (CLI)\n"
                + "  (tip: just double-click apexai.exe for interactive mode)\n\n"
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

// ---------- interactive (double-click) mode ----------

async Task<int> RunInteractiveAsync()
{
    try { Console.Title = "ApexAI - telemetry"; } catch { /* no console */ }
    Console.WriteLine("========================================");
    Console.WriteLine("  ApexAI - F1 24/25 telemetry client");
    Console.WriteLine($"  server: {config.ApiBase}");
    Console.WriteLine("========================================");
    Console.WriteLine();

    try
    {
        if (!session.IsLinked)
        {
            Console.WriteLine("Sign in (a new account is created automatically if it doesn't exist yet).");
            Console.WriteLine();
            string email = Prompt("  Email:    ");
            string password = ReadPassword("  Password: ");
            Console.WriteLine();
            Console.WriteLine("Signing in...");
            await LoginWithAsync(email, password);
            Console.WriteLine($"OK - signed in as {session.Email ?? email}.");
            Console.WriteLine();
        }
        else
        {
            Console.WriteLine("This PC is already signed in.");
            Console.WriteLine();
        }

        Console.WriteLine("What would you like to do?");
        Console.WriteLine("  [1] Capture F1 telemetry   (start a session in F1 24/25)");
        Console.WriteLine("  [2] Send a test lap        (check the connection without the game)");
        Console.Write("Choose 1 or 2 (Enter = 1): ");
        string choice = (Console.ReadLine() ?? "").Trim();
        Console.WriteLine();

        if (choice == "2")
        {
            await SendDemoLapAsync();
            return PauseExit(0, "Test lap sent - open the website to see it.");
        }

        await CaptureAsync();
        return PauseExit(0, "Stopped.");
    }
    catch (OperationCanceledException)
    {
        return PauseExit(0, "Stopped.");
    }
    catch (ApiException ex)
    {
        return PauseExit(1, $"Sign-in/API error [{ex.StatusCode} {ex.Code}]: {ex.Message}");
    }
    catch (Exception ex)
    {
        return PauseExit(1, $"Error: {ex.Message}");
    }
}

// ---------- shared actions ----------

async Task CaptureAsync()
{
    var queue = new UploadQueue(session);
    var capture = new TelemetryCapture(config.UdpPort, queue);
    capture.LapCompleted += lap =>
        Console.WriteLine($"  + Lap {lap.LapTimeMs / 1000.0:F3}s captured (valid={lap.Valid}), uploading...");

    using var cts = new CancellationTokenSource();
    Console.CancelKeyPress += (_, e) =>
    {
        e.Cancel = true;
        cts.Cancel();
    };

    Console.WriteLine($"Listening for F1 telemetry on UDP :{config.UdpPort}.");
    Console.WriteLine("In F1 24/25:  Settings -> Telemetry Settings -> UDP Telemetry = On,");
    Console.WriteLine($"              UDP Port = {config.UdpPort}, UDP Format = 2024 (or 2025). Then drive.");
    Console.WriteLine("Press Ctrl+C to stop.");
    Console.WriteLine();

    var flusher = FlushLoop(queue, cts.Token);
    await capture.RunAsync(cts.Token);
    await flusher;
}

async Task SendDemoLapAsync()
{
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
        $"  Lap {lap.LapTimeMs / 1000.0:F3}s ({lap.SampleCount} pts): uploaded {sent}, pending {queue.PendingCount}");
}

// ---------- login helpers ----------

async Task LoginAsync()
{
    var (email, password) = Credentials();
    await LoginWithAsync(email, password);
}

async Task LoginWithAsync(string email, string password)
{
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

// ---------- console helpers ----------

static string Prompt(string label)
{
    Console.Write(label);
    return (Console.ReadLine() ?? "").Trim();
}

static string ReadPassword(string label)
{
    Console.Write(label);
    var sb = new StringBuilder();
    while (true)
    {
        ConsoleKeyInfo k;
        try
        {
            k = Console.ReadKey(intercept: true);
        }
        catch (InvalidOperationException)
        {
            // No interactive console (input redirected) — fall back to a plain read.
            return (Console.ReadLine() ?? "").Trim();
        }

        if (k.Key == ConsoleKey.Enter)
            break;
        if (k.Key == ConsoleKey.Backspace)
        {
            if (sb.Length > 0)
            {
                sb.Length--;
                Console.Write("\b \b");
            }
        }
        else if (!char.IsControl(k.KeyChar))
        {
            sb.Append(k.KeyChar);
            Console.Write('*');
        }
    }
    return sb.ToString();
}

static int PauseExit(int code, string message)
{
    if (!string.IsNullOrEmpty(message))
        Console.WriteLine(message);
    Console.WriteLine();
    Console.WriteLine("Press any key to close...");
    try { Console.ReadKey(intercept: true); } catch { /* no interactive console */ }
    return code;
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
