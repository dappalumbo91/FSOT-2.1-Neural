# FSOT 3.0 — Morse Code Tokenisation System

## Architecture Documentation

---

## 1. Foundation: Five Seeds, Zero Free Parameters

The entire system derives from five transcendental/mathematical constants. No tunable hyperparameters exist — every coefficient, threshold, timing ratio, and amplitude is computed from these seeds.

| Seed | Symbol | Value (first 20 digits) | Source |
|------|--------|------------------------|--------|
| Pi | π | 3.1415926535897932385 | Circle constant |
| Euler's number | e | 2.7182818284590452354 | Natural exponential base |
| Golden ratio | φ | 1.6180339887498948482 | (1+√5)/2 |
| Euler-Mascheroni | γ | 0.5772156649015328606 | Harmonic series limit |
| Catalan's constant | G | 0.9159655941772190151 | Alternating beta function |

---

## 2. Derived Constants (from FSOT Mathematical Key)

All intermediate constants are deterministic functions of the five seeds.

### §2 — Stability & Structural Parameters

| Constant | Formula | Value | Role in Morse System |
|----------|---------|-------|---------------------|
| ψ_con (stability line) | (e−1)/e = 1−e⁻¹ | 0.6321 | Dot duration, timing unit |
| η_eff (entropy efficiency) | 1/(π−1) | 0.4669 | Observer efficiency |
| θ_S (structural angle) | sin(ψ_con · η_eff) | 0.2909 | Spin flip energy cost |
| Poof (decay) | exp((−ln π / e) / (η_eff · ln φ)) | computed | Coherence decay |

### §3 — Coherence & Phase

| Constant | Formula | Value | Role |
|----------|---------|-------|------|
| C_eff (coherence) | (1−Poof·sin θ_S)(1+0.01G/(πφ)) | 0.9577 | Token normalisation ceiling |
| P_var (phase variance) | −cos(θ_S + π) | 0.9580 | Collapse threshold component |
| B_in (bleed-in) | C_eff · (1−sin θ_S / φ) | 0.7879 | Attention inhibition |
| P_base | γ / e | 0.2124 | Perceived adjustment base |
| P_new | P_base · √2 | 0.3003 | Scalar engine perceived term |

### §19 — Neural Architecture

| Constant | Formula | Value | Role |
|----------|---------|-------|------|
| Lateral Inhibition | 1/φ | 0.6180 | Dot amplitude, positional decay base |
| Prediction Gain | e/π | 0.8653 | Signal processing |
| Hebbian LR | γ/π | 0.1837 | Token offset seed |
| Sync Decay | 1/φ² | 0.3820 | Inter-element gap duration |

### §24 — Trinary / Collapse

| Constant | Formula | Value | Role |
|----------|---------|-------|------|
| Collapse Threshold | C_eff · P_var | 0.9174 | Token normalisation ceiling |
| Max Trits | 3³ | 27 | Length normalisation denominator |

---

## 3. Layer 1 — Morse Code Table (99 Characters)

Standard ITU plus extended mathematical symbols. Each character maps to a unique dot/dash pattern.

### 3.1 Binary Encoding

```
dot  (.)  →  0    (short signal, amplitude = 1/φ = 0.6180)
dash (-)  →  1    (long signal,  amplitude = 1.0)
```

### 3.2 Character Classes

| Class | Count | Examples |
|-------|-------|---------|
| Letters (A–Z) | 26 | A: `.-`, E: `.`, T: `-`, Z: `--..` |
| Digits (0–9) | 10 | 0: `-----`, 5: `.....` |
| Punctuation (ITU) | 18 | `.`: `.-.-.-`, `?`: `..--..`, `!`: `-.-.--` |
| Greek letters | 16 | π: `.--..-`, α: `.--.-..`, φ: `..--..-` |
| Math operators | 16 | ∫: `.-.--.-`, ∞: `.----.-`, Σ: `...--.-` |
| Additional symbols | 13 | `<`: `.-.-.-. `, `{`: `..---..`, `*`: `.--..-.` |
| **Total** | **99** | All unique, all verified |

