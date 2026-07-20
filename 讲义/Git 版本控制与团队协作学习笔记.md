# Git 版本控制与团队协作完整讲义

## 前言

从零讲解 **Git 本地版本管理、分支原理、远程仓库关联、Pull/Push 核心机制、企业标准开发流程**。摒弃晦涩理论，全部通俗化解释 \+ 可直接复制的实操命令，适合课堂教学、课后实训、企业开发入门。

**学习目标**

- 理解 Git 工作区、暂存区、本地仓库、远程仓库四层结构

- 彻底搞懂分支、版本、快照的核心原理

- 掌握本地代码版本保存、回退、分支开发

- 掌握 0 拉取远程代码、首次推送代码、同步代码

- 掌握企业安全开发规范（杜绝代码覆盖、版本丢失）

# 第一章：核心概念通俗精讲（必考/必会）

## 1\.1 Git 四大核心区域（底层原理）

Git 不是简单的“上传下载工具”，是**本地快照式版本管理系统**，分为四层：

1. **工作区（Working Directory）**
   你电脑肉眼看到的文件夹、改代码、新建文件的地方，是「临时修改区」，无版本记录。

2. **暂存区（Stage/Index）**
   `git add` 后的区域，临时登记修改，告诉 Git：这些文件准备要存为新版本。
   **特点：只是登记，还不是正式版本。**

3. **本地仓库（Local Repo）**
   `git commit` 后生成**永久版本快照**，保存在本地 `.git` 隐藏文件夹。
   **只有 commit 才算一个版本，可回退、可追溯、可分支切换。**

4. **远程仓库（Remote Repo）**
   GitHub / Gitee / 公司 GitLab 内网仓库，存放团队统一的线上版本，用于多人共享、代码备份。

## 1\.2 版本（Commit）是什么？

每一次 `commit` = **一次完整项目快照**。

- 每次版本都会生成唯一哈希 ID（版本号）

- 所有历史版本永久保存，不会被新代码覆盖

- 可以任意切换、回退、对比任意历史版本

❌ 误区：Push 新版本会覆盖旧代码
✅ 真相：Push 是**追加新版本**，历史版本全部保留

## 1\.3 分支（Branch）核心原理

分支 = **独立的版本开发流水线**

### 1\.3\.1 主干分支 main

线上稳定分支，存放正式、可运行代码，**禁止直接在 main 开发**。

### 1\.3\.2 开发分支（feature/xxx、dev）

所有新功能、修改、bug 修复，全部新建分支开发：

- 分支之间代码完全隔离

- 改坏了直接废弃分支，不影响主线

- 开发完成后合并到 main 主线

通俗比喻：
`main` = 成品主视频
`新分支` = 剪辑草稿工程
草稿随便改、随便删，不影响成品，定稿后再合并。

## 1\.4 Origin 远程别名

`origin` 是 Git 默认给「远程仓库地址」起的别名。

- `origin/main`：远程线上主干分支

- `main`：你本地的主干分支

## 1\.5 Pull 与 Push 终极通俗解释

### Pull（拉取）：远程 → 本地

下载团队/线上最新代码，同步到自己电脑，**防止自己代码老旧、覆盖别人修改**。

### Push（推送）：本地 → 远程

把自己本地的新版本，上传到线上仓库，给团队共享、云端备份。

# 第二章：本地 Git 全套操作（仅本地，不碰远程）

## 2\.1 查看状态

```Plain
git status
```

识别三种状态：

- Untracked：新增未追踪文件

- Modified：文件已修改未暂存

- Changes to be committed：已暂存，待提交版本

## 2\.2 暂存修改（add）

```Plain
# 所有文件暂存
git add .

# 单个文件暂存
git add 文件名
```

## 2\.3 生成本地永久版本（commit）

```Plain
git commit -m "本次修改说明"
```

关键点：**只有 commit 才是真正保存版本，add 只是临时登记**

## 2\.4 查看本地所有版本

```Plain
git log --oneline
```

## 2\.5 切换历史版本（临时查看）

```Plain
git checkout 版本哈希号

# 切回最新主线
git checkout main
```

## 2\.6 版本回退（教学常用）

```Plain
# 软回退：保留代码，只撤销版本
git reset --soft 哈希

# 硬回退：彻底删除后续版本（谨慎使用）
git reset --hard 哈希
```

