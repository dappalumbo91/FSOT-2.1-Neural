# Machine encoding (primary) vs Morse (secondary)

## Decision

For a **computer-native neurological body**, the default translation path is **machine**, not Morse.

| Path | Role | Use when |
|------|------|----------|
| **`machine`** ★ | UTF-8 / raw bytes → T1 trit packs → `MachineWord` (OS-visible integers) | Sensory inject, IPC, Zig ABI, Linux/Windows buffers |
| **`chemical`** | DNA/codon primary map (A,G=+1; C,T=−1) → AA/process | Genetics / wet-lab structure |
| **`morse`** | ITU Morse ↔ trit (legacy) | Human telegraphy demos only |

**Why not Morse as primary?**  
Morse is optimized for human ears and radio. Operating systems move **bytes and machine words**. FSOT trinary stays the neural code; packing into little-endian integers matches bare-metal `TritWord` and Linux/Windows process ABI.

Chemical signals still matter: codon map remains the **genetic** spine. Machine path is how the **computer body** talks.

## API

```python
from fsot_nuron.machine_encode import translate, EncodePath

translate("hello", path=EncodePath.MACHINE)
translate("ATGAAACGG", path=EncodePath.CHEMICAL)
translate("SOS", path=EncodePath.MORSE)  # secondary
```

Console: **Machine encode** tab in `python -m product.console`.

## Relation to product UI

UI stays local (tkinter / later GTK-on-Linux). Encoding tab shows hex machine words and trit streams ready for inject into the multi-region brain.
