# ApexAI desktop client (C# / .NET 8)

Captures F1 24/25 telemetry over UDP, assembles laps, and uploads them to the backend.

## Projects

| Project | Target | Notes |
|---|---|---|
| `src/ApexAI.Telemetry` | net8.0 | F1 24/25 UDP parser, lap assembler, `lap-trace/1` model. Cross-platform. |
| `src/ApexAI.Core` | net8.0 | API client, auth/session, durable upload queue, UDP capture. Cross-platform. |
| `src/ApexAI.Cli` | net8.0 | Console harness (`apexai`) — `login`, `demo`, `capture`. Cross-platform. |
| `src/ApexAI.App` | net8.0-**windows** | WPF tray app (login + status). **Windows only.** |
| `tests/ApexAI.Telemetry.Tests` | net8.0 | xUnit tests for parser + assembler + trace. |

## Build & test

Cross-platform parts (libraries, CLI, tests) build and run anywhere with the .NET 8 SDK:

```bash
dotnet test tests/ApexAI.Telemetry.Tests        # parser/assembler/trace tests
dotnet build src/ApexAI.Cli                      # the console client
```

The WPF tray app builds on Windows only:

```powershell
dotnet build src/ApexAI.App        # net8.0-windows
```

## Running

Configuration via env: `APEXAI_API_BASE` (default `http://localhost:8000`), `APEXAI_UDP_PORT`
(default `20777`).

```bash
# Link this machine to your account
dotnet run --project src/ApexAI.Cli -- login --email you@example.com --password ********

# Smoke test the upload path without the game (generates a synthetic lap)
dotnet run --project src/ApexAI.Cli -- demo --email you@example.com --password ********

# Capture real laps from F1 24/25
dotnet run --project src/ApexAI.Cli -- capture
```

The WPF app (`ApexAI.App`) does the same with a tray icon, login window, and live status.

## Enabling F1 telemetry

In the game: **Settings → Telemetry Settings → UDP Telemetry: On**, UDP Send Rate **60 Hz**,
IP address `127.0.0.1` (or the IP of the PC running the client — works from consoles on the same
network), Port `20777`.

## How a lap is built

`F1PacketParser` reads the player car's blocks (per-car stride is derived from packet length, so it
tolerates minor version differences). `LapAssembler` drives sampling off **Lap Data** (authoritative
lap time + distance), pairing each with the latest **Car Telemetry**; a lap is emitted when the lap
number increments. The trace is gzipped JSON in the shared `lap-trace/1` format and uploaded (or
queued offline and retried).
