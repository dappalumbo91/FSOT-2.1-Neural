# Transfer test (teach A → probe paraphrase B)

OK: **True**  pairs=3  mean_hit=**1.000**  mean_curiosity=**1.000**

| Teach title | probes | hits | hit_rate | curiosity |
|-------------|-------:|-----:|---------:|----------:|
| FSOT Thesis | 8 | 8 | 1.000 | 1.000 |
| FSOT PHOTONIC V2 THESIS | 8 | 8 | 1.000 | 1.000 |
| README | 6 | 6 | 1.000 | 1.000 |

## Notes

- Transfer = teach A, probe without title-token shortcuts.
- Success is content/mechanism recall, not string match to title.
