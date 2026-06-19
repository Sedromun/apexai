using System.Diagnostics;
using System.Drawing;
using System.Windows;
using System.Windows.Forms;
using ApexAI.Core;
using Application = System.Windows.Application;

namespace ApexAI.App;

/// <summary>
/// Tray application. Wires the capture pipeline (UDP → assembler → queue) to a minimal UI:
/// a login window when unlinked, otherwise a status window, plus a tray icon.
/// </summary>
public partial class App : Application
{
    private readonly AppConfig _config = AppConfig.Default;
    private NotifyIcon _tray = null!;
    private ApiClient _api = null!;
    private ClientSession _session = null!;
    private UploadQueue _queue = null!;
    private CancellationTokenSource? _captureCts;
    private StatusWindow? _statusWindow;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        _api = new ApiClient(_config.ApiBase);
        _session = new ClientSession(_api, new TokenStore());
        _queue = new UploadQueue(_session);

        _tray = new NotifyIcon
        {
            Icon = SystemIcons.Information,
            Visible = true,
            Text = "ApexAI",
        };
        var menu = new ContextMenuStrip();
        menu.Items.Add("Открыть", null, (_, _) => ShowStatus());
        menu.Items.Add("Открыть кабинет", null, (_, _) => OpenCabinet());
        menu.Items.Add("Выход", null, (_, _) => ExitApp());
        _tray.ContextMenuStrip = menu;
        _tray.DoubleClick += (_, _) => ShowStatus();

        if (_session.IsLinked)
        {
            StartCapture();
            ShowStatus();
        }
        else
        {
            ShowLogin();
        }
    }

    private void ShowLogin()
    {
        var login = new LoginWindow(_session);
        login.LoggedIn += () =>
        {
            StartCapture();
            ShowStatus();
        };
        login.Show();
    }

    private void ShowStatus()
    {
        _statusWindow ??= new StatusWindow(_session, _queue, Logout);
        _statusWindow.Show();
        _statusWindow.Activate();
    }

    private void StartCapture()
    {
        _captureCts?.Cancel();
        _captureCts = new CancellationTokenSource();
        var token = _captureCts.Token;

        var capture = new TelemetryCapture(_config.UdpPort, _queue);
        capture.LapCompleted += lap => _statusWindow?.OnLapCompleted(lap);
        _ = Task.Run(() => capture.RunAsync(token));
        _ = Task.Run(() => FlushLoopAsync(token));
    }

    private async Task FlushLoopAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(5000, ct);
                int sent = await _queue.FlushAsync(ct);
                if (sent > 0)
                    _statusWindow?.RefreshPending();
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch
            {
                // transient — keep looping
            }
        }
    }

    private void OpenCabinet() =>
        Process.Start(new ProcessStartInfo(_config.ApiBase.Replace(":8000", ":3000"))
        {
            UseShellExecute = true,
        });

    private void Logout()
    {
        _captureCts?.Cancel();
        _session.Logout();
        if (_statusWindow is not null)
        {
            _statusWindow.AllowClose = true;
            _statusWindow.Close();
            _statusWindow = null;
        }
        ShowLogin();
    }

    private void ExitApp()
    {
        _captureCts?.Cancel();
        if (_statusWindow is not null)
            _statusWindow.AllowClose = true;
        _tray.Visible = false;
        _tray.Dispose();
        _api.Dispose();
        Shutdown();
    }
}
