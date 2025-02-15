class Memory:
    def __init__(self):
        self.past_interactions = []
        self.learned_information = {}

    def store_interaction(self, interaction):
        self.past_interactions.append(interaction)

    def retrieve_interactions(self):
        return self.past_interactions

    def store_information(self, key, value):
        self.learned_information[key] = value

    def retrieve_information(self, key):
        return self.learned_information.get(key, None)

    def clear_memory(self):
        self.past_interactions.clear()
        self.learned_information.clear()