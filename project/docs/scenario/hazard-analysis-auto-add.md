# Scenario: 图片分析结果自动进入隐患台账

- Given: 已登录用户上传一张可识别的现场图片
- When: 视觉模型返回一项或多项结构化隐患
- Then: 系统创建一条关联原图和批注图的待派单隐患记录，并把记录摘要放入分析响应

## Test Steps

- Case 1 (happy path): 模型返回两项隐患，台账总数增加一条，详情包含两项名称和两张关联图片。
- Case 2 (edge case): 模型返回零项隐患，台账数量保持不变，响应不包含新记录。

## Status

- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run full backend suite and confirm 12 tests still pass after refactor
