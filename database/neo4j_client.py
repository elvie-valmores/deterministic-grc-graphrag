from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

class GraphDBClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(URI, auth=AUTH)

    def close(self):
        self.driver.close()

    def commit_mapping_to_graph(self, framework: str, clause: str, internal_policy: str, relationship: str, version: str):
        safe_rel = relationship.upper().replace(" ", "_").strip()

        # Phase 1: Temporal Versioning in Cypher (with proper WITH boundaries)
        query = f"""
        MERGE (f:Framework {{name: $framework}})
        MERGE (c:Clause {{name: $clause}})
        MERGE (f)-[:HAS_CLAUSE]->(c)
        
        WITH c
        // Find existing ACTIVE versions of this policy and retire them
        OPTIONAL MATCH (old_p:Policy {{name: $internal_policy, status: 'ACTIVE'}})-[old_r]->(c)
        SET old_p.status = 'RETIRED'
        
        // Create the new ACTIVE version of the policy
        MERGE (p:Policy {{name: $internal_policy, version: $version}})
        SET p.status = 'ACTIVE'
        MERGE (p)-[:{safe_rel}]->(c)
        """
        
        with self.driver.session() as session:
            session.run(query, framework=framework, clause=clause, internal_policy=internal_policy, version=version)
            print(f"✅ Committed to Graph: {internal_policy} (v{version}) -> {safe_rel} -> {clause}")

    def get_policies_by_clause(self, clause_name: str):
        # Phase 1: Only retrieve ACTIVE policies
        query = """
        MATCH (p:Policy)-[r]->(c:Clause {name: $clause})
        WHERE p.status = 'ACTIVE'
        RETURN p.name AS policy, p.version AS version, type(r) AS relationship
        """
        with self.driver.session() as session:
            result = session.run(query, clause=clause_name)
            return [{"policy": record["policy"], "version": record["version"], "relationship": record["relationship"]} for record in result]

graph_db = GraphDBClient()