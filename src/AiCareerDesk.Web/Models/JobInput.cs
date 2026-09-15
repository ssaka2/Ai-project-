using System.ComponentModel.DataAnnotations;

namespace AiCareerDesk.Web.Models;

// Only editable fields: clients cannot submit record ownership or audit timestamps.
public class JobInput : IValidatableObject
{
    public Guid Version { get; set; }

    [Required, StringLength(200)] public string Title { get; set; } = "";
    [Required, StringLength(200)] public string Company { get; set; } = "";
    [StringLength(200)] public string? Location { get; set; }
    [Display(Name = "Application URL"), StringLength(2000)]
    public string? ApplicationUrl { get; set; }
    [StringLength(20000)] public string? Description { get; set; }
    [StringLength(5000)] public string? Notes { get; set; }
    [EnumDataType(typeof(ApplicationStatus))]
    public ApplicationStatus Status { get; set; }

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        if (!string.IsNullOrWhiteSpace(ApplicationUrl) &&
            (!Uri.TryCreate(ApplicationUrl, UriKind.Absolute, out var uri) ||
             (uri.Scheme != Uri.UriSchemeHttps && uri.Scheme != Uri.UriSchemeHttp)))
            yield return new ValidationResult("Enter an absolute http or https URL.", [nameof(ApplicationUrl)]);
    }
}
