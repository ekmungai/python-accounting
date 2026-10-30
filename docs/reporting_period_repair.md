## Repairing Reporting Periods
Before the fix described in the CHANGELOG, an Entity whose year does not start in January had its next Reporting Period opened from January until the month before `year_start`. Its running period moved to Adjusting, and Balances saved in those months were attached a year late. Upgrading stops this happening, but does not change the data it left behind, so affected Entities should be repaired straight after upgrading. Until they are, sales can be rejected and default dated reports can fail.

`find` only lists what needs repairing for the session's Entity. `repair` applies it in one database transaction, leaving anything that involves a closed period or has no period to move to.

```python
from python_accounting.utils.reporting_period_repair import find, repair

findings = find(session)

for finding in findings.periods:
    print(finding.period, finding.previous, finding.blocked)

for finding in findings.balances:
    print(finding.balance, finding.period, finding.target, finding.blocked)

repaired = repair(session, findings) # Run this once the findings have been reviewed
```

Review the findings before repairing. For a period that has already begun, Balances are matched on `created_at`, which holds the time the application started rather than the time they were saved, so some may be missed or listed by mistake.