---

## 4. Layer 2 — FSOT Token Computation

Each Morse pattern produces a unique scalar token via FSOT seed-derived mathematics. **This is where Morse becomes FSOT.**

### 4.1 D_eff — Effective Dimensionality (the discriminator)

```
D_eff(c) = 5 + Σᵢ (bitᵢ · γⁱ)
```

- **D_base = 5**: Particle Physics dimensionality (lowest FSOT domain, §5)
- **γⁱ positional encoding**: Euler-Mascheroni has no algebraic relation to φ, breaking the golden-ratio identity (1 + 1/φ = φ) that caused early collisions
- Each unique binary pattern → unique D_eff → unique position in the scalar engine's nonlinear landscape

**Why γ and not φ?**  
Early versions used φ-based weights. The identity φ = 1 + 1/φ means mirror patterns (e.g., `.-` vs `-.`) can produce identical weighted sums. γ has no such algebraic relation to φ, so the positional encoding is truly independent of the amplitude weighting.

### 4.2 Token Formula

```
token(c) = φ_component / √D_eff       ← §4 Term 1 base
         + P_new · ln(D_eff / 25)      ← §4 perceived adjustment
         + ψ_con · n / 27              ← §24 length via Max_Trits
         + γ / π                        ← §19 Hebbian_LR offset
```

Where:  
```
φ_component = Σᵢ amp(bitᵢ) · (1/φ)ⁱ

  amp(0) = ψ_con = 0.6321   (dot — stability line)
  amp(1) = 1.0               (dash — reference amplitude)
```

The scalar engine's nonlinear functions **1/√D** and **ln(D/25)** act as natural discriminators — even if two patterns have similar φ_components, differing D_eff values get amplified by these nonlinearities.

### 4.3 Normalised Token

```
token_normalised = raw_token / max_token

  max_token = token("------")    (all dashes, length 6)
  clipped to Collapse Threshold = 0.9174
```

### 4.4 Validation Results

| Test | Result |
|------|--------|
| Morse ↔ Binary roundtrip | 99/99 |
| Token uniqueness | All 99 unique |
| Token → Char roundtrip | 99/99 |
| Text roundtrip | 6/6 test phrases |
| Min token separation | 6.81 × 10⁻⁵ |
| Precision | 50 decimal digits |
| Free parameters | 0 |

---

## 5. Layer 3 — Signal Timing (Waveform)

All Morse signal timing derives from FSOT constants — no arbitrary "3× dot" ratios.

| Parameter | Formula | Value | Standard Morse |
|-----------|---------|-------|---------------|
| Dot duration | ψ_con | 0.6321 | 1 unit |
| Dash duration | ψ_con · φ | 1.0225 | 3 units |
| Dot amplitude | 1/φ | 0.6180 | 1.0 |
| Dash amplitude | 1.0 | 1.0 | 1.0 |
| Inter-element gap | 1/φ² | 0.3820 | 1 unit |
| Inter-letter gap | ψ_con | 0.6321 | 3 units |
| Inter-word gap | ψ_con · φ | 1.0225 | 7 units |

The golden ratio φ naturally scales between dot and dash, replacing the arbitrary 1:3:7 convention with a mathematically principled φ-scaling.

---

## 6. Layer 4 — Quantum Observer Case Model

**The problem**: Morse code is case-insensitive. `A` and `a` produce the same pattern `.-`. How do we encode case?

**The solution**: Quantum spin states as an observer model.

### 6.1 Spin State Mapping

| State | Symbol | Meaning | FSOT Amplitude | Physical Analogy |
|-------|--------|---------|---------------|-----------------|
| Spin UP | \|↑⟩ | Uppercase | φ = 1.618 | Excited state |
| Spin DOWN | \|↓⟩ | Lowercase | 1/φ = 0.618 | Ground state |
| No Spin | · | Non-letter | ψ_con = 0.632 | Superposition |

