# Taught mathematical rules
- **add_comm**: `a + b = b + a` — Order of addends does not change sum
- **add_zero**: `a + 0 = a` — Adding zero leaves a number unchanged
- **add_combine**: `total = a + b + …` — Together / altogether / in all → add
- **sub_remove**: `left = total − used` — Left / remain / rest → subtract
- **sub_diff**: `diff = |a − b|` — How many more / less → difference
- **mul_groups**: `total = n × size` — Each / every / times → multiply
- **mul_rate**: `amount = rate × time` — Per hour/day with duration → multiply (convert units)
- **div_share**: `each = total ÷ n` — Split equally / per person → divide
- **div_rate**: `time = amount ÷ rate` — How long at constant rate → divide
- **half**: `half(n) = n / 2` — Half as many / half of → divide by 2
- **double**: `double(n) = n × 2` — Twice / double → multiply by 2
- **percent**: `p% of x = (p/100) × x` — Percent of a quantity
- **remain_after**: `left = start − a − b` — Start, use some, use more, what left
- **compose**: `use prior result in next rule` — Multi-hop: output of step k is input to step k+1

# Language → strategy maps
- `altogether means add` → **add**
- `left means subtract from total` → **sub**
- `more/less means difference` → **sub**
- `each/every often means multiply groups` → **mul**
- `times as many means multiply` → **mul**
- `half means divide by two` → **half**
- `twice means multiply by two` → **double**
- `split equally means divide` → **div**
- `percent of means times p over 100` → **percent**
- `per unit time is a rate` → **rate**
- `remainder after uses is subtract chain` → **sub_chain**
