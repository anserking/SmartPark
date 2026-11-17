# SmartPark algorithms and data structures

The implementations live in `backend/app/algorithms/`. These are application
algorithms used for destination suggestions and parking ranking, not
decorative examples.

| Structure/algorithm | Implementation and use | Time complexity | Extra space |
| --- | --- | --- | --- |
| Trie | `trie.py`; prefix suggestions for normalized destination names | Insert/search: O(m); enumerate suggestions: O(v + r), where m is prefix length, v is visited Trie nodes, and r is returned results | O(total characters) |
| Adjacency-list weighted graph | `graph.py`; road intersections and road edges, with access checks and one-way handling during graph construction | Add edge: O(1); graph storage: O(V + E) | O(V + E) |
| Dijkstra with binary heap | `dijkstra.py`; shortest road distances, predecessor tracking, and route reconstruction | O((V + E) log V) | O(V) |
| Min-heap ranking | `ranking.py`; rank reachable, vehicle-compatible parking candidates by road distance | Build/pop all candidates: O(C log C); retrieving k results: O(C log C + k log C) | O(C) |
| Hash tables | Python dictionaries in Trie children, graph adjacency/distances, and OSM-ID deduplication in `services/parking_normalization.py` | Average lookup/insert: O(1); worst case: O(n) | O(n) |
| Merge sort | `sorting.py` and `ranking.py`; stable custom sorting by known parking fee, with unknown fees last | O(n log n) | O(n) |

`build_weighted_graph()` excludes explicitly inaccessible edges. Car and
motorcycle graphs respect one-way edges; walking graphs treat those edges as
bidirectional. Unknown vehicle compatibility is retained for ranking, while an
explicit incompatibility filters a candidate out.