### 6.2 Observer Rules (Positional Prediction)

The observer predicts the "natural" spin state based on **where the letter sits** in the word and sentence. This mirrors English orthographic conventions:

```
RULE 1: Mid-word (position > 0) → predict |↓⟩ (lowercase)
        "You don't put an uppercase letter in the middle of a word"

RULE 2: Word-initial + sentence start → predict |↑⟩ (uppercase)
        Capitalise the first letter after .  !  ? or start of text

RULE 3: Word-initial + not sentence start → predict |↓⟩ (lowercase)
        Non-initial words default to lowercase

RULE 4: Non-letter character → no spin (NONE)
        Digits, punctuation, symbols have no case
```

### 6.3 Spin Flip = Deviation from Prediction

When the actual case differs from the observer's prediction, a **spin flip** occurs. Each flip costs energy:

```
Flip energy = θ_S = sin(ψ_con · η_eff) = 0.2909  (§2.7)
Total message energy = Σ (θ_S for each flip)
```

### 6.4 Energy Interpretation

| Text Pattern | Flips | Energy | Interpretation |
|-------------|-------|--------|---------------|
| "Hello world." | 0 | 0.000 | Ground state — natural English |
| "hello world" | 1 | 0.291 | 1 flip (beginning `h` should be UP) |
| "HELLO WORLD" | 9 | 2.618 | High energy — all mid-word letters flipped |
| "NASA launched Apollo 11" | 4 | 1.164 | Acronym + proper noun flips |
| "Stop. Go now." | 0 | 0.000 | Ground state — sentence boundary handled |
| "e = mc2" | 1 | 0.291 | Scientific lowercase at sentence start |

**Key insight**: Proper English sentence case **is** the ground state (minimum energy). Deviations (ALL CAPS, unconventional case) cost energy. The system naturally encodes the information-theoretic content of case choices.

### 6.5 Compact Encoding

The spin channel adds one bit per character:
```
Flip vector: [0, 0, 0, 0, 0, 1, 0, 0, 1, ...]
  0 = observer prediction correct (no flip)
  1 = actual case differs from prediction (flip)

Spin state vector: [+1, -1, -1, -1, -1, +1, -1, ...]
  +1 = |↑⟩ (uppercase)
  -1 = |↓⟩ (lowercase)
   0 = no spin (non-letter)
```

### 6.6 Full Roundtrip

```
Encode:  "Hello World" → Morse + flip vector [0,0,0,0,0,0,0,0,0,0]
Decode:  Morse → "HELLO WORLD" (all caps) → apply spins → "Hello World"
```

The Morse channel carries the character identity. The spin channel carries the case.

---

## 7. Pipeline Summary

```
Input text:  "Hello world."
     │
     ├─── [Spin Observer] ──→ measure per-char spin states
     │                         predict from position + sentence boundary
     │                         compute flip vector + energy
     │
     ├─── [Normalise] ──────→ ASCII uppercase (preserve Greek/math)
     │
     ├─── [Morse Encode] ───→ ".... . .-.. .-.. ---   .-- --- .-. .-.. -.. .-.-.-"
     │
     ├─── [Binary Encode] ──→ per-char: [[0,0,0,0], [0], [0,1,0,0], ...]
     │
     ├─── [D_eff Compute] ──→ per-char: [5.0, 5.0, 5.333, ...]
     │
     ├─── [Token Compute] ──→ per-char FSOT scalar tokens
     │
     └─── [Waveform] ───────→ time-domain signal with FSOT timing

Output:
  EncodedMessage {
    morse_str, binary_sequences, tokens, tokens_normalised,
    spin_observations, spin_flips, spin_energy
  }

Decode path:
  tokens → nearest-match char → uppercase text → apply spin → original case
  morse  → lookup table → uppercase text → apply spin → original case
```

---

## 8. Layer 5 — Punctuation Observer (Reasoning Through Language)

**The problem**: Given a stream of tokenised words, how does the system know where to put commas, periods, question marks, etc.?

