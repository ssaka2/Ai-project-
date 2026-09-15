using MailKit.Net.Smtp;
using MailKit.Security;
using MimeKit;
using Microsoft.AspNetCore.Identity.UI.Services;
using Microsoft.Extensions.Options;
namespace AiCareerDesk.Web.Services.Email;

public class EmailOptions
{
    public bool Enabled { get; set; }
    public string Host { get; set; } = "";
    public int Port { get; set; } = 587;
    public string Security { get; set; } = "StartTls";
    public string Username { get; set; } = "";
    public string Password { get; set; } = "";
    public string FromAddress { get; set; } = "";
    public string FromName { get; set; } = "AI Career Desk";
    public bool IsConfigured => Enabled && !string.IsNullOrWhiteSpace(Host) &&
        Port is > 0 and <= 65535 && MailboxAddress.TryParse(FromAddress, out _);
    public SecureSocketOptions SocketOptions => Security switch
    {
        "StartTls" => SecureSocketOptions.StartTls,
        "SslOnConnect" => SecureSocketOptions.SslOnConnect,
        "None" => SecureSocketOptions.None,
        _ => throw new InvalidOperationException("Email:Security must be StartTls, SslOnConnect, or None.")
    };
}

public class SmtpEmailSender(IOptions<EmailOptions> options, ILogger<SmtpEmailSender> logger) : IEmailSender
{
    public async Task SendEmailAsync(string email, string subject, string htmlMessage)
    {
        var config = options.Value;
        if (!config.IsConfigured) throw new InvalidOperationException("Email delivery is not configured.");
        var message = new MimeMessage();
        message.From.Add(new MailboxAddress(config.FromName, config.FromAddress));
        message.To.Add(MailboxAddress.Parse(email));
        message.Subject = subject;
        message.Body = new BodyBuilder { HtmlBody = htmlMessage }.ToMessageBody();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        using var client = new SmtpClient();
        try
        {
            await client.ConnectAsync(config.Host, config.Port, config.SocketOptions, timeout.Token);
            if (!string.IsNullOrWhiteSpace(config.Username))
                await client.AuthenticateAsync(config.Username, config.Password, timeout.Token);
            await client.SendAsync(message, timeout.Token);
            await client.DisconnectAsync(true, timeout.Token);
        }
        catch (Exception error) when (error is MailKit.CommandException or MailKit.ProtocolException
            or IOException or OperationCanceledException or System.Net.Sockets.SocketException
            or System.Security.Authentication.AuthenticationException or MailKit.Security.AuthenticationException)
        {
            // Avoid logging addresses, passwords, token URLs, or message bodies.
            logger.LogWarning("SMTP delivery failed.");
            throw new InvalidOperationException("Email could not be delivered. Please retry using the resend confirmation or password recovery page.");
        }
    }
}