# 第三章：分支完整操作（企业标准开发模式）

**企业铁律：禁止直接在 main 分支开发**

## 3\.1 查看分支

```Plain
# 查看本地分支
git branch

# 查看所有分支（本地+远程）
git branch -a
```

## 3\.2 创建并切换新分支

```Plain
# 新建并进入分支（二选一）
git checkout -b feature/demo
git switch -b feature/demo
```

## 3\.3 分支开发、提交、推送

```Plain
git add .
git commit -m "新功能开发完成"
git push origin feature/demo
```

## 3\.4 分支合并到主线

```Plain
# ====================== 重要区分 ======================
# 1. 【单人学习/个人仓库】可用：本地合并后推送main
# 切回主线
git checkout main
# 拉取最新主线
git pull origin main
# 合并开发分支
git merge feature/demo
# 个人仓库可推送主线（仅学习使用）
git push origin main

# 2. 【企业团队/多人协作】严禁直接push main
# 正确操作：仅推送个人开发分支，通过PR/MR审核合并主线
git push origin feature/demo
# 后续由管理员审核代码，合并入main主线，开发者无需操作main
```

# 第四章：远程仓库关联原理（GitHub / 公司GitLab通用）

## 4\.1 查看当前远程绑定

```Plain
git remote -v
```

## 4\.2 更换/绑定远程仓库

```Plain
# 删除旧远程
git remote remove origin

# 绑定新远程（公司内网 / GitHub）
git remote add origin 远程仓库地址.git
```

## 4\.3 关键区别：外网GitHub vs 公司内网Git

| 场景   | GitHub 外网仓库                  | 公司内网 GitLab             |
| ---- | ---------------------------- | ----------------------- |
| 网络   | 需要VPN/代理                     | **必须关闭代理，直连内网**         |
| 地址   | https://github\.com/xxx\.git | http://内网IP/项目组/项目\.git |
| 账号验证 | PAT令牌                        | 工号/公司邮箱/内网令牌            |
| 操作命令 | 完全一致                         | 完全一致                    |

# 第五章：从零完整实操流程

## 5\.1 场景一：从远程仓库【首次拉取代码】

适用于：新项目、克隆公司/学校代码

```Plain
# 1. 进入存放代码的文件夹
cd D:\研发\project

# 2. 克隆远程完整仓库（自带所有版本、.git仓库）
git clone 远程仓库地址.git

# 3. 进入项目目录
cd 项目文件夹

# 4. 自动创建本地main分支并关联远程
git checkout main

# 5. 同步线上最新代码
git pull origin main
```

## 5\.2 场景二：本地新项目【首次推送代码到远程】

适用于：本地新建项目，第一次上传 GitHub/公司仓库

```Plain
# 1. 初始化本地git仓库
git init

# 2. 暂存所有文件
git add .

# 3. 首次本地提交
git commit -m "项目初始化提交"

# 4. 绑定远程仓库
git remote add origin 远程仓库地址.git

# 5. 拉取远程（防止冲突）
git pull origin main --allow-unrelated-histories

# 6. 推送到远程主线
git push origin main
```

## 5\.3 场景三：日常开发标准流程（企业通用）

**最安全、无覆盖、无丢失版本**

```Plain
# 企业标准安全开发流程（多人协作通用，课堂重点）
# 1. 开发前先同步线上main最新代码（保证本地基线最新）
git pull origin main

# 2. 新建独立功能分支（核心：绝不直接在main开发）
git checkout -b feature/new_func

# 3. 本地完成代码修改、功能开发
# 4. 暂存并生成本地版本
git add .
git commit -m "完成新功能xxx"

# 5. 再次同步主线代码，提前规避线上冲突
git pull origin main

# 6. 解决冲突后再次提交（无冲突可省略）
git add .
git commit -m "合并主线代码，解决开发冲突"

# 7. 仅推送【个人开发分支】到远程，严禁push main
git push origin feature/new_func

# 8. 最终合并主线（开发者无需操作git）
# 登录Git平台，提交PR/GitLab MR合并申请
# 管理员审核代码通过后，自动合并入main主线
```

# 第六章：常见误区与安全规范

## 6\.1 三大致命误区

- ❌ 直接在 main 分支开发、push