**The solution**: A slow-reasoning decision tree that asks TRUE/FALSE at each level, descending until it reaches a terminal decision. This is mathematical reasoning applied to English sentence structure.

### 8.1 The Decision Tree

At every position where punctuation could appear, the observer walks this tree:

```
Level 0: Is there punctuation after this token?
├── FALSE → NONE (no punctuation) ■
└── TRUE
    Level 1: Is it sentence-ending punctuation?
    ├── TRUE
    │   Level 2: Is it a period (declarative)?
    │   ├── TRUE → PERIOD (.) ■
    │   └── FALSE
    │       Level 3: Is it a question mark (interrogative)?
    │       ├── TRUE → QUESTION (?) ■
    │       └── FALSE → EXCLAMATION (!) ■
    └── FALSE (internal punctuation)
        Level 2: Is it a comma?
        ├── TRUE → COMMA (,) ■
        └── FALSE
            Level 3: Is it an apostrophe?
            ├── TRUE → APOSTROPHE (') ■
            └── FALSE
                Level 4: Is it a colon?
                ├── TRUE → COLON (:) ■
                └── FALSE
                    Level 5: Is it a semicolon?
                    ├── TRUE → SEMICOLON (;) ■
                    └── FALSE
                        ... (dash, parens, quotes, etc.)
```

### 8.2 Energy Cost = Depth × Reasoning Unit

```
Misprediction energy = θ_S + depth_reached × (η_eff / MAX_DEPTH)
  θ_S = 0.2909           (structural angle, §2.7 — base flip cost)
  η_eff = 0.4669          (entropy efficiency, §2.5)
  MAX_DEPTH = ⌊27/3⌋ = 9  (from §24 Max_Trits)
  Depth unit = η_eff / 9 = 0.0519
```

**Key insight**: Deeper decisions cost more. A misplaced exclamation mark (depth 3) costs more energy than a missing comma (depth 2). This mirrors human cognition — confusing `!` vs `?` is a deeper error than missing a comma.

### 8.3 FSOT Constants Used

| Constant | Formula | Value | Role |
|----------|---------|-------|------|
| Decision depth cost | η_eff / ⌊27/3⌋ | 0.0519 | Per-level reasoning cost |
| Base misprediction | θ_S | 0.2909 | Minimum error energy |
| Max reasoning depth | ⌊Max_Trits / 3⌋ | 9 | Deepest possible tree |
| Clause boundary | ψ_con | 0.6321 | Stability line |
| Coherence | C_eff | 0.9577 | Sentence coherence threshold |

---

## 9. Layer 6 — Space Observer (Word Boundary Reasoning)

Spacing follows English rules:

| Rule | Prediction | Example |
|------|-----------|---------|
| After word → next word | SPACE | `Hello world` |
| After sentence-ender + more text | SPACE | `Stop. Go` |
| After comma/semicolon/colon | SPACE | `Hello, world` |
| After opening paren | NO SPACE | `(see` |
| Before closing paren | NO SPACE | `done)` |
| Before comma/period | NO SPACE | `world.` |
| Mid-word characters | NO SPACE | `He` (between H and e) |
| End of text | NO SPACE | final character |

Space misprediction energy = **Sync_Decay = 1/φ² = 0.3820** (inter-element gap, §19).

---

## 10. Combined Observer Stack

The three observer channels work in parallel on every character:

```
          ┌────────────────────┐
Input ──→ │ Spin Observer      │──→ case channel    (1 bit/char)
text      │ (|↑⟩ up, |↓⟩ down)│
          ├────────────────────┤
      ──→ │ Punct Observer     │──→ punct channel   (reasoning trace)
          │ (decision tree)    │
          ├────────────────────┤
      ──→ │ Space Observer     │──→ space channel   (1 bit/position)
          │ (boundary rules)   │
          └────────────────────┘

Total structure energy = spin_energy + punct_energy + space_energy
                      + math_energy + math_group_energy
                      + precedence_energy + type_energy
```

