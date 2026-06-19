using System.Text.Json;

namespace ApexAI.Core;

/// <summary>Persists the refresh token to disk so the client stays linked across restarts.</summary>
public sealed class TokenStore
{
    private readonly string _path;

    public TokenStore(string? path = null) => _path = path ?? DefaultPath();

    public static string DefaultDir()
    {
        var dir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ApexAI");
        Directory.CreateDirectory(dir);
        return dir;
    }

    private static string DefaultPath() => Path.Combine(DefaultDir(), "auth.json");

    public StoredAuth? Load()
    {
        if (!File.Exists(_path))
            return null;
        try
        {
            return JsonSerializer.Deserialize<StoredAuth>(File.ReadAllText(_path), ApiJson.Options);
        }
        catch (Exception ex) when (ex is JsonException or IOException)
        {
            return null;
        }
    }

    public void Save(StoredAuth auth) =>
        File.WriteAllText(_path, JsonSerializer.Serialize(auth, ApiJson.Options));

    public void Clear()
    {
        if (File.Exists(_path))
            File.Delete(_path);
    }
}
