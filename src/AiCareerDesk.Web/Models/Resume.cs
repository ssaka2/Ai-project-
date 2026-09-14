using System.ComponentModel.DataAnnotations;
namespace AiCareerDesk.Web.Models;

public class Resume
{
    public Guid Id { get; set; } = Guid.NewGuid();
    [Required, MaxLength(450)] public string OwnerId { get; set; } = "";
    [Required, MaxLength(200)] public string Name { get; set; } = "";
    [Required, MaxLength(30000)] public string Content { get; set; } = "";
    public DateTime UpdatedUtc { get; set; } = DateTime.UtcNow;
}

public class ResumeInput
{
    [Required, StringLength(200)] public string Name { get; set; } = "";
    [Required, StringLength(30000)] public string Content { get; set; } = "";
}

public class ResumeDraft
{
    public Guid Id { get; set; } = Guid.NewGuid();
    [Required, MaxLength(450)] public string OwnerId { get; set; } = "";
    // Provenance IDs deliberately have no FK: snapshots survive source deletion.
    public Guid SourceResumeId { get; set; }
    public Guid SourceJobId { get; set; }
    [Required, MaxLength(450)] public string Name { get; set; } = "";
    [Required, MaxLength(30000)] public string ResumeSnapshot { get; set; } = "";
    [MaxLength(20000)] public string JobDescriptionSnapshot { get; set; } = "";
    [Required, MaxLength(30000)] public string Content { get; set; } = "";
    public DateTime CreatedUtc { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedUtc { get; set; } = DateTime.UtcNow;
}

public class DraftInput
{
    [Required, StringLength(30000)] public string Content { get; set; } = "";
}