### 10.1 Energy Interpretation

| Text | Spin E | Punct E | Space E | Math E | Total E | Interpretation |
|------|--------|---------|---------|--------|---------|----------------|
| `Hello, world. How are you?` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Perfect English — ground state |
| `HELLO WORLD` | 2.62 | 0.00 | 0.00 | 0.00 | 2.62 | Excited case state |
| `2 + 3 = 5` | — | — | — | 0.00 | 0.00 | Well-formed math — ground state |
| `+ 3 = 5` | — | — | — | 0.39 | 0.39 | Missing left operand |
| `(x + y` | — | — | — | 0.96 | 0.96 | Unmatched bracket |

**Minimum energy = well-formed English.** Every deviation from standard orthographic conventions — capitalisation, punctuation placement, spacing — costs energy proportional to how unusual the deviation is. The system literally reasons: "Is this the ground state of English?"

---

## 11. Updated Pipeline

```
Input text:  "Hello, world. How are you?"
     │
     ├─── [Spin Observer] ──→ case spin states + flip vector + energy
     ├─── [Punct Observer] ──→ decision tree traces + energy
     ├─── [Space Observer] ──→ boundary predictions + energy
     ├─── [Math Observer] ───→ grammar analysis + bracket balance + energy
     ├─── [Math Tokenizer] ──→ logical token list (multi-char)
     ├─── [Prec Observer] ──→ PEMDAS precedence check + energy
     ├─── [Type Observer] ──→ semantic domain check + energy
     │
     ├─── [Normalise] ──────→ ASCII uppercase
     ├─── [Morse Encode] ───→ ITU patterns
     ├─── [Binary Encode] ──→ 0/1 sequences
     ├─── [D_eff Compute] ──→ effective dimensionalities
     ├─── [Token Compute] ──→ FSOT scalar tokens
     └─── [Waveform] ───────→ time-domain signal

Output: EncodedMessage {
  morse_str, binary_sequences, tokens, tokens_normalised,
  spin_observations, spin_flips, spin_energy,
  punct_observations, punct_energy,
  space_observations, space_energy,
  math_observations, math_energy,
  math_group_observations, math_group_energy,
  math_tokens,
  precedence_observations, precedence_energy,
  type_observations, type_energy,
  total_structure_energy      ← combined reasoning energy (7 channels)
}
```

---

## 12. Layer 8 — Math Expression Observer

The math observer applies the same TRUE/FALSE decision tree reasoning pattern to mathematical expression grammar that the punctuation observer applies to English sentence structure.

### 12.1 Design Principle

Just as English has grammar rules (sentences end with periods, commas follow clauses), mathematics has grammar rules (binary operators need two operands, brackets must balance, functions need arguments). The math observer walks an expression character-by-character and asks: **"Does this symbol obey the grammar of mathematics?"**

Every violation costs energy. A well-formed expression like `x^2 + y^2 = r^2` sits at the energy minimum (ground state). A malformed expression like `+ 3 = 5` (missing left operand) costs θ_S energy per violation.

### 12.2 MathRole Classification

Each non-space token is classified into one of 13 roles:

| Role | Value | Examples | Description |
|------|-------|----------|-------------|
| OPERAND | 0 | `x`, `2`, `π`, `α` | Numbers, variables, Greek letters |
| BINARY_OP | 1 | `+`, `-`, `*`, `/`, `^`, `×`, `÷` | Operators needing two operands |
| UNARY_PREFIX | 2 | `-` (at start), `√`, `∂` | Operators needing one right operand |
| RELATION | 3 | `=`, `<`, `>`, `≤`, `≥`, `≠` | Comparison/equality symbols |
| OPEN_GROUP | 4 | `(`, `[`, `{` | Opening brackets |
| CLOSE_GROUP | 5 | `)`, `]`, `}` | Closing brackets |
| SEPARATOR | 6 | `,` | Argument/list separators |
| SUBSCRIPT | 7 | `_` | Subscript marker |
| SUPERSCRIPT | 8 | `^` | Exponentiation (also BINARY_OP) |
| FUNCTION | 9 | `∫`, `Σ`, `Π`, `∂`, `√`, `∇` | Mathematical functions needing arguments |
| FACTORIAL | 10 | `!` | Postfix operator |
| SPACE | 11 | ` ` | Whitespace (skipped) |
| UNKNOWN | 12 | anything else | Unrecognised tokens |

