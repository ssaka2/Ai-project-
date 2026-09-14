using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Models;
using Microsoft.EntityFrameworkCore;
namespace AiCareerDesk.Web.Services.AI;

public class TailoringWorkflow(ApplicationDbContext db, IResumeTailoringService provider, GenerationGate gate)
{
    public bool IsConfigured => provider.IsConfigured;

    public async Task<List<TailoringSuggestion>> ListAsync(string owner, Guid draftId)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        if (!await db.ResumeDrafts.AnyAsync(x => x.Id == draftId && x.OwnerId == owner)) return [];
        return await db.TailoringSuggestions.AsNoTracking().Where(x => x.ResumeDraftId == draftId)
            .OrderByDescending(x => x.CreatedUtc).ToListAsync();
    }

    public async Task<Guid?> GenerateAsync(string owner, Guid draftId, bool consent, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        var draft = await db.ResumeDrafts.AsNoTracking()
            .SingleOrDefaultAsync(x => x.Id == draftId && x.OwnerId == owner, cancellationToken);
        if (draft is null) return null;
        if (!consent) throw new TailoringException("Confirm that you want to send these source documents to OpenAI.");
        if (!provider.IsConfigured) throw new TailoringException("AI tailoring is not configured. You can still edit your draft manually.");
        if (string.IsNullOrWhiteSpace(draft.JobDescriptionSnapshot))
            throw new TailoringException("This draft has no job description. Save a job description and create a new draft first.");
        using var lease = gate.Enter(owner);
        var result = await provider.GenerateAsync(new(draft.ResumeSnapshot, draft.JobDescriptionSnapshot), cancellationToken);
        cancellationToken.ThrowIfCancellationRequested();
        // No draft update occurs here. A response cannot overwrite edits made while it was running.
        if (!await db.ResumeDrafts.AnyAsync(x => x.Id == draftId && x.OwnerId == owner, cancellationToken)) return null;
        var suggestion = new TailoringSuggestion
        {
            ResumeDraftId = draftId, Content = result.DraftText,
            SkillGaps = string.Join("\n", result.SkillGaps),
            Provider = provider.ProviderName, Model = result.Model, ResponseId = result.ResponseId
        };
        db.TailoringSuggestions.Add(suggestion);
        try { await db.SaveChangesAsync(cancellationToken); }
        catch (DbUpdateException)
        {
            db.Entry(suggestion).State = EntityState.Detached;
            if (!await db.ResumeDrafts.AnyAsync(x => x.Id == draftId && x.OwnerId == owner, cancellationToken)) return null;
            throw;
        }
        return suggestion.Id;
    }

    public async Task<WriteResult> ApplyAsync(string owner, Guid draftId, Guid suggestionId, Guid expectedVersion)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        var draft = await db.ResumeDrafts.SingleOrDefaultAsync(x => x.Id == draftId && x.OwnerId == owner);
        if (draft is null) return WriteResult.NotFound;
        var suggestion = await db.TailoringSuggestions.AsNoTracking()
            .SingleOrDefaultAsync(x => x.Id == suggestionId && x.ResumeDraftId == draftId);
        if (suggestion is null) return WriteResult.NotFound;
        if (draft.Version != expectedVersion) return WriteResult.Conflict;
        draft.Content = suggestion.Content;
        draft.Version = Guid.NewGuid();
        draft.UpdatedUtc = DateTime.UtcNow;
        try { await db.SaveChangesAsync(); }
        catch (DbUpdateConcurrencyException)
        {
            db.Entry(draft).State = EntityState.Detached;
            return WriteResult.Conflict;
        }
        return WriteResult.Saved;
    }
}
