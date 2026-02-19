MATCH (n) RETURN n;
MATCH (p:Person) RETURN p.surname, p.nhs_no, p.name, p.age;
MATCH (p:Person) RETURN count(p);
MATCH (c:Crime) RETURN c.last_outcome, c.date, c.id, c.type, c.charge, c.note;
MATCH (c:Crime) RETURN count(c);
MATCH ()-[r]->() RETURN r;
MATCH ()-[r]->() RETURN count(r);
MATCH (p:Person {name: 'John'})-[:PARTY_TO]->(c:Crime) RETURN p.surname, p.nhs_no, p.name, p.age, c.last_outcome, c.date, c.id, c.type, c.charge, c.note;
MATCH (p:Person)-[:PARTY_TO]->(c:Crime) RETURN p.name, p.surname, c.type;
MATCH (p:Person {surname: 'Smith'})-[r]->(n) RETURN p.surname, p.nhs_no, p.name, p.age;
MATCH (p:Person)-[r]->(n) WHERE p.surname = 'Smith' RETURN p.surname, p.nhs_no, p.name, p.age;
MATCH (p1:Person)-[:PARTY_TO]->(c:Crime)<-[:PARTY_TO]-(p2:Person) WHERE p1 <> p2 RETURN p1.name, p2.name, c.type;
MATCH (p1:Person)-[:KNOWS]->(p2:Person)-[:PARTY_TO]->(c:Crime) RETURN p1.name, p2.name;
MATCH (c:Crime)-[:OCCURRED_AT]->(l:Location) RETURN l.postcode;