**Context-sensitive classification**: The minus sign `-` is classified as UNARY_PREFIX if it appears at the start of an expression, after an operator, or after an opening bracket. Otherwise it's BINARY_OP.

### 12.3 Grammar Decision Trees

Each role has a decision tree that validates it in context:

#### OPERAND
```
L0: Token classified as OPERAND? → TRUE
  L1: Is operand in a valid position? → TRUE/FALSE
      (Consecutive operands without an operator between them → FALSE)
```

#### BINARY_OP
```
L0: Token classified as BINARY_OP? → TRUE
  L1: Does binary operator have a left operand? → TRUE/FALSE
    L2: Does binary operator have a right operand? → TRUE/FALSE
```

#### UNARY_PREFIX
```
L0: Token classified as UNARY_PREFIX? → TRUE
  L1: Does unary prefix have a right operand? → TRUE/FALSE
```

#### RELATION
```
L0: Token classified as RELATION? → TRUE
  L1: Does relation have a left-hand side? → TRUE/FALSE
    L2: Does relation have a right-hand side? → TRUE/FALSE
```

#### OPEN_GROUP / CLOSE_GROUP
```
L0: Token classified as OPEN/CLOSE_GROUP? → TRUE
  L1: Is opening/closing group in a valid position? → TRUE/FALSE
```

#### FUNCTION
```
L0: Token classified as FUNCTION? → TRUE
  L1: Does function have an argument (or expression following)? → TRUE/FALSE
```

#### FACTORIAL
```
L0: Token classified as FACTORIAL? → TRUE
  L1: Does factorial have a left operand? → TRUE/FALSE
```

### 12.4 Bracket Balance (Grouping Observer)

A separate pass checks that all brackets are properly matched using a stack:

1. Walk left to right
2. Push each opening bracket `(`, `[`, `{` onto the stack
3. On closing bracket, pop and check the pair matches
4. Any unmatched bracket costs **C_eff × P_var = 0.9577** energy (the collapse threshold)

This is more expensive than a single grammar violation (θ_S = 0.2909) because unmatched brackets corrupt the entire expression structure.

### 12.5 Energy Model

```
Grammar violation energy:  θ_S + depth × (η_eff / 9)
  where depth = how deep in the decision tree the failure occurs
  
  Base cost:     θ_S     = 0.2909  (per violation)
  Depth penalty: η_eff/9 = 0.0519  (per level)

Bracket imbalance energy:  C_eff × P_var = 0.9577  (per unmatched bracket)

Total math energy = Σ(grammar violations) + Σ(bracket imbalances)
```

### 12.6 Examples

| Expression | Grammar E | Group E | Total | Verdict |
|-----------|-----------|---------|-------|---------|
| `2 + 3 = 5` | 0.00 | 0.00 | 0.00 | ✓ Ground state |
| `x^2 + y^2 = r^2` | 0.00 | 0.00 | 0.00 | ✓ Ground state |
| `a * b + c` | 0.00 | 0.00 | 0.00 | ✓ Ground state |
| `+ 3 = 5` | 0.39 | 0.00 | 0.39 | ✗ No left operand for `+` |
| `x ^ ` | 0.45 | 0.00 | 0.45 | ✗ No right operand for `^` |
| `(x + y` | 0.00 | 0.96 | 0.96 | ✗ Unmatched `(` |

### 12.7 Complete Observer Stack

```
Input ──→ Spin Observer (case)
     ──→ Punct Observer (English grammar)
     ──→ Space Observer (word boundaries)
     ──→ Math Observer (expression grammar)
     ──→ Math Group Observer (bracket balance)
     
Total structure energy = spin + punct + space + math_grammar + math_grouping
```

