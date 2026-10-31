# codex-skill

一个 Git 仓库，集中维护多个彼此独立、可单独安装和发布的 Codex Skills。

## Skills

| Skill | 版本 | 用途 |
| --- | --- | --- |
| `director-mode-fusion` | 1.0.16 | 将小说、剧本或故事改编为可执行的导演分镜 |
| `shot-parser` | 2.0.4 | 从分镜或剧本解析角色、纯环境场景和特殊剧情道具 |

每个 Skill 都拥有自己的 `SKILL.md`、参考资料、脚本、测试和版本记录。安装其中一个 Skill 时，不需要同时安装其他 Skill。

## 目录结构

```text
codex-skill/
├── skills/
│   ├── director-mode-fusion/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   ├── references/
│   │   ├── examples/
│   │   ├── evaluations/
│   │   ├── scripts/
│   │   ├── CHANGELOG.md
│   │   └── README.md
│   └── shot-parser/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       ├── tests/
│       ├── CHANGELOG.md
│       ├── VERSION
│       └── README.md
├── tools/
│   ├── skill_common.py
│   ├── sync_skill.py
│   ├── validate_skills.py
│   └── release_skill.py
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## 安装

先克隆仓库：

```powershell
git clone https://github.com/ikun1946/codex-skill.git
Set-Location codex-skill
```

安装指定 Skill：

```powershell
python tools/sync_skill.py shot-parser
python tools/sync_skill.py director-mode-fusion
```

安装全部 Skill：

```powershell
python tools/sync_skill.py --all
```

默认同步到：

```text
%USERPROFILE%\.codex\skills\<skill-name>\
%USERPROFILE%\.gemini\config\skills\<skill-name>\
```

目标目录已存在时，同步工具默认停止，避免覆盖本地修改。确认需要覆盖后追加 `--force`：

```powershell
python tools/sync_skill.py director-mode-fusion --force
```

也可以手动把 `skills/<skill-name>/` 复制到目标技能目录。

## 校验

检查所有 Skill 的目录、名称和 `SKILL.md`：

```powershell
python tools/validate_skills.py
```

同时运行各 Skill 自带的测试：

```powershell
python tools/validate_skills.py --tests
```

## 独立发布

每个 Skill 使用带自身名称的 Git 标签，例如：

```text
director-mode-fusion-v1.0.17
shot-parser-v2.0.5
```

发布一个 Skill：

```powershell
python tools/release_skill.py director-mode-fusion 1.0.17 -m "更新说明"
python tools/release_skill.py shot-parser 2.0.5 -m "更新说明"
```

发布工具只更新目标 Skill 的版本、变更记录、提交、标签和 GitHub Release，不修改其他 Skill 的版本。

## 独立性约定

- Skill 不得在运行时读取另一个 Skill 目录中的文件。
- 每个 Skill 的 `scripts/`、`references/`、`assets/` 和测试必须位于自身目录内。
- 根目录 `tools/` 仅用于仓库安装、校验和发布，不属于任何 Skill 的运行时依赖。
- 每个 Skill 可以独立安装、更新、回滚、校验和发布。
