# CAIROS Troubleshooting

## No deterministic match

Configure AI or add a template:

```bash
cairos config ai use-ollama llama3.1
cairos config ai use-gemini gemini-2.5-flash
```

## Gemini model not found

```bash
cairos config ai list-models
cairos config ai use-gemini gemini-2.5-flash
```

## Gemini key missing

```bash
export GEMINI_API_KEY="your-key"
cairos config ai test
```

## Check command did the wrong thing

Shell safety:

```bash
cairos check git push --force
```

Natural language:

```bash
cairos -- check the commit log and summarize it
```

## Windows and WSL

Install inside the WSL distribution where you want to use CAIROS. Windows can
edit files through the UNC path, but the `cairos` executable should run inside
WSL for WSL projects.
