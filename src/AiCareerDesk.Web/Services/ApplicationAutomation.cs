using System.Globalization;
using System.Text;
using AiCareerDesk.Web.Models;

namespace AiCareerDesk.Web.Services;

public static class ApplicationAutomation
{
    // Suggestions are calculated on demand; no background worker or paid service.
    public static DateTime? FollowUpDate(JobApplication job) => job.Status switch
    {
        ApplicationStatus.Applied => job.UpdatedUtc.Date.AddDays(7),
        ApplicationStatus.Interviewing => job.UpdatedUtc.Date.AddDays(3),
        _ => null
    };

    public static List<JobApplication> Due(IEnumerable<JobApplication> jobs, DateTime utcNow) =>
        jobs.Where(j => FollowUpDate(j) is DateTime due && due <= utcNow.Date)
            .OrderBy(j => FollowUpDate(j)).ThenBy(j => j.Company).ThenBy(j => j.Id).ToList();

    public static string Draft(JobApplication job) =>
        $"Subject: Following up on {job.Title} at {job.Company}\n\n" +
        $"Hello,\n\nI am following up on my application for the {job.Title} position at {job.Company}. " +
        "I remain interested in the opportunity and would appreciate any update on the next steps. " +
        "Please let me know if I can provide any additional information.\n\nThank you for your time,\n[Your name]";

    public static byte[] Csv(IEnumerable<JobApplication> jobs)
    {
        var text = new StringBuilder("Title,Company,Location,Status,Application URL,Updated UTC,Suggested follow-up UTC\r\n");
        foreach (var job in jobs)
        {
            var cells = new[] { job.Title, job.Company, job.Location, job.Status.ToString(),
                job.ApplicationUrl, job.UpdatedUtc.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                FollowUpDate(job)?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) ?? "" };
            text.AppendJoin(',', cells.Select(CsvCell)).Append("\r\n");
        }
        return Encoding.UTF8.GetPreamble().Concat(Encoding.UTF8.GetBytes(text.ToString())).ToArray();
    }

    private static string CsvCell(string value)
    {
        // Quoting alone does not prevent spreadsheet formula execution.
        var trimmed = value.TrimStart();
        if (trimmed.Length > 0 && "=+-@".Contains(trimmed[0]) ||
            value.Any(c => c is '\t' or '\r' or '\n')) value = "'" + value;
        return "\"" + value.Replace("\"", "\"\"") + "\"";
    }
}
