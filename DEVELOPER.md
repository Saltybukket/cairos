# Developing CAIROS

Main modules:

- `cairos/cli.py`: command routing.
- `cairos/templates.py`: deterministic planning.
- `cairos/safety.py`: risk scanning.
- `cairos/context.py`: compact project context.
- `cairos/ai/`: AI backends and validation.
- `cairos/preview.py`: preview and diff output.
- `cairos/history.py`: safe history.

Run checks:

```bash
make compile
make test
make secret-check
make check
```

Network AI tests are optional:

```bash
make test-ai
```

Use match debugging for template work:

```bash
cairos plan --debug-match create a small bash script that prints current folder
```
