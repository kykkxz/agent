# Scenario: SQLite rebuild releases file handles

- Given: a writable temporary directory and an empty valid collection run
- When: the SQLite database is rebuilt and verified
- Then: the database can be rebuilt again or renamed immediately

## Test Steps

- Case 1 (happy path): rebuild the same database path twice.
- Case 2 (edge case): verify the database and immediately rename it.

## Status

- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
