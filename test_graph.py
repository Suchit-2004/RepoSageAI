
from falkordb import FalkorDB

db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("reposage")

graph.query("""
CREATE
  (a:File {name: 'app.py'}),
  (b:File {name: 'database.py'}),
  (a)-[:DEPENDS_ON]->(b)
""")

result = graph.ro_query("""
MATCH (a:File)-[:DEPENDS_ON]->(b:File)
RETURN a.name, b.name
""")

for row in result.result_set:
    print(f"{row[0]} depends on {row[1]}")

print("RepoSage AI: FalkorDB connection successful!")
