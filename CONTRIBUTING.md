# Contributing to FSOT-2.1-Neural

Fluid Spacetime Omni-Theory 2.1 genetic-codon neural network: biologically structured FSOT neurons wired from the 64-codon trinary genetic map, with zero free parameters.

## Theory authority

- The FSOT theory authority is [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean), engine pin **AEB2AD**.
- Do not invent new constants, LECs, or rules. Every value must trace to the pinned authority.
- Structural math changes are ported through [FSOT-2.1-Cpp](https://github.com/dappalumbo91/FSOT-2.1-Cpp) pull requests first, not merged silently here.
- The in-repo law snapshot (`data/archive_snapshot/`) must not be edited by hand.

## Pull requests

- Branch off `main`; keep **one concern per PR**.
- Describe what changed and why; link any related issue.
- Make sure CI is green before asking for review.

## Tests and CI

CI is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

- **CI smoke** — `python scripts/ci_smoke.py` (seeds, Morse, codon, neuron, failure catalog)
- **Language precision gates** — `python run_language_loop.py --verify-only`

Install with `pip install -r requirements.txt` (CPU torch is fine).

Run the relevant commands locally before pushing.

## License

Contributions are accepted under the Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
By submitting a PR you agree your contribution is licensed under those terms.

## Conduct

Be respectful, precise, and professional. Critique claims and code, not people.
