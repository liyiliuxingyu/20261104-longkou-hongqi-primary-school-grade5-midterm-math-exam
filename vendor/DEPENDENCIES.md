# TeX 依赖支持说明

这组文件为五年级数学小测 A3 工程补齐中文排版依赖，可随工程放入 `vendor/`。它不是完整 TeX 发行版，仍需要本机具有 XeLaTeX、LaTeX 基础包、数学包和 TikZ。

## 已固定并验证的版本

| 包 | 版本 | 发布日期 | 许可 |
|---|---|---|---|
| ctex | 2.5.10 | 2022-07-14 | LPPL 1.3c 或更新版本 |
| xeCJK | 3.9.1 | 2022-08-05 | LPPL 1.3c 或更新版本 |
| zhnumber | 3.0 | 2022-07-14 | LPPL 1.3c 或更新版本 |
| Fandol | 0.3 | 2015-07-18 | GPL 3.0，附上游字体嵌入例外 |

ctex、xeCJK、zhnumber 取自 [CTeX-org/ctex-kit 的固定提交](https://github.com/CTeX-org/ctex-kit/tree/c4ccfaefe803ab4a12c9fedc929be1e349e3c612)，对应 xeCJK-v3.9.1 标签。运行文件用上游 `ctxdocstrip` 从原始 `.dtx` 提取，没有修改宏包功能。生成所依据的原始 `.dtx`、`.ins` 及支持源码保留在 `texmf/source/`。

Fandol 取自 [CTAN 官方字体包](https://mirrors.ctan.org/fonts/fandol.zip)，保留全部八个原始 OpenType 字体文件。包内记录的版本号为 0.3；它与每个字体文件的内部字体版本字段是不同概念。上述字体和宏包不含任何用户的账号、认证信息或工具凭据。

当前 CTAN 的 ctex、xeCJK 和 zhnumber 新版本要求更新的 LaTeX 内核，因此这里固定使用已在现有内核下编译通过的相互兼容版本。完整版本、来源、源归档 SHA256 和源文件提交记录见 `metadata/dependency-manifest.json`。

## 需要本机提供的基础组件

- XeTeX / XeLaTeX 与 LaTeX2e 基础文件。
- l3kernel、l3packages、fontspec、geometry。
- amsmath、amsfonts（含 amssymb）、tools（含 array、tabularx）。
- graphics（含 graphicx）、xcolor、PGF/TikZ。
- TikZ 的 calc、arrows.meta、decorations.pathreplacing 库。
- Latin Modern、Computer Modern 和标准 AMS 数学字体。

这些中文依赖在当前机器的 XeTeX 0.999996 / TeX Live 2025-dev、LaTeX2e 2024-11-01 patch 2 下完成基础编译验证，覆盖中文常规字、粗体、黑体、楷体、数学分数和 TikZ 括号图。这个基础样例没有覆盖完整试卷中的带圈数字字体；完整试卷另需下述 Latin Modern 数学符号字体映射。完整工程的通过状态以工程构建与验证报告为准。

## 搜索路径和格式缓存

优先用工程构建脚本设置 `TEXMFHOME` 指向工程内的 `vendor/texmf`。如果系统的 `ls-R` 索引失效，脚本可以仅在本次构建进程内读取 `kpsewhich -var-value=TEXMF` 的展开结果并去掉 `!!`，让 kpathsea 正常搜索已有目录；不需要修改系统索引或系统配置。

如果本机没有 `xelatex.fmt`，可以在工程的 `build/.formats` 中用当前引擎生成：

```sh
xetex -ini -etex -no-pdf -jobname=xelatex -progname=xelatex -interaction=nonstopmode -halt-on-error xelatex.ini
```

编译时将 `TEXFORMATS` 指向该缓存目录并保留末尾的路径分隔符，以继续使用系统默认搜索路径。`TEXMFVAR`、`TEXMFCONFIG` 和 `TEXMFCACHE` 也应指向工程构建缓存。生成的 `.fmt` 与具体引擎及基础包有关，不作为跨机器依赖文件打包。

本次格式生成找不到 `language.dat` 时，TeX 正常回退到已有的 `hyphen.tex`；该工程没有多语种断词需求。若在其他项目中需要多语种断词，应由对应发行版提供其语言配置。

## 数学符号与带圈数字的字体映射

完整试卷的带圈数字会调用 Latin Modern 数学符号字体，例如 `lmsy9`。该字体需要 `lm.map` 中指定的 `lm-mathsy.enc` 重编码；仅能找到 `lmsy9.pfb` 和 `lmsy9.tfm` 并不充分。基础编译样例所使用的 CMR/CMSY 字体正常，不代表这里的映射依赖已经覆盖。

当前机器缺少生成后的 `pdftex.map` 时，完整试卷的 xdvipdfmx 曾在处理 `lmsy9` 时报告缺失字形并异常退出。对完整试题 XDV 显式加载本机 `lm.map` 后，驱动成功生成 PDF，因此不能将这一问题归因于原题 PNG 或中文文件名。

工程构建脚本针对这种情况，仅在系统 `pdftex.map` 缺失时，把本机已有的 `cm.map`、`cmextra.map` 和 `lm.map` 拼接到工程 `build/.fontmaps/pdftex.map`，并仅给当前编译进程设置 `TEXFONTMAPS`，保留默认搜索路径。该步骤不更换字体、不改题目源码，也不修改系统配置。若本机连这些基础映射或编码文件也未安装，应补齐该机发行版的 Latin Modern 与标准数学字体组件。

## 许可及文件校验

- 每个宏包的原始许可声明与完整 LPPL 文本位于 `licenses/`。
- Fandol 原始 GPL 与字体嵌入例外全文位于 `licenses/Fandol-GPL-3.0-with-font-exception.txt`，不要只保留 GPL 正文而遗漏文末例外。
- TeX 资源树逐文件 SHA256 位于 `metadata/texmf-files.json`；整个工程的完整校验清单位于仓库根目录 `SHA256SUMS`。可在工程根目录运行 `python3 scripts/verify.py --files-only --strict`。
- 不包含预编译格式缓存、系统 TeX 可执行程序、网络配置或认证数据。

## 给工程装配者的复制范围

复制 `texmf/`、`licenses/`、`metadata/` 和本说明文件。不要复制下载缓存 `downloads/`，其中有未采用的新版本归档和重复字体压缩包。它们不是该支持包的运行依赖。
