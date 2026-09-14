namespace AiCareerDesk.Web.Services.AI;

public record TailoringRequest(string ResumeSource, string JobDescriptionSource);
public record TailoringResult(string DraftText, IReadOnlyList<string> SkillGaps, string Model, string ResponseId);
public interface IResumeTailoringService
{
    string ProviderName { get; }
    bool IsConfigured { get; }
    Task<TailoringResult> GenerateAsync(TailoringRequest request, CancellationToken cancellationToken);
}

public class TailoringException(string message) : Exception(message);

public class AiOptions
{
    public bool Enabled { get; set; }
    public string ApiKey { get; set; } = "";
    public string Model { get; set; } = "";
}
