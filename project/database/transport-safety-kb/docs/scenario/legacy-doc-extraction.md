# Scenario: Legacy Word document extraction

- Given: An official OLE `.doc` source and an available Word COM automation interface
- When: The extraction layer receives the original bytes
- Then: It returns normalized document text and cleans up Word and temporary files on every path

## Test Steps

- Case 1 (happy path): recognize an OLE header and extract text through the Word COM adapter
- Case 2 (edge case): close Word and remove the temporary file when Word cannot open the document

## Status

- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor
