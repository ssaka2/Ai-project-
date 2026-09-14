# AI tailoring setup

The app includes an OpenAI Responses API adapter. It is **disabled by default**.
Enable it only on a configured server with an API key and a model that supports
Responses structured JSON output. No live OpenAI call was made during implementation.

## Development configuration

Use user secrets from the repository root:

```sh
dotnet user-secrets set "AI:ApiKey" "<your-api-key>" --project src/AiCareerDesk.Web
dotnet user-secrets set "AI:Model" "<supported-model-id>" --project src/AiCareerDesk.Web
dotnet user-secrets set "AI:Enabled" "true" --project src/AiCareerDesk.Web
```

Replace the placeholders locally. Do not paste credentials into issues, pull
requests, screenshots, or committed files. In hosting, use the secret manager
or AI__ApiKey, AI__Model, and AI__Enabled environment variables.

AI uses the configured API account. The application does not provision API access
or change subscriptions. No key or model identifier is hard-coded.

Apply migrations before starting the updated app:

```sh
dotnet tool restore
dotnet ef database update --project src/AiCareerDesk.Web
```

## User workflow

1. Save a resume and a job description, then create a draft.
2. Open AI suggestions from that draft.
3. Inspect the source snapshots and confirm sending them to OpenAI.
4. Generate a suggestion. It is stored separately; the saved draft is unchanged.
5. Compare suggested text, current saved text, and the skill-gap summary.
6. Choose Use this suggestion to replace saved draft text, or keep editing manually.
7. Review every factual claim before downloading and using the resume.

Generation uses the original snapshots, not later changes to the source records.
Create a new draft if the original sources need to change. Suggestions and their
provider/model/response/prompt-version metadata are retained with the draft.
Deleting a draft removes its suggestions.

The adapter requests store=false; this is not a promise of zero provider retention.
Review the provider's current data policy before using real personal data.
No resume content or provider error body is intentionally logged by this code.

## Failure and cost controls

- Maximum 30,000 resume characters and 20,000 job-description characters.
- Maximum 6,000 output tokens; responses must be completed and structurally valid.
- Maximum 256 KiB response body, 30,000 output characters, and 20 gap entries.
- A 60-second request deadline and request cancellation support.
- At most three generation attempts per account per ten-minute window.
- At most two simultaneous generations per application instance.
- No automatic retries of paid generation requests.

Limits are in-memory and reset on restart. Before running multiple app instances,
use shared limits and provider-side spend controls. Failed provider requests can
still count toward application and provider limits.

Missing configuration leaves job tracking and manual resume editing available.
Failures, refusals, malformed/incomplete responses, and timeouts never replace a draft.

## Edit conflicts

Draft edits and suggestion acceptance carry an optimistic concurrency token.
If another session saves first, the stale request gets HTTP 409. The draft editor
keeps submitted text visible; open the latest saved draft in a new tab to compare
and copy desired changes. On the suggestion page, reload the comparison before
deciding whether to apply. Jobs and base resumes still use last-write-wins.

## Validation limits

Automated tests use fake providers and fake HTTP responses. They verify request
shape, ownership, consent, parsing, failure handling, separate suggestion storage,
and conflict behavior. They cannot prove a live model never invents facts.
Run a small synthetic live evaluation after configuring the provider; real output
quality and account/model compatibility remain unverified.

## Primary references

- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [API data controls](https://developers.openai.com/api/docs/guides/your-data)
