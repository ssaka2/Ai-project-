using System.ComponentModel.DataAnnotations;

namespace AiCareerDesk.Web.Models;

public enum ApplicationStatus { Saved, Applied, Interviewing, Offer, Rejected, Withdrawn }

public class JobApplication
{
    [ConcurrencyCheck] public Guid Version { get; set; } = Guid.NewGuid();
    public Guid Id { get; set; } = Guid.NewGuid();
    [Required, MaxLength(450)] public string OwnerId { get; set; } = "";
    [Required, MaxLength(200)] public string Title { get; set; } = "";
    [Required, MaxLength(200)] public string Company { get; set; } = "";
    [MaxLength(200)] public string Location { get; set; } = "";
    [MaxLength(2000)] public string ApplicationUrl { get; set; } = "";
    [MaxLength(20000)] public string Description { get; set; } = "";
    [MaxLength(5000)] public string Notes { get; set; } = "";
    public ApplicationStatus Status { get; set; } = ApplicationStatus.Saved;
    public DateTime CreatedUtc { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedUtc { get; set; } = DateTime.UtcNow;
}
