# Scenario: Recoverable official catalog discovery

- Given: A configured official accident-report index and an optional existing checkpoint
- When: The discovery command runs for one source or finalizes accumulated checkpoints
- Then: It writes accepted candidates incrementally, skips already recorded URLs, and emits a deterministic catalog without opening every detail page

## Test Steps

- Case 1 (happy path): select one source and limit the batch to one candidate
- Case 2 (resume): rerun against a checkpoint and do not duplicate the existing candidate
- Case 3 (finalize): merge checkpoint files into a deterministic generated catalog

## Status

- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
