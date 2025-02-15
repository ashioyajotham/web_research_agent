class Comprehension:
    def __init__(self):
        self.knowledge_base = []

    def process_task(self, task):
        # Process the given task and update the knowledge base
        processed_info = self._understand_task(task)
        self.knowledge_base.append(processed_info)

    def _understand_task(self, task):
        # Logic to comprehend the task
        return f"Understanding task: {task}"

    def adapt_to_future_tasks(self, new_task):
        # Logic to adapt based on previous tasks
        return f"Adapting to new task: {new_task}"