- ❌ 不 pull 直接 push，极易造成代码冲突覆盖

- ❌ 使用 `git push -f` 强制推送（删除团队版本）

## 6\.2 核心安全结论（单人 vs 团队 严格区分）

- 版本机制：普通 `git push` 只会**追加新版本**，不会覆盖、删除云端历史版本，所有commit永久留存，可随时回溯

- 开发规范：**单人学习场景**可直接push main；**企业多人协作场景**严禁直接push、修改main主线

- 协作核心：所有人独立分支开发、本地解冲突、推送个人分支，通过PR/MR审核合并主线，彻底杜绝代码覆盖风险

- 网络规则：外网GitHub需要配置VPN代理，公司内网Git必须关闭代理，否则无法连接仓库

- 高危禁令：任何场景禁止使用 `git push -f` 强制推送，会销毁团队线上版本记录

# 第七章：高频速查命令表（考试/实训速记）

| 功能       | 命令                       |
| -------- | ------------------------ |
| 查看文件变更状态 | git status               |
| 暂存所有修改   | git add \.               |
| 生成本地版本   | git commit \-m "备注"      |
| 查看本地版本列表 | git log \-\-oneline      |
| 新建切换分支   | git checkout \-b 分支名     |
| 关联远程仓库   | git remote add origin 地址 |
| 拉取远程代码   | git pull origin main     |
| 推送代码到远程  | git push origin 分支名      |
| 查看远程绑定   | git remote \-v           |

# 第八章：多人团队协作终极标准流程

## 8\.1 团队协作核心规则

在企业/多人项目中，**所有人绝对禁止直接操作、推送、修改 main 主线**。

**唯一正确开发模型：**

1. **main**：公共稳定基线，只读、不开发、不推送

2. **每位开发者独立新建个人功能分支**开发代码

3. **所有冲突在自己本地分支解决**，绝不把冲突推上云端

4. **只推送个人分支**

5. **合并进主线必须走平台 PR/MR 审核**

## 8\.2 双人协作场景模拟（A同学、B同学）

### 场景设定

- 公共远程仓库：main（稳定版）

- A同学分支：feature/A\_dev

- B同学分支：feature/B\_dev

## 8\.3 每位开发者【每日统一开发流程】（最终标准答案）

```Plain
# 步骤1：开发开始前，先拉取远程main最新代码（保证本地基线最新）
git pull origin main

# 步骤2：自己在个人分支写代码、改功能
# 步骤3：写完后，暂存+本地提交（只存自己分支）
git add .
git commit -m "完成xxx功能/修复xxxbug"

# 步骤4：再次拉取主线最新代码（防止队友已经更新了主线）
# 重点：冲突全部在自己本地解决，不上传脏代码
git pull origin main

# 若出现冲突：手动修改文件保留正确代码 → 再次提交
git add .
git commit -m "合并主线，解决多人开发冲突"

# 步骤5：只推送【自己的分支】，严禁 push main！
git push origin feature/你的分支名

# 步骤6：登录 Git 平台，提交 PR/GitLab MR 合并申请
# 【下方附带完整网页点击操作步骤】

# 步骤7：老师/管理员审核通过后，自动合并入 main 主线

```

## 8\.6 网页端 PR（GitHub）/ MR（公司GitLab）完整点击步骤

**前置条件：已经把自己的分支 push 到远程**

### 一、GitHub 提交 PR（Pull Request）步骤

1. 打开你的 GitHub 仓库主页

2. 推送完分支后，页面顶部会自动弹出蓝色提示：**Compare \& pull request**，直接点击

3. 若无弹窗：点击顶部 **Pull requests** → **New pull request**

4. 选择分支对比：
   **base（目标分支）**：main（主线，要合并进去的稳定分支）

5. **compare（源分支）**：你自己的 feature/xxx 开发分支

6. 填写 PR 信息：
   标题：一句话说明本次修改（例：新增用户登录功能、修复爬虫超时bug）

7. 描述：详细写改了哪些文件、实现了什么功能、测试情况

8. 点击 **Create pull request** 提交成功

9. 等待管理员/组长审核，审核通过后点击 **Merge** 合并进主线

10. 合并完成后：线上 main 自动更新，所有人下次开发 pull 即可同步你的代码

