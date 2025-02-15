import unittest
from src.agent.planner import Planner

class TestPlanner(unittest.TestCase):

    def setUp(self):
        self.planner = Planner()

    def test_create_plan(self):
        task = "Write a Python script to fetch data from an API."
        plan = self.planner.create_plan(task)
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertGreater(len(plan["steps"]), 0)

    def test_execute_plan(self):
        task = "Write a Python script to fetch data from an API."
        plan = self.planner.create_plan(task)
        result = self.planner.execute_plan(plan)
        self.assertTrue(result)

    def test_plan_management(self):
        task1 = "Task 1"
        task2 = "Task 2"
        self.planner.create_plan(task1)
        self.planner.create_plan(task2)
        self.assertEqual(len(self.planner.plans), 2)

if __name__ == '__main__':
    unittest.main()