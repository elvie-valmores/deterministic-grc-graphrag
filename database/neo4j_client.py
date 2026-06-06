from neo4j import GraphDatabase

# Credentials matching your docker-compose.yml
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

class GraphDBClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(URI, auth=AUTH)

    def close(self):
        self.driver.close()

    def commit_mapping_to_graph(self, framework: str, clause: str, internal_policy: str, relationship: str):
        """
        Takes an approved mapping and deterministically writes it to Neo4j.
        Strictly uses MERGE to ensure idempotency.
        """
        safe_rel = relationship.upper().replace(" ", "_").strip()

        query = f"""
        // 1. Find or create the Framework Node
        MERGE (f:Framework {{name: $framework}})
        
        // 2. Find or create the Clause Node, and link it to the Framework
        MERGE (c:Clause {{name: $clause}})
        MERGE (f)-[:HAS_CLAUSE]->(c)
        
        // 3. Find or create your Internal Policy Node
        MERGE (p:Policy {{name: $internal_policy}})
        
        // 4. Create the deterministic edge between your Policy and the Clause
        MERGE (p)-[:{safe_rel}]->(c)
        """
        
        with self.driver.session() as session:
            session.run(query, framework=framework, clause=clause, internal_policy=internal_policy)
            print(f"✅ Successfully committed to Graph: {internal_policy} -> {safe_rel} -> {clause}")

graph_db = GraphDBClient()