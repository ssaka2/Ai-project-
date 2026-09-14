using System.ComponentModel.DataAnnotations;
using AiCareerDesk.Web.Data;
using AiCareerDesk.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace AiCareerDesk.Web.Services;

public class JobService(ApplicationDbContext db)
{
    private IQueryable<JobApplication> Owned(string ownerId)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(ownerId);
        return db.Jobs.Where(x => x.OwnerId == ownerId);
    }

    public Task<List<JobApplication>> ListAsync(string ownerId, ApplicationStatus? status = null)
    {
        var query = Owned(ownerId).AsNoTracking();
        if (status.HasValue) query = query.Where(x => x.Status == status.Value);
        return query.OrderByDescending(x => x.UpdatedUtc).ToListAsync();
    }

    public Task<JobApplication?> GetAsync(string ownerId, Guid id) =>
        Owned(ownerId).AsNoTracking().SingleOrDefaultAsync(x => x.Id == id);

    public async Task<Guid> CreateAsync(string ownerId, JobInput input)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(ownerId);
        var job = new JobApplication { OwnerId = ownerId };
        Apply(job, input);
        db.Jobs.Add(job);
        await db.SaveChangesAsync();
        return job.Id;
    }

    public async Task<bool> UpdateAsync(string ownerId, Guid id, JobInput input)
    {
        var job = await Owned(ownerId).SingleOrDefaultAsync(x => x.Id == id);
        if (job is null) return false;
        var previousStatus = job.Status;
        Apply(job, input);
        if (previousStatus != job.Status)
            db.StatusHistory.Add(new ApplicationStatusHistory
            {
                JobApplicationId = job.Id, FromStatus = previousStatus,
                ToStatus = job.Status, ChangedUtc = job.UpdatedUtc
            });
        // EF commits the job update and its history event in one transaction.
        await db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> DeleteAsync(string ownerId, Guid id)
    {
        var job = await Owned(ownerId).SingleOrDefaultAsync(x => x.Id == id);
        if (job is null) return false;
        db.Jobs.Remove(job);
        await db.SaveChangesAsync();
        return true;
    }

    public async Task<List<ApplicationStatusHistory>> HistoryAsync(string ownerId, Guid id)
    {
        if (!await Owned(ownerId).AnyAsync(x => x.Id == id)) return [];
        return await db.StatusHistory.AsNoTracking().Where(x => x.JobApplicationId == id)
            .OrderByDescending(x => x.ChangedUtc).ToListAsync();
    }

    private static void Apply(JobApplication job, JobInput input)
    {
        Validator.ValidateObject(input, new ValidationContext(input), validateAllProperties: true);
        job.Title = input.Title.Trim();
        job.Company = input.Company.Trim();
        job.Location = input.Location?.Trim() ?? "";
        job.ApplicationUrl = input.ApplicationUrl?.Trim() ?? "";
        job.Description = input.Description ?? "";
        job.Notes = input.Notes ?? "";
        job.Status = input.Status;
        job.UpdatedUtc = DateTime.UtcNow;
    }
}
