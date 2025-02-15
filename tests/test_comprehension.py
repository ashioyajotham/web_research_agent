import unittest
from src.agent.comprehension import Comprehension

class TestComprehension(unittest.TestCase):

    def setUp(self):
        self.comprehension = Comprehension()

    def test_process_task(self):
        task = "Write a Python function to add two numbers."
        result = self.comprehension.process_task(task)
        self.assertIsNotNone(result)
        self.assertIn("def add_numbers", result)

    def test_adapt_to_similar_task(self):
        task1 = "Create a function that multiplies two numbers."
        task2 = "Write a function to divide two numbers."
        self.comprehension.process_task(task1)
        result = self.comprehension.adapt_to_similar_task(task2)
        self.assertIsNotNone(result)
        self.assertIn("def divide_numbers", result)

if __name__ == '__main__':
    unittest.main()