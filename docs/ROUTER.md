# CAIROS Request Router

CAIROS uses a request router so deterministic templates do not grab requests
they cannot understand safely.

## Why Routing Exists

Simple commands should stay fast and offline:

```bash
cairos plan create folder docs
cairos how are you
```

Long, fuzzy, typo-heavy or multi-clause requests should use AI fallback when it
is configured, or produce a safe no-match when it is not.

All plans still go through CAIROS safety scanning before display or execution.

## Route Labels

The stable route labels are:

```text
template
ai
conversation
safety_check
no_match
```

## Heuristic Router

The heuristic router is always available and has no third-party dependencies.
It considers:

- word count and character length
- fuzzy phrases such as `something like that`, `maybe`, `oder so`
- multiple clauses such as `and then`, `but`, `except`, `-`
- dangerous shell command patterns
- common conversation inputs
- simple template-compatible patterns
- directory-navigation target terms

## Optional ML Router

The ML router is optional. Normal CAIROS installs do not require scikit-learn or
joblib.

Install training dependencies in a development environment:

```bash
python -m pip install -e '.[ml-router]'
```

Train:

```bash
python scripts/train_router.py --data data/router_training.jsonl
```

Evaluate:

```bash
python scripts/eval_router.py --data data/router_training.jsonl
python scripts/eval_router.py --data data/router_training.jsonl --use-ml
```

The default model output path is:

```text
data/router_model.joblib
```

At runtime, ML is opt-in. If joblib, scikit-learn, or the model file are
missing, CAIROS falls back to the heuristic router without crashing.

## Debugging

Use:

```bash
cairos plan --debug-route <task>
```

Debug output includes:

- router type
- selected route
- confidence
- reason
- complexity score
- fuzzy phrases
- template candidate
- matched terms
- ignored tokens
- template allowed yes/no

## Adding Training Examples

Add JSONL rows to `data/router_training.jsonl` with this shape:

```json
{"text":"create folder docs","label":"template","template_category":"folders","expected_intent":"create folder","shell_hint":"unknown","risk_hint":"low","notes":""}
```

Keep examples realistic. Do not include raw API keys or private paths.
