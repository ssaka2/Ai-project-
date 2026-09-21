"""Call the actual MCP server through the SDK's in-memory protocol client."""
import asyncio
import json
from pathlib import Path
from mcp import Client
from knowledge_server import create_server


async def main():
    async with Client(create_server(Path(__file__).with_name('notes'))) as client:
        result = await client.call_tool('search_documents', {'query': 'rollback'})
        print(json.dumps(result.structured_content, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
