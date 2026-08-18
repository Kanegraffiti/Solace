# Bash fluency benchmark

Solace's Bash capability is measured by a 50-case, offline benchmark in
`tests/data/bash_fluency_cases.json`. The cases reflect real terminal work rather
than general conversation and are grouped into five capabilities:

- Bash-vs-other-language routing;
- task-to-command and reusable-script lookup;
- command, flag, redirection, pipe, and chain explanation;
- diagnosis of common Bash and Termux errors; and
- warnings for destructive or high-risk commands.

Termux cases cover Android shared-storage links, `termux-setup-storage`, package
installation with `pkg`, and the reusable `$HOME/scripts` directory. The test
suite never executes commands from the dataset.

Run only the benchmark with:

```bash
pytest -q tests/test_bash_fluency_benchmark.py
```

Every case is an enforced regression test. Add a case before expanding Bash
behavior, then update the deterministic knowledge or matching logic until the
new case passes. Keep commands reviewable and preserve the rule that Solace does
not silently execute suggested shell commands.
