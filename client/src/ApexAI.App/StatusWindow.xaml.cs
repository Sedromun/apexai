using System.ComponentModel;
using System.Diagnostics;
using System.Windows;
using ApexAI.Core;
using ApexAI.Telemetry.Trace;

namespace ApexAI.App;

public partial class StatusWindow : Window
{
    private readonly ClientSession _session;
    private readonly UploadQueue _queue;
    private readonly Action _onLogout;

    /// <summary>Set by the app to permit a real close (otherwise closing hides to the tray).</summary>
    public bool AllowClose { get; set; }

    public StatusWindow(ClientSession session, UploadQueue queue, Action onLogout)
    {
        InitializeComponent();
        _session = session;
        _queue = queue;
        _onLogout = onLogout;

        AccountText.Text = $"Аккаунт: {session.Email}";
        StatusText.Text = "Ожидание телеметрии F1 (UDP) …";
        RefreshPending();
    }

    public void OnLapCompleted(CompletedLap lap)
    {
        Dispatcher.Invoke(() =>
        {
            string suffix = lap.Valid ? string.Empty : "  — невалидный";
            LapsList.Items.Insert(0, $"{lap.LapTimeMs / 1000.0:F3} с  ({lap.SampleCount} точек){suffix}");
            StatusText.Text = "Игра обнаружена ✓   Запись идёт ✓";
            RefreshPending();
        });
    }

    public void RefreshPending() =>
        Dispatcher.Invoke(() => PendingText.Text = $"В очереди на отправку: {_queue.PendingCount}");

    private void OnOpenCabinet(object sender, RoutedEventArgs e) =>
        Process.Start(new ProcessStartInfo("http://localhost:3000") { UseShellExecute = true });

    private void OnLogout(object sender, RoutedEventArgs e) => _onLogout();

    protected override void OnClosing(CancelEventArgs e)
    {
        if (!AllowClose)
        {
            e.Cancel = true; // minimize to tray instead of exiting
            Hide();
        }
        base.OnClosing(e);
    }
}
