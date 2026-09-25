FROM python:3.13-slim
RUN groupadd --gid 10001 vpnapi && useradd --uid 10001 --gid vpnapi --no-create-home vpnapi
WORKDIR /app
COPY vpn_api.py .
RUN mkdir /data && chown vpnapi:vpnapi /data
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 VPN_API_HOST=0.0.0.0 PORT=8090 VPN_DATABASE=/data/peers.db
EXPOSE 8090
HEALTHCHECK --interval=10s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2)"
CMD ["python", "vpn_api.py"]
