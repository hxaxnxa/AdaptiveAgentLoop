from neo4j import GraphDatabase
import os

# --- Use environment variables for this! ---
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "my-password")

class Neo4jGraph:
    def __init__(self):
        self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self._driver.close()

    def get_session(self):
        return self._driver.session()

# Create a single instance to be used by the app
graph_db = Neo4jGraph()

# Function to get a DB session (for dependency injection)
def get_graph_db():
    return graph_db.get_session()