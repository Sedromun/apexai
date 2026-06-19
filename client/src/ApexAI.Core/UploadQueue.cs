using System.Text.Json;

namespace ApexAI.Core;

/// <summary>
/// Durable on-disk queue of completed laps. Laps are written immediately (so a crash or offline
/// period never loses them) and uploaded when connectivity allows. Idempotent: the backend dedupes
/// on client_lap_uuid, so a retried upload is harmless.
/// </summary>
public sealed class UploadQueue
{
    private readonly string _dir;
    private readonly ClientSession _session;

    public UploadQueue(ClientSession session, string? dir = null)
    {
        _session = session;
        _dir = dir ?? Path.Combine(TokenStore.DefaultDir(), "queue");
        Directory.CreateDirectory(_dir);
    }

    public int PendingCount => Directory.GetFiles(_dir, "*.meta.json").Length;

    public void Enqueue(LapMeta meta, byte[] gzipTrace)
    {
        string id = Sanitize(meta.ClientLapUuid);
        File.WriteAllText(
            Path.Combine(_dir, id + ".meta.json"), JsonSerializer.Serialize(meta, ApiJson.Options));
        File.WriteAllBytes(Path.Combine(_dir, id + ".trace.gz"), gzipTrace);
    }

    /// <summary>Upload all pending laps. Returns how many were sent. Stops early when offline.</summary>
    public async Task<int> FlushAsync(CancellationToken ct = default)
    {
        int sent = 0;
        foreach (var metaPath in Directory.GetFiles(_dir, "*.meta.json"))
        {
            ct.ThrowIfCancellationRequested();
            string id = Path.GetFileName(metaPath)[..^".meta.json".Length];
            string gzPath = Path.Combine(_dir, id + ".trace.gz");
            if (!File.Exists(gzPath))
            {
                File.Delete(metaPath);
                continue;
            }

            LapMeta? meta = JsonSerializer.Deserialize<LapMeta>(
                await File.ReadAllTextAsync(metaPath, ct), ApiJson.Options);
            if (meta is null)
            {
                Remove(metaPath, gzPath);
                continue;
            }
            byte[] gzip = await File.ReadAllBytesAsync(gzPath, ct);

            try
            {
                await _session.UploadLapAsync(meta, gzip, ct);
                Remove(metaPath, gzPath);
                sent++;
            }
            catch (ApiException ex) when (ex.StatusCode is 400 or 409 or 413 or 422)
            {
                // Permanent rejection (duplicate / invalid / too large) — drop to avoid a poison queue.
                Remove(metaPath, gzPath);
            }
            catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException)
            {
                break; // offline / timeout — keep the lap and retry later
            }
        }
        return sent;
    }

    private static void Remove(string metaPath, string gzPath)
    {
        if (File.Exists(metaPath)) File.Delete(metaPath);
        if (File.Exists(gzPath)) File.Delete(gzPath);
    }

    private static string Sanitize(string id) =>
        string.Concat(id.Where(c => char.IsLetterOrDigit(c) || c is '-' or '_'));
}