The system now reasons about **both natural language and mathematical notation** — all from the same five seeds, same energy model, same TRUE/FALSE decision tree pattern.

---

## 12.8 Layer 9 — Math Expression Tokenizer

The character-level grammar observer processes one character at a time (matching the Morse encoding granularity). The tokenizer adds a higher-level analysis layer that groups characters into **logical mathematical tokens**:

### Token Types

| Subtype | Example | Grouping Rule |
|---------|---------|---------------|
| `number` | `3.14`, `100`, `42` | Consecutive digits + optional decimal point |
| `function_name` | `sin`, `cos`, `log`, `exp`, `ln` | Known function names (30+ recognized) |
| `function_letter` | `f(x)`, `g(y)` | Single letters f, g, h followed by `(` |
| `function_symbol` | `∫`, `Σ`, `Π`, `√`, `∂`, `∇` | Unicode function symbols |
| `variable` | `x`, `y`, `z` | Single ASCII letters (not function names) |
| `constant` | `π`, `φ`, `γ` | Greek letter constants |
| `operator` | `+`, `*`, `/` | Binary operators |
| `unary_minus` | `-x`, `(-3)` | Context-sensitive minus as unary |

### Multi-Character Recognition

```
"sin(x)"    → [sin:FUNCTION, (:OPEN, x:OPERAND, ):CLOSE]     (4 logical tokens)
"3.14"      → [3.14:OPERAND]                                   (1 logical token)
"xy"        → [x:OPERAND, y:OPERAND]                           (2 variables, implied ×)
"f(x, y)"   → [f:FUNCTION, (:OPEN, x:OPERAND, ,:SEP, y:OPERAND, ):CLOSE]
```

The tokenizer enables the next two observer layers (precedence and type) which require understanding token boundaries.

---

## 12.9 Layer 10 — Operator Precedence Observer (PEMDAS)

### Design

Mathematical expressions have implicit evaluation order determined by operator precedence (PEMDAS/BODMAS):

| Level | Name | Operators | Binds |
|-------|------|-----------|-------|
| 5 | POSTFIX | `!` | Tightest |
| 4 | UNARY | `-x`, `√`, `∂`, `∇` | ↑ |
| 3 | POWER | `^` | ↑ |
| 2 | MULTIPLY | `*`, `×`, `/`, `÷` | ↑ |
| 1 | ADDITION | `+`, `-` | ↑ |
| 0 | RELATION | `=`, `<`, `>`, `≤`, `≥`, `≠` | Loosest |

### Ambiguity Detection

Adjacent operators of **different precedence levels** that share the same parenthesization depth are flagged as **precedence-ambiguous**:

| Expression | Ambiguous? | Why |
|-----------|------------|-----|
| `2 + 3 * 4` | **YES** | ADDITION adjacent to MULTIPLY, no parens |
| `2 + (3 * 4)` | NO | Parentheses resolve evaluation order |
| `a + b - c` | NO | Same precedence (ADDITION), left-to-right |
| `x^2 + y^2` | **YES** | POWER adjacent to ADDITION |
| `(x^2) + (y^2)` | NO | Parenthesized |

### Energy

```
Precedence ambiguity energy: SYNC_DECAY = 1/φ² = 0.3820 per ambiguous site
```

SYNC_DECAY (§19, inter-element gap) is the natural choice: precedence ambiguity is a "gap" in explicit structure — the reader must mentally insert parentheses.

---

## 12.10 Layer 11 — Type / Domain Observer

### Design

Beyond syntax, mathematical expressions have **semantic type constraints**. The type observer performs basic domain analysis:

### Type Classification

