import unittest
from src.agent.browser import Browser

class TestBrowser(unittest.TestCase):

    def setUp(self):
        self.browser = Browser()

    def test_search(self):
        query = "OpenAI"
        results = self.browser.search(query)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_retrieve_results(self):
        query = "OpenAI"
        self.browser.search(query)
        results = self.browser.retrieve_results()
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

if __name__ == '__main__':
    unittest.main()