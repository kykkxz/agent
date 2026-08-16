# Scenario: Authority-aware search ranking

- Given: A knowledge base containing laws, regulations, enterprise systems, and accident reports
- When: A fixed question clearly targets a statutory responsibility
- Then: The matching core law or construction-safety regulation remains in the Top 5 despite larger lower-scope corpora

## Test Steps

- Case 1 (general safety law): prefer the Safety Production Law for special-operation qualification
- Case 2 (construction regulation): prefer the Construction Safety Regulation for supervision duties

## Status

- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