| MathType | Subtype | Examples | Description |
|----------|---------|----------|-------------|
| NUMERIC | number | `1`, `3.14`, `100` | Literal numbers |
| VARIABLE | variable | `x`, `y`, `z` | Unknown quantities |
| CONSTANT | constant | `π`, `e`, `φ` | Known mathematical constants |
| FUNCTION | function_name/letter/symbol | `sin`, `f`, `∫` | Functions (not their results) |
| EXPRESSION | — | `(x+1)` | Result of an operation |

### Domain Checks

1. **Function arguments**: Functions must be followed by arguments (open-group or operand)
2. **Factorial domain**: `n!` requires non-negative integer *n* — `(-3)!` is flagged
3. **Exponent domain**: `x^` must have a power expression after it

### Energy

```
Type inconsistency energy: θ_S = 0.2909 per inconsistency
```

Same cost as a grammar violation — a type error is structurally equivalent to a misplaced token.

---

## 12.11 Complete Observer Stack (Updated)

```
Input ──→ Spin Observer (case)              → spin channel
     ──→ Punct Observer (English grammar)   → punct channel
     ──→ Space Observer (word boundaries)   → space channel
     ──→ Math Grammar Observer (char-level) → grammar channel
     ──→ Math Group Observer (brackets)     → grouping channel
     ──→ Math Tokenizer (multi-char)        → token list
     ──→ Precedence Observer (PEMDAS)       → precedence channel
     ──→ Type Observer (semantic domain)    → type channel
     
Total structure energy = spin + punct + space
                       + math_grammar + math_grouping
                       + precedence + type
```

**7 energy channels**, all from the same 5 seeds.

---

## 13. What This Means

This system demonstrates that **natural language text and mathematical expressions can be fully encoded and reasoned about using only five mathematical constants**:

1. **Character identity**: Morse dot/dash → binary → FSOT token (99 unique scalars)
2. **Character case**: Quantum spin observer — positional rules (1 bit per char)
3. **Punctuation**: Slow-reasoning decision tree — TRUE/FALSE at each level
4. **Spacing**: Word boundary prediction — English orthographic rules
5. **Math grammar**: Expression structure observer — operator/operand rules
6. **Bracket balance**: Stack-based grouping with collapse threshold energy
7. **Multi-char tokenization**: Numbers, named functions, implied functions
8. **Operator precedence**: PEMDAS analysis — ambiguity detection
9. **Type/domain**: Semantic consistency — function arguments, factorial domain
10. **Signal timing**: All durations/amplitudes from seed-derived ratios
11. **Zero free parameters**: No tuning, no training, no learned weights

### Coverage of Math vs English Contrast

| Aspect | Math Coverage | English Coverage |
|--------|-------------|-----------------|
| Foundational elements | 99-char closed set, operators, Greek, functions | Same 99-char set, spin for case |
| Core rules | Prescriptive grammar (ERR on violation) | Descriptive energy (cost on deviation) |
| Structure/syntax | PEMDAS precedence + bracket nesting | Phrase structure + decision trees |
| Semantics/meaning | Type observer (function domain, factorial) | Pragmatic energy (punct context) |
| Precision vs ambiguity | Zero tolerance (grammar) + ambiguity detector (precedence) | High tolerance (energy, not rejection) |
| Expressiveness | Subscript, superscript, functions, factorial | Case emphasis, exclamation depth |
| Universality | Culture-independent (5 seeds, zero params) | Same seeds, usage-dependent energy |
| Evolution/change | Extend via function/operator sets | Extend via character table |
| Observer dependence | 1 context-sensitive case (minus sign) | 4 stacked observers (spin, punct, space, math) |
| Verification | Formal: TRUE/FALSE proof at each node | Social: energy measures surprise, not rejection |

The total structure energy is a mathematical measure of how "standard" a piece of text or expression is. Well-formed English and well-formed mathematics both sit at the energy minimum. This is reasoning through math — 7 independent channels, each asking different questions about the same input, all deriving their costs from the same five seeds.

**Next**: Extend reasoning to code syntax, musical notation, and other structured symbol systems — all from the same five seeds.

---

*FSOT 3.0 — fsot_morse.py — April 2026*
