using System.Net;
using System.Net.Sockets;
using AiCareerDesk.Web.Services.Email;
using MailKit.Security;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Xunit;

namespace AiCareerDesk.Web.Tests;

public class EmailSenderTests
{
    private static EmailOptions Configured() => new()
    {
        Enabled = true, Host = "smtp.example.test", Port = 587, FromAddress = "desk@example.test"
    };

    [Fact]
    public void ConfiguredRequiresEnabledHostValidPortAndSenderAddress()
    {
        Assert.True(Configured().IsConfigured);
        var disabled = Configured(); disabled.Enabled = false;
        var noHost = Configured(); noHost.Host = " ";
        var zeroPort = Configured(); zeroPort.Port = 0;
        var highPort = Configured(); highPort.Port = 65536;
        var badSender = Configured(); badSender.FromAddress = "not an address";
        foreach (var options in new[] { disabled, noHost, zeroPort, highPort, badSender })
            Assert.False(options.IsConfigured);
    }

    [Theory]
    [InlineData("StartTls", SecureSocketOptions.StartTls)]
    [InlineData("SslOnConnect", SecureSocketOptions.SslOnConnect)]
    [InlineData("None", SecureSocketOptions.None)]
    public void SecuritySettingMapsToSocketOptions(string security, SecureSocketOptions expected)
    {
        var options = Configured();
        options.Security = security;
        Assert.Equal(expected, options.SocketOptions);
    }

    [Theory]
    [InlineData("starttls")]
    [InlineData("Auto")]
    [InlineData("")]
    public void UnknownSecuritySettingIsRejected(string security)
    {
        var options = Configured();
        options.Security = security;
        Assert.Throws<InvalidOperationException>(() => options.SocketOptions);
    }

    [Fact]
    public async Task SendingWithoutConfigurationFailsBeforeConnecting()
    {
        var sender = new SmtpEmailSender(Options.Create(new EmailOptions()), NullLogger<SmtpEmailSender>.Instance);
        var error = await Assert.ThrowsAsync<InvalidOperationException>(() =>
            sender.SendEmailAsync("user@example.test", "Subject", "<p>Body</p>"));
        Assert.Equal("Email delivery is not configured.", error.Message);
    }

    [Fact]
    public async Task DeliveryFailureIsReportedWithoutSecretsOrRecipient()
    {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        var options = Configured();
        options.Host = "127.0.0.1";
        options.Port = port;
        options.Security = "None";
        options.Username = "smtp-user";
        options.Password = "smtp-secret";
        var sender = new SmtpEmailSender(Options.Create(options), NullLogger<SmtpEmailSender>.Instance);

        var error = await Assert.ThrowsAsync<InvalidOperationException>(() =>
            sender.SendEmailAsync("user@example.test", "Reset", "<a href=\"https://example.test/reset?token=abc\">Reset</a>"));

        Assert.StartsWith("Email could not be delivered.", error.Message);
        Assert.Null(error.InnerException);
        foreach (var secret in new[] { "smtp-secret", "smtp-user", "user@example.test", "token=abc" })
            Assert.DoesNotContain(secret, error.ToString());
    }
}
