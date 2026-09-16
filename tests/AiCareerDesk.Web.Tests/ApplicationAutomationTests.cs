using System.Text;
using AiCareerDesk.Web.Models;
using AiCareerDesk.Web.Services;
using Xunit;

namespace AiCareerDesk.Web.Tests;

public class ApplicationAutomationTests
{
    [Fact]
    public void DueQueueIncludesBoundaryAndExcludesClosedAndFutureRecords()
    {
        var today = new DateTime(2026, 9, 16, 0, 0, 0, DateTimeKind.Utc);
        var applied = new JobApplication { Status = ApplicationStatus.Applied, UpdatedUtc = today.AddDays(-7).AddHours(23) };
        var interview = new JobApplication { Status = ApplicationStatus.Interviewing, UpdatedUtc = today.AddDays(-4) };
        var future = new JobApplication { Status = ApplicationStatus.Applied, UpdatedUtc = today.AddDays(-6) };
        var closed = new JobApplication { Status = ApplicationStatus.Rejected, UpdatedUtc = today.AddDays(-90) };
        Assert.Equal(new[] { interview, applied }, ApplicationAutomation.Due([applied, future, closed, interview], today));
        Assert.Null(ApplicationAutomation.FollowUpDate(closed));
        applied.UpdatedUtc = today;
        Assert.Empty(ApplicationAutomation.Due([applied], today));
    }

    [Theory]
    [InlineData("=HYPERLINK(1)")]
    [InlineData("  +SUM(1)")]
    [InlineData("-1+2")]
    [InlineData("@SUM(1)")]
    [InlineData("\t=1")]
    public void SpreadsheetFormulasAreNeutralized(string title)
    {
        var csv = Encoding.UTF8.GetString(ApplicationAutomation.Csv([new JobApplication { Title = title }]));
        Assert.Contains("\"'" + title + "\"", csv);
    }

    [Fact]
    public void CsvEscapesQuotesAndCommasAndDraftDoesNotInventExperience()
    {
        var job = new JobApplication { Title = "C# Developer", Company = "Example, \"Inc\"" };
        var csv = Encoding.UTF8.GetString(ApplicationAutomation.Csv([job]));
        Assert.Contains("\"Example, \"\"Inc\"\"\"", csv);
        Assert.Contains(job.Title, ApplicationAutomation.Draft(job));
        Assert.Contains("[Your name]", ApplicationAutomation.Draft(job));
    }
}
