using System.Windows;
using ApexAI.Core;

namespace ApexAI.App;

public partial class LoginWindow : Window
{
    private readonly ClientSession _session;

    public event Action? LoggedIn;

    public LoginWindow(ClientSession session)
    {
        InitializeComponent();
        _session = session;
    }

    private async void OnLogin(object sender, RoutedEventArgs e)
    {
        ErrorText.Text = string.Empty;
        LoginButton.IsEnabled = false;
        try
        {
            await _session.LoginAsync(EmailBox.Text.Trim(), PasswordBox.Password);
            LoggedIn?.Invoke();
            Close();
        }
        catch (ApiException ex)
        {
            ErrorText.Text = ex.Code == "invalid_credentials" ? "Неверный email или пароль" : ex.Message;
        }
        catch (Exception ex)
        {
            ErrorText.Text = "Нет связи с сервером: " + ex.Message;
        }
        finally
        {
            LoginButton.IsEnabled = true;
        }
    }
}
