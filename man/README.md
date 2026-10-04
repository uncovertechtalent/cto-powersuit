# man

The LLM man pages as mdoc(7) sources. Source hub: https://machinebehavior.io/man

## View a page

```bash
man ./man/man7/llm-intro.7
mandoc -T utf8 man/man7/golem.7 | less
```

## Pages

| Section | Pages |
|---|---|
| 1 | `stance(1)`, `register(1)` |
| 5 | `trap-file(5)`, `instruction-file(5)`, `llms.txt(5)`, `lesson(5)` |
| 7 | `llm-intro(7)`, `knowledge-infrastructure(7)`, `codec(7)`, `golem(7)`, `claudish(7)`, `compaction(7)`, `llm-user(7)` |
| 8 | `operations(8)`, `engine(8)`, `track(8)`, `chaos(8)`, `toil(8)` |
