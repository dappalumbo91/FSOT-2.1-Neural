# Visual individual identity

OK: **True**  tutor_ablated=**True**

- **VIU re-ID top1=** 0.689 (chance≈0.152)
- unique-name top1=**0.333** (trials=6)
- n_viu=**33** named=**26** heldout=**45**

Primary metric is visual re-identification of **individuals**, not global name bags.

## Notes

- Identity unit = visual individual (VIU), not the name string.
- Names bind to VIUs by co-occurrence; same name may label many VIUs.
- Tutor-ablated query: pixels → nearest VIU.
- films=['Resident Evil 1 2002.mp4', 'Resident Evil 2 2004 Apocalypse.mp4', 'Resident Evil 3 2007 Extinction.mp4', 'Resident Evil 4 2010 Afterlife.mp4', 'Resident Evil 5 2012 Retribution.mp4']
- Resident Evil 1 2002.mp4: frames=24 binds=13 viu=3 held=9
- Resident Evil 2 2004 Apocalypse.mp4: frames=24 binds=14 viu=7 held=9
- Resident Evil 3 2007 Extinction.mp4: frames=24 binds=9 viu=9 held=9
- Resident Evil 4 2010 Afterlife.mp4: frames=24 binds=18 viu=6 held=9
- Resident Evil 5 2012 Retribution.mp4: frames=24 binds=16 viu=8 held=9
- viu_reid=0.689 chance≈0.152 unique_name=0.333 trials_name=6 heldout=45
- Primary success = re-identify the same visual individual, not bag-average all people who share a string name.
