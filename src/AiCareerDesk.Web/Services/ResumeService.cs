using System.ComponentModel.DataAnnotations;
using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Models;
using Microsoft.EntityFrameworkCore;
namespace AiCareerDesk.Web.Services;

public class ResumeService(ApplicationDbContext db)
{
    private IQueryable<Resume> Owned(string owner)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        return db.Resumes.Where(x => x.OwnerId == owner);
    }
    private IQueryable<ResumeDraft> Drafts(string owner)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        return db.ResumeDrafts.Where(x => x.OwnerId == owner);
    }
    public Task<List<Resume>> ListAsync(string owner) =>
        Owned(owner).AsNoTracking().OrderByDescending(x => x.UpdatedUtc).ToListAsync();
    public Task<Resume?> GetAsync(string owner, Guid id) =>
        Owned(owner).AsNoTracking().SingleOrDefaultAsync(x => x.Id == id);
    public Task<List<ResumeDraft>> ListDraftsAsync(string owner) =>
        Drafts(owner).AsNoTracking().OrderByDescending(x => x.UpdatedUtc).ToListAsync();
    public Task<ResumeDraft?> GetDraftAsync(string owner, Guid id) =>
        Drafts(owner).AsNoTracking().SingleOrDefaultAsync(x => x.Id == id);

    public async Task<Guid> CreateAsync(string owner, ResumeInput input)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(owner);
        Validator.ValidateObject(input, new ValidationContext(input), true);
        var resume = new Resume { OwnerId = owner, Name = input.Name.Trim(), Content = input.Content };
        db.Resumes.Add(resume);
        await db.SaveChangesAsync();
        return resume.Id;
    }
    public async Task<WriteResult> UpdateAsync(string owner, Guid id, ResumeInput input)
    {
        var resume = await Owned(owner).SingleOrDefaultAsync(x => x.Id == id);
        if (resume is null) return WriteResult.NotFound;
        if (resume.Version != input.Version) return WriteResult.Conflict;
        Validator.ValidateObject(input, new ValidationContext(input), true);
        resume.Name = input.Name.Trim();
        resume.Content = input.Content;
        resume.UpdatedUtc = DateTime.UtcNow;
        resume.Version = Guid.NewGuid();
        try { await db.SaveChangesAsync(); }
        catch (DbUpdateConcurrencyException)
        {
            db.Entry(resume).State = EntityState.Detached;
            return WriteResult.Conflict;
        }
        return WriteResult.Saved;
    }
    public async Task<bool> DeleteAsync(string owner, Guid id)
    {
        var resume = await Owned(owner).SingleOrDefaultAsync(x => x.Id == id);
        if (resume is null) return false;
        db.Resumes.Remove(resume);
        await db.SaveChangesAsync();
        return true;
    }
    public async Task<Guid?> CreateDraftAsync(string owner, Guid resumeId, Guid jobId)
    {
        var resume = await Owned(owner).AsNoTracking().SingleOrDefaultAsync(x => x.Id == resumeId);
        var job = await db.Jobs.AsNoTracking().SingleOrDefaultAsync(x => x.Id == jobId && x.OwnerId == owner);
        if (resume is null || job is null) return null;
        var draft = new ResumeDraft
        {
            OwnerId = owner, SourceResumeId = resume.Id, SourceJobId = job.Id,
            Name = resume.Name + " — " + job.Title,
            ResumeSnapshot = resume.Content, JobDescriptionSnapshot = job.Description,
            Content = resume.Content
        };
        db.ResumeDrafts.Add(draft);
        await db.SaveChangesAsync();
        return draft.Id;
    }
    public async Task<WriteResult> UpdateDraftAsync(string owner, Guid id, DraftInput input)
    {
        var draft = await Drafts(owner).SingleOrDefaultAsync(x => x.Id == id);
        if (draft is null) return WriteResult.NotFound;
        if (draft.Version != input.Version) return WriteResult.Conflict;
        Validator.ValidateObject(input, new ValidationContext(input), true);
        draft.Content = input.Content;
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
    public async Task<bool> DeleteDraftAsync(string owner, Guid id)
    {
        var draft = await Drafts(owner).SingleOrDefaultAsync(x => x.Id == id);
        if (draft is null) return false;
        db.ResumeDrafts.Remove(draft);
        await db.SaveChangesAsync();
        return true;
    }
}
