FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /source
COPY . .
RUN dotnet restore src/AiCareerDesk.Web/AiCareerDesk.Web.csproj
RUN dotnet tool restore
RUN dotnet publish src/AiCareerDesk.Web/AiCareerDesk.Web.csproj -c Release --no-restore -o /out
RUN dotnet ef migrations bundle --project src/AiCareerDesk.Web --configuration Release --self-contained -r linux-x64 --output /out/migrate

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build --chown=app:app /out .
RUN mkdir -p /var/keys && chown app:app /var/keys
USER app
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "AiCareerDesk.Web.dll"]
