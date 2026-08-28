# Hall Core 0

Minimal persistent continuity runtime:

```text
verified GitHub webhook -> Hall Event Envelope -> append-only SQLite -> read-only projection -> stop
```

It does not route, commission, bind, execute, merge, publish, or promote.

Run conformance tests:

```bash
python -m unittest discover -s services/hall-core/tests -v
```
