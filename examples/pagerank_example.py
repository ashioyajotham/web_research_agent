import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Add environment variable setup
from dotenv import load_dotenv
load_dotenv()

# Set up Google API key for Gemini
os.environ['GOOGLE_API_KEY'] = os.getenv('GEMINI_API_KEY')

import numpy as np
from tools.code_tools import CodeGeneratorTool

def create_pagerank_implementation():
    return """
import numpy as np

def pagerank(adjacency_matrix: np.ndarray, damping_factor: float = 0.85, iterations: int = 20) -> np.ndarray:
    n = len(adjacency_matrix)
    
    # Normalize adjacency matrix
    out_degrees = np.sum(adjacency_matrix, axis=1)
    transition_matrix = adjacency_matrix / out_degrees[:, np.newaxis]
    transition_matrix = np.nan_to_num(transition_matrix, 0)
    
    # Initialize PageRank values
    pagerank_vector = np.ones(n) / n
    
    # Power iteration
    for _ in range(iterations):
        pagerank_vector_next = (1 - damping_factor) / n + damping_factor * transition_matrix.T.dot(pagerank_vector)
        pagerank_vector = pagerank_vector_next
        
    return pagerank_vector
"""

async def main():
    try:
        # Initialize namespace with required imports
        namespace = {
            'np': np,
        }
        
        # Add PageRank implementation to namespace
        exec(create_pagerank_implementation(), namespace)
        
        # Create adjacency matrix for our graph
        adj_matrix = np.array([
            [0, 1, 1],  # A's links to B, C
            [0, 0, 1],  # B's link to C
            [1, 0, 0]   # C's link to A
        ])
        
        # Calculate PageRank using our implementation
        ranks = namespace['pagerank'](adj_matrix)
        
        # Print results
        print("\nResults:")
        print("-" * 40)
        pages = ['A', 'B', 'C']
        for page, rank in zip(pages, ranks):
            print(f"PageRank of {page}: {rank:.4f}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
