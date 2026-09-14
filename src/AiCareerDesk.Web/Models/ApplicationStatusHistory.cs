namespace AiCareerDesk.Web.Models;
public class ApplicationStatusHistory
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid JobApplicationId { get; set; }
    public ApplicationStatus FromStatus { get; set; }
    public ApplicationStatus ToStatus { get; set; }
    public DateTime ChangedUtc { get; set; } = DateTime.UtcNow;
}
