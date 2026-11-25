# 20261104龙口市红旗小学五年级数学期中考试试卷

依据两张原卷照片整理的 A3 试题版、答案版及可接续 LaTeX 工程。保留原始双栏题序、跨栏断点和图形位置；答案使用红色。

## 查看试卷

- [试题版 PDF](pdf/五年级数学小测_试题版.pdf)：A3 横向，2 页。
- [答案版 PDF](pdf/五年级数学小测_答案版.pdf)：A3 横向，2 页。
- [先读我](00_先读我.txt)：工程结构及基本操作。
- [新对话接续提示](新对话接续提示.txt)：可复制到新对话的交接提示。
- [工程状态](project_state.json)：完成状态、限制及下一步。

打印时选择 A3、横向、实际大小（100%）。

## 文件结构

| 目录/文件 | 内容 |
| --- | --- |
| `pdf/` | 两份当前参考成品 |
| `src/` | 两份主 TeX、共享 TikZ 图形、原题局部图与编译说明 |
| `originals/` | 两张原始上传照片 |
| `vendor/` | 中文宏包、Fandol 字体、上游源码、版本与许可证 |
| `scripts/` | 编译、完整性检查、重新打包脚本 |
| `reference/` | 四页参考预览 |
| `docs/` | 数学核对、版式约束、恢复范围、运行环境 |
| `verification/` | 2026-11-19 的实际验证记录，以及本次仓库发布说明 |
| `archive/` | 原 LaTeX 源 ZIP 的来源备份；其所有内容同时在 `src/` 展开 |
| `AGENTS.md` | 后续协作和修改规则 |
| `SHA256SUMS` | 当前仓库快照的逐文件 SHA-256 |

工程文件按目录展开存放，可以直接查看和修改。

## 克隆与检查

```sh
git clone https://github.com/liyiliuxingyu/20261104-longkou-hongqi-primary-school-grade5-midterm-math-exam.git
cd 20261104-longkou-hongqi-primary-school-grade5-midterm-math-exam
python3 scripts/verify.py --files-only --strict
```

完整性检查只需 Python 3.9 或更新版本。新克隆仓库的 `.git` 元数据不计入工程文件清单；产生 `build/` 等新文件后再次检查时，可去掉 `--strict`。

## 编译

基础环境需要 XeLaTeX、xdvipdfmx、kpsewhich，以及标准 LaTeX/TikZ 和 Computer Modern/Latin Modern 字体。中文依赖已经放在 `vendor/texmf`。

```sh
python3 scripts/build.py --check
python3 scripts/build.py
```

每版自动编译两遍，结果写入 `build/`。`pdf/` 中的参考成品不会被覆盖。Windows 可使用 `py -3` 或 `build.bat`，Linux/macOS 可使用 `sh build.sh`。本项目历史实测环境为 Linux，Windows/macOS 未实机验证。

完整 PDF 校验及渲染比较需要 Python 3.11 或更新版本和 `requirements.txt` 中的组件：

```sh
python3 -m pip install -r requirements.txt
python3 scripts/verify.py --skip-checksums --pdf-dir build --compare-dir pdf --require-identical-render --render-dir build/preview --report build/verification.json
```

详细说明见 [运行环境与依赖](docs/运行环境与依赖.txt)。

## 已完成的验证与未决项

2026-11-19 已从独立 ZIP 解压到含中文和空格的新目录，成功完成两版、每版两遍 XeLaTeX 编译；四页文字与参考成品一致，108 DPI 下 RGB 渲染逐像素一致。记录见 [验证说明](verification/本次验证说明.txt) 和 [比较报告](verification/rebuild_pdf_comparison.json)。

2026-11-25 为 GitHub 发布恢复相同工程包，核对其完整性并保留全部 170 个原包文件。发布新增仓库首页和来源记录，对校验器作 Git 仓库兼容调整，并修正依赖说明中的校验清单路径；没有改动题目、答案、图形、PDF 或字体。本次没有重复进行 TeX 编译，前述编译和图像比较属于 2026-11-19 的验证记录。

仍需保留以下状态：

- **填空第 10 题外露面积待核。** 体积为 6 立方分米确定；图过暗，不能据手写数字猜定面积。
- **附加第 3 题的 13 立方分米有条件。** 按铁块完全浸没计算；原题未明确这一条件。
- 旧临时工作区中的部分早期草稿和生成脚本没有恢复。现行 TeX 已完整展开，可直接编译；见 [恢复范围](docs/恢复范围.txt)。

仓库名称及中文标题采用用户指定的学校、年级、考试日期和题名；试卷内部沿用已经排版的“五年级数学小测”标题。

## 继续修改或交接

先读 `AGENTS.md`、`project_state.json` 和 `docs/`，保持 A3 排版。修改共同题干时同步更新两份主源码。确认新成品后更新状态和验证记录，再运行：

```sh
python3 scripts/pack.py ../A3_math_exam_next_snapshot.zip
```

该命令排除 `.git` 和可重建缓存，更新 `SHA256SUMS`，并检查压缩包内部文件。不要用更新校验清单掩盖非预期改动。

第三方字体、宏包及其源码的上游许可证、固定版本和取得来源见 `vendor/licenses/`、`vendor/metadata/`。
