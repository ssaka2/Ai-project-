using System.Collections.Concurrent;
using Microsoft.AspNetCore.Identity.UI.Services;
namespace AiCareerDesk.Web.Tests;
public class RecordingEmailSender : IEmailSender
{
    public ConcurrentDictionary<string, string> Messages { get; } = new();
    public Task SendEmailAsync(string email, string subject, string htmlMessage)
    {
        Messages[email] = htmlMessage;
        return Task.CompletedTask;
    }
}