### 二、公司 GitLab 提交 MR（Merge Request）步骤

1. 打开公司内网 GitLab 项目仓库

2. 推送分支后，页面自动提示：**Create merge request**，点击进入

3. 若无提示：左侧菜单 **Merge Requests** → **New merge request**

4. 选择分支：
   **目标分支（Target branch）**：main

5. **源分支（Source branch）**：你的个人开发分支

6. 填写标题、修改说明，可选择指派审核人

7. 点击 **Create merge request**

8. 管理员审核代码无误后，点击**Merge** 完成主线合并

## 8\.7 核心考试考点（必背）

- **PR/MR 作用**：代码审核、团队协作、保护主线不被乱改

- **开发者权限**：只能提交合并申请，不能自己合并主线

- **合并唯一入口**：网页端审核合并，禁止本地 push main

- **冲突原则**：所有冲突必须在自己分支本地解决，不提交冲突代码到线上

## 8\.4 为什么必须这样做？（彻底解答你的安全疑问）

### 1\. 不会覆盖队友代码

所有新代码、冲突合并，全部在**本地个人分支**完成，不会直接改动线上主线。

### 2\. 主线永远干净稳定

main 只留存审核通过、可运行的代码，不会存在开发一半、报错、冲突代码。

### 3\. 所有版本永久保留、可回溯

每次合并都是**追加新版本**，不会删除、覆盖历史版本。

## 8\.5 教学终极总结（一句话记住全套 Git）

**主线只读、分支开发、本地同步、本地解冲突、分支推送、审核合并主线。**

# 第九章：常见报错快速排错（实训必备）

## 9\.1 GitHub 443 连接超时

原因：开启VPN后Git未配置代理

解决（你的VPN端口7897）：

