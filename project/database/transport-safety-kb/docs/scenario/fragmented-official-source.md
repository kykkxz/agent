# Scenario: Multiple official documents in one archived source

- Given: One official attachment containing several plans with exact standalone title lines
- When: The pipeline normalizes the fetched source
- Then: It emits one non-overlapping standard-document text range per configured title while retaining one raw asset

## Test Steps

- Case 1 (happy path): split three exact standalone titles into three non-overlapping fragments
- Case 2 (edge case): return the original title and text when no split titles are configured

## Status

- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
