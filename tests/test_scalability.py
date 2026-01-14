import unittest
import os
import sys
import time
from unittest.mock import MagicMock, patch
import fakeredis

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables before importing modules
os.environ['OPENAI_API_KEY'] = 'test_key'
os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'test_token'
os.environ['LINE_CHANNEL_SECRET'] = 'test_secret'

class TestScalability(unittest.TestCase):
    def setUp(self):
        # Setup FakeRedis with decode_responses=True to match app behavior
        self.redis_client = fakeredis.FakeStrictRedis(decode_responses=True)
        
        # Patch the redis client in rag_engine
        self.redis_patcher = patch('rag_engine.get_redis_client', return_value=self.redis_client)
        self.mock_get_redis = self.redis_patcher.start()
        
    def tearDown(self):
        self.redis_patcher.stop()
        self.redis_client.flushall()

    @patch('rag_engine.fetch_taoyuanq_content')
    def test_cache_hit_bypass_scraper(self, mock_fetch):
        """Test that if data is in Redis, scraper is NOT called"""
        from rag_engine import get_cached_content
        
        # Seed Redis with data
        self.redis_client.set("taoyuanq_content", "Cached Data")
        
        # Call function
        content = get_cached_content()
        
        # Verify
        self.assertEqual(content, "Cached Data")
        mock_fetch.assert_not_called()

    @patch('rag_engine.fetch_taoyuanq_content')
    def test_cache_miss_triggers_scraper(self, mock_fetch):
        """Test that if Redis is empty, scraper IS called and data is saved"""
        from rag_engine import get_cached_content
        
        mock_fetch.return_value = "Fresh Data"
        
        # Call function
        content = get_cached_content()
        
        # Verify
        self.assertEqual(content, "Fresh Data")
        mock_fetch.assert_called_once()
        
        # Verify data is now in Redis
        saved_data = self.redis_client.get("taoyuanq_content")
        self.assertEqual(saved_data, "Fresh Data")

    def test_redis_connection_failover(self):
        """Test failover to local memory if Redis is down"""
        # Simulate Redis connection error by making get raise an error
        self.redis_client.get = MagicMock(side_effect=Exception("Connection Refused"))
        
        from rag_engine import get_cached_content
        
        with patch('rag_engine.fetch_taoyuanq_content', return_value="Fallback Data") as mock_fetch:
            # Should not crash, but fallback to fetch
            content = get_cached_content()
            self.assertEqual(content, "Fallback Data")

if __name__ == '__main__':
    unittest.main()
