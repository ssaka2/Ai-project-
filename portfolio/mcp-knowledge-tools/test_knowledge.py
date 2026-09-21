import sys
import tempfile
import unittest
from pathlib import Path
from mcp import Client, StdioServerParameters
from knowledge_server import create_server, load_documents


class KnowledgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'demo.md').write_text('# Demo\nDeploy with a rollback plan.\nCheck readiness.\n')
        self.server = create_server(self.root)

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_tool_discovery_and_catalog(self):
        async with Client(self.server) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            self.assertEqual(names, {'list_documents', 'read_document', 'search_documents'})
            result = await client.call_tool('list_documents', {})
            self.assertEqual(result.structured_content['documents'][0]['id'], 'demo.md')

    async def test_search_citation_and_read_match(self):
        async with Client(self.server) as client:
            result = await client.call_tool('search_documents', {'query': 'rollback'})
            hit = result.structured_content['matches'][0]
            self.assertEqual(hit['citation'], 'demo.md:L2-L3')
            result = await client.call_tool('read_document', {'document_id': 'demo.md', 'start_line': 2, 'line_count': 2})
            self.assertEqual(result.structured_content['text'], hit['text'])

    async def test_path_traversal_returns_tool_error(self):
        async with Client(self.server) as client:
            result = await client.call_tool('read_document', {'document_id': '../secret.md'})
            self.assertTrue(result.is_error)

    async def test_invalid_range_returns_tool_error(self):
        async with Client(self.server) as client:
            result = await client.call_tool('read_document', {'document_id': 'demo.md', 'line_count': 100})
            self.assertTrue(result.is_error)

    async def test_snapshot_does_not_follow_later_file_edits(self):
        (self.root / 'demo.md').write_text('changed')
        async with Client(self.server) as client:
            result = await client.call_tool('search_documents', {'query': 'rollback'})
            self.assertEqual(len(result.structured_content['matches']), 1)

    async def test_catalog_resource(self):
        async with Client(self.server) as client:
            result = await client.read_resource('knowledge://catalog')
            self.assertIn('demo.md', str(result))

    async def test_stdio_subprocess(self):
        params = StdioServerParameters(command=sys.executable,
            args=[str(Path(__file__).with_name('knowledge_server.py').resolve())],
            env={'KNOWLEDGE_ROOT': str(self.root)})
        async with Client(params) as client:
            result = await client.call_tool('search_documents', {'query': 'rollback'})
            self.assertEqual(result.structured_content['matches'][0]['document_id'], 'demo.md')

    async def test_oversized_documents_rejected(self):
        (self.root / 'big.md').write_bytes(b'x' * 100_001)
        with self.assertRaises(ValueError):
            load_documents(self.root)


if __name__ == '__main__':
    unittest.main()
