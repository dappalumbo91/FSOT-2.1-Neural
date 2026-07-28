# Shakespeare corpus — classical English literature foundation

**Keep.** Culturally dense, widely discussed literature — useful as a **classical English / literature** foundation for future FSOT communication benchmarks (not as an LLM training stack).

| File | Role |
|------|------|
| `stream_shakespeare.txt` | Plain-text stream for encode / retrieve / style probes |
| `fsot_shakespeare_test.py` | Legacy lab script (reference only; prefer mission runners) |
| `fsot_v4_shakespeare.py` | Legacy lab script (reference only) |

**Not Morse.** Telegraphy demos are secondary elsewhere (`morse_itu` optional path only).

## Future use (planned)

- Machine-path encode of lines → multi-region memory probe  
- Compare retrieval / paraphrase fidelity as a **literature intelligence** ladder  
- Bridge later to NLP externals (IMDB, etc.) for broader natural-language *benchmarks* once a communication bridge exists  

```powershell
# Example: machine-encode a line (mission path)
python -c "from fsot_nuron.machine_encode import translate, EncodePath; print(translate(open(r'data/literature/shakespeare/stream_shakespeare.txt',encoding='utf-8',errors='replace').read()[:200], path=EncodePath.MACHINE)['n_trits'])"
```
