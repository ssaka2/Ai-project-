using System.ComponentModel.DataAnnotations;
namespace AiCareerDesk.Web.Models;

public class TailoringSuggestion
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid ResumeDraftId { get; set; }
    [Required, MaxLength(30000)] public string Content { get; set; } = "";
    [MaxLength(11000)] public string SkillGaps { get; set; } = "";
    [Required, MaxLength(50)] public string Provider { get; set; } = "";
    [Required, MaxLength(200)] public string Model { get; set; } = "";
    [MaxLength(200)] public string ResponseId { get; set; } = "";
    [MaxLength(50)] public string PromptVersion { get; set; } = "resume-tailoring-v1";
    public DateTime CreatedUtc { get; set; } = DateTime.UtcNow;
}

public enum WriteResult { Saved, NotFound, Conflict }