```Plain
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

## 9\.2 公司内网Git连不上

原因：开了外网代理，内网被拦截

```Plain
git config --global --unset http.proxy
git config --global --unset https.proxy
```

## 9\.3 提示：remote contains work you do not have

原因：线上有新版本，你没pull就想push

解决：先 pull 再 push，禁止强推。

## 9\.4 分离头指针、git log 只能看到一个版本

原因：手动切换到了旧版本快照

解决：

```Plain
git checkout main
```

8.9 GitHub PR 页面实操细节、三种合并模式、变基优化提交线
一、推送分支后网页发起 PR 完整操作步骤
终端执行 git push origin dev_max 推送个人开发分支，刷新 GitHub 仓库首页
顶部弹窗快速入口：Compare & pull request；无弹窗则点击顶部导航栏 Pull requests → 右上角 New pull request
分支选择规范（不能选反）
base（目标分支）：main（稳定主线，代码要合并进这里）
compare（源分支）：dev_max（自己开发的功能分支）
核对分支改动差异（两种查看方式）
网页端：切换到 Files changed 标签，可视化查看增删代码
终端命令（快速查看改动文件列表）
powershell
git diff dev_max main --name-only

冲突状态识别
绿色提示 No conflicts with base branch：无代码冲突，平台可自动合并
红色冲突标记：存在多人代码覆盖冲突，必须回到本地分支手动解决后重新推送
二、Merge pull request 三种合并模式详解（考试重点）
点击绿色 Merge pull request 下拉框，提供 3 种合并方案，适用场景区分：
Create a merge commit（默认模式，多人团队推荐）
额外生成一条独立合并提交记录，完整保留主线、开发分支全部历史提交，能清晰追溯每一次分支合并动作，适合企业多人协作项目。
Squash and merge（单人 / 个人练习推荐）
将当前开发分支所有多条提交，压缩合并为单一条干净提交并入主线，主线版本历史简洁清爽，无零散测试提交，适合学生实训、个人仓库。
Rebase and merge（追求线性提交线）
以主线最新代码为基底重放开发分支提交，不产生额外合并节点，整个仓库提交记录为一条直线，无分叉。
三、优化：避免 git pull 产生多余合并提交（变基拉取代码）
问题说明
常规 git pull origin main 拉取主线更新时，若本地分支与主线存在版本差，会自动生成一条「合并提交记录」，导致提交线分叉杂乱。
解决方案：带变基参数拉取代码（保持线性干净历史）
powershell

# 拉取主线代码，使用变基替代自动合并

git pull origin main --rebase

实操场景：在你的开发分支 dev_max 同步主线代码时，统一使用该命令，减少多余合并节点。
四、单人仓库实操建议
提交 PR 后下拉合并按钮，选择 Squash and merge，压缩多条测试提交为一条主线记录；
合并完成后，页面会出现 Delete branch 按钮，测试功能验证无误后，可直接删除废弃开发分支 dev_max，保持仓库分支整洁；
合并完成后刷新仓库主页，main 分支会同步更新你的全部代码。
五、页面校验标识识别（快速判断能否合并）
Ready to merge：仓库规则、代码冲突校验全部通过，满足合并条件；
Files changed X：本次 PR 一共修改 X 个文件，可核对本地开发改动是否匹配；
源分支 / 目标分支双向核对：确认源分支是自己的开发分支、目标分支固定为main，防止分支合并方向颠倒。

# GitHub Rulesets 主线分支保护配置讲解（写入讲义）

## 一、页面功能说明

当前页面为仓库 `Settings → Rules → Rulesets → New branch ruleset`，是GitHub新版**分支规则集**配置页面，用于给 `main` 主线添加强制保护，实现「禁止直接push主线、必须走PR审核合并」的企业规范，替代旧版单独的分支保护入口。

### 页面核心字段翻译与作用

1. **Ruleset Name *（规则集名称）**
    自定义命名，推荐填写 `Main-Branch-Protect`，方便识别该规则用于保护主线。
2. **Enforcement status（生效状态）**
   - `Disabled`：规则不生效（当前默认状态）
   - `Active`：启用规则，所有协作者必须遵守保护限制
3. **Bypass list（豁免名单）**
    添加用户/团队后，该对象可绕过分支保护规则；多人协作课堂/企业场景**建议留空**，所有人统一受约束。
4. **Target branches（目标分支）**
    指定该规则生效的分支，填写 `main`，仅对主线启用保护。

---

## 二、完整配置步骤（实训操作流程）

1. **填写规则名称**
    在 `Ruleset Name` 输入框填入 `Main-Branch-Protect`。
2. **设置生效状态**
    将 `Enforcement status` 下拉从 `Disabled` 改为 `Active`。
3. **指定受保护分支**
    下滑找到 `Target branches`，匹配规则选择 `Include default branch`（默认主线main），或手动填写分支名 `main`。
4. **添加核心保护规则（关键配置）**
    下滑至 `Rules` 区域，点击 `Add rule`，添加以下4条强制规则：
   
   | 规则名称                                        | 配置作用                               |
   | ------------------------------------------- | ---------------------------------- |
   | Restrict pushes matching a ref              | 禁止任何人直接 `git push origin main`     |
   | Block force pushes                          | 拦截 `git push --force` 强制推送，防止历史被篡改 |
   | Require pull request reviews before merging | 合并主线前必须提交PR并完成审核                   |
   | Do not allow deletions                      | 禁止删除main主线分支                       |
5. **保存规则集**
    页面底部点击 `Create ruleset`，主线保护立即生效。

---

## 三、配置完成后的权限效果（对应讲义协作规范）

### ✅ 普通协作者（Write权限）

1. 仅能推送自己创建的功能分支，无法直接push main；
2. 修改主线代码必须提交PR，等待仓库管理员审核通过后才能合并；
3. 不能执行强制推送、删除主线等高危操作。
   
   ### ⚠️ 管理员（Admin权限）
   
   默认同样受规则约束；若需要临时豁免，可添加至上方 `Bypass list`，课堂教学不推荐豁免。

---

## 四、新旧版本分支保护区别（考点补充）

1. **旧版入口**：仓库首页蓝色提示 `Protect this branch`，简易单分支保护；
2. **新版Rulesets**：支持批量多分支统一配置、精细化权限管控，是GitHub官方主推方案；
3. 两者最终效果一致，教学中优先使用 `Rulesets` 页面配置，适配新版界面。

---

## 五、配套讲义易错提醒

1. 若 `Enforcement status` 保持 `Disabled`，所有保护规则不会生效，他人仍可直接推送main；
2. `Target branches` 必须正确绑定 `main`，否则规则不会作用于主线；
3. 豁免名单仅用于特殊运维场景，多人课堂协作项目保持空白，保证规范统一。
