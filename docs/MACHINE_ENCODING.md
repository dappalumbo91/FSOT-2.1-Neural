# Machine encoding (primary) vs Morse (secondary)

## Decision

For a **computer-native neurological body**, the default translation path is **machine**, not Morse.

**FSOT marriage (required):** packing alone is transport. Drive and strength go through  
`fsot_nuron.fsot_bridge` — pin archive → Computer_Body / Biology fold → ScalarInput → \(S\)/trinary couple.  
See [`FSOT_APPLICATION_NEURAL.md`](FSOT_APPLICATION_NEURAL.md).

| Path | Role | Use when |
|------|------|----------|
| **`machine`** ★ | UTF-8 / raw bytes → **lossless** bit→trit (0→0, 1→+1) → T1 packs → `MachineWord` / `MachineFrame` | Sensory inject, IPC, Zig ABI, Linux/Windows buffers |
| **`chemical`** | DNA/codon primary map (A,G=+1; C,T=−1) → AA/process → **machine frame** | Genetics / wet-lab structure into the body |
| **`morse`** | ITU Morse ↔ trit (legacy) | Human telegraphy demos only |

**Why not Morse as primary?**  
Morse is optimized for human ears and radio. Operating systems move **bytes and machine words** (syscalls, mmap, pipes, ELF sections). FSOT trinary stays the neural code; packing into little-endian integers matches bare-metal Zig `TritWord` and Linux/Windows process ABI.

```text
chemical signals (DNA / codon / wet-lab structure)
        ↓  genetic spine (always chemical map)
   primary trits  {-1,0,+1}
        ↓  transport (this is the machine path)
   T1 pack → u64 LE words → MachineFrame
        ↓
   SensoryBus / Zig inject / shared memory
```

Chemical signals still matter: codon map remains the **genetic** spine.  
Machine path is how the **computer body** talks — same idea as how Linux and Windows move process memory.

## OS-native ABI frame

```text
magic[4]="FSOT" | version u8 | path_id u8 | n_trits u16 LE
then word records: pack u64 LE | n_trits u8 | pad 3
```

| path_id | meaning |
|---------|---------|
| 1 | machine |
| 2 | chemical |
| 3 | morse (secondary) |

Packing matches `embodiment/zig/src/trit.zig` `TritWord` (2 bits/trit, LE, ≤32 trits/u64).

## API

```python
from fsot_nuron.machine_encode import (
    translate, EncodePath, build_machine_frame,
    chemical_signals_to_machine, encode_to_sensory_packet,
)

translate("hello", path=EncodePath.MACHINE)
chemical_signals_to_machine("ATGAAACGG")   # chem → machine words
frame = build_machine_frame("hello")       # binary IPC buffer
frame.to_bytes()                           # write to pipe / mmap later

# Sensory inject (preferred body entry)
from fsot_nuron.sensory import SensoryBus, push_machine_text
bus = SensoryBus()
push_machine_text(bus, "stimulus", path="machine")
```

CLI:

```powershell
python run_machine_encode.py --verify --inject-demo
python run_machine_encode.py --dna ATGAAACGG
python run_machine_encode.py --text "hello" --path machine
```

Console: **Machine encode** tab in `python -m product.console` (v0.2).

## Relation to product UI

UI stays local (tkinter / later GTK-on-Linux). Encoding tab shows hex machine words, ABI frames, chem→machine bridge, and sensory-bus inject — ready for multi-region brain drive.
