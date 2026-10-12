# 复现指南

分三个层次，按需要的代价递增：

| 层次 | 需要什么 | 能验证什么 | 耗时 |
|---|---|---|---|
| A. 离线复核 | `pip install -r requirements.txt` | 所有报告数字与图表 | 秒级 |
| B. 端到端重算 | 上一步 + `data/interim/` | 阶段 ③④ 的代码与归档结果逐节点一致 | 分钟级 |
| C. 完整重跑 | 上一步 + Scopus API key | 从检索式开始的全部流程 | 数小时～数天 |

---

## A. 离线复核（不需要网络与 API key）

```powershell
pip install -r requirements.txt
python scripts/verify_results.py
```

预期输出：

```
检查 ...\data\processed\base3.csv（243 行）
  [通过] 243 篇的 SCtot 与节点文件全部一致
  [通过] Rate == SCtot / Cited by

验证通过。
```

这一步做两件事：

1. 对 `base3.csv` 的每一行，把 `data/processed/network/<eid>_nodes.csv` 的 `SC`
   列求和，与 `SCtot` 比对；
2. 校验 `Rate == SCtot / Cited by`。

重绘全部三张图（写入 `report/figures/`，会覆盖现有文件）：

```powershell
# 图 1（全量 3138 篇）+ 图 2（国家分布）
python scripts/make_overview_figures.py --full-query

# 图 3（逐年独奏引用占比），同时导出数值底稿
python scripts/plot_rate.py --csv data/processed/yearly_stats.csv
```

预期输出（已实测）：

```
发文量数据源：...\data\raw\scopus_export_May 26-2026_1368e081-...csv
Done. Saved as ...\report\figures\article_year.png
  年度记录 3138 篇，年份范围 1977-2026
  其中核心文献 243 篇，年份范围 1992-2024
国家分布数据源：...\data\raw\overall.csv
Done. Saved as ...\report\figures\author_nation.png
```

报告中的关键数字可以这样核对：

```powershell
# 全量逐年发文量之和应为 3138
python -c "import sys; sys.path.insert(0,'src'); from solo_citations import figures; \
print(int(figures.panel_counts('YEAR').sum()))"

# 国家分布（报告正文：美、中、法居前三）
python -c "import sys; sys.path.insert(0,'src'); from solo_citations import figures; \
print(figures.author_countries(top=5))"

# NIF 点火论文（不在样本中）的 R_SC = 79/475
python -c "print(79/475)"                  # 0.166315...

# 2021 年的样本均值（报告正文 0.2224）——见 yearly_stats.csv 的 Year=2021 行
```

### 图 2「作者国籍分布」的数据来源

报告图 2 原先的图片文件在课程目录中没有对应的生成脚本，而且
`data/raw/scopus_export_*.csv` **根本没有机构/国家字段**，无法从中统计国家。
本仓库改为从 Scopus「Refine results」面板导出 `data/raw/overall.csv` 中解析
`COUNTRY` 维度，得到的是**整个检索结果集**的国家分布，与报告文字描述的
「根据检索到的 3138 篇文献元数据」一致：

| 国家 | 记录数 |
|---|---|
| United States | 1350 |
| China | 707 |
| France | 348 |
| Japan | 294 |
| United Kingdom | 229 |

这些数值与报告结论完全吻合。`make_overview_figures.py --top N` 可控制显示前 N 个国家。

### 图 1 的两种口径

```powershell
# 默认：只统计导出的 262 条记录（被引 ≥ 50 次的那批）
python scripts/make_overview_figures.py

# --full-query：统计全量 3138 篇（报告正文的口径，仓库中已按此生成）
python scripts/make_overview_figures.py --full-query
```

两种口径都会用红色叠加 243 篇核心文献并标出核心样本的起始年份（1992）。

---

## B. 端到端重算阶段 ③④

若手上有一份 `data/interim/`（逐篇的 `REFs.csv`、`Cits.csv`、`<eid>'sCitsREF/`），
可以完全重算引文网络：

```powershell
# 用归档数据重建某一篇并与仓库中的结果逐节点比对
python scripts/verify_results.py --rebuild 2-s2.0-36449005127

# 重建全部网络（写入 data/processed/network/，会覆盖归档结果）
python scripts/build_networks.py --input data/interim --output data/processed/network

# 从网络重新汇总 SC 与被引
python scripts/aggregate_sc.py --sample data/raw/scopus_export_*.csv `
    --output data/processed/eid_sc_tot.csv
```

`--rebuild` 的预期输出（开发时实测）：

```
重建 2-s2.0-36449005127 并与归档结果逐节点比对
  [通过] 40316 个节点完全一致，SC 合计 2068
```

要把重建结果与归档结果**同时**保留以便人工比对，先指定另一个输出目录：

```powershell
python scripts/build_networks.py --output data/interim/rebuilt_network
```

---

## C. 完整重跑（需要 Scopus API key）

### C0. 准备密钥

```powershell
$env:SCOPUS_API_KEYS = "你的32位key1,你的32位key2"     # 多个 key 会被轮询
# 或者：Copy-Item config\scopus_keys.example.txt config\scopus_keys.txt 后写入
```

申请地址：<https://dev.elsevier.com/apikey/manage>。
「参考文献列表」（`AbstractRetrieval(view="REF")`）通常需要机构订阅，
没有订阅时阶段 ① 的 `REFs.csv` 会为空，阶段 ③ 的 SC 会全部退化为 0。

### C1. 先小批量验证

```powershell
python scripts/collect_citations.py --from-export --limit 5
python scripts/build_networks.py --limit 5
```

确认 `data/interim/` 下出现 `REFs.csv`、`Cits.csv`，以及 `data/processed/network/`
下出现 5 个 `_nodes.csv`。

### C2. 全量采集

```powershell
# 阶段①+② 一次性跑完（243 篇）
python scripts/collect_citations.py --from-export

# 也可以分开跑，便于单独重试
python scripts/collect_citations.py --from-export --stage 1
python scripts/collect_citations.py --from-export --stage 2
```

采集是**可中断可续跑**的：

- 每篇目标论文完成后写入 `data/interim/done_b_eids.txt` / `done_c_eids.txt`，
  重跑时自动跳过；
- 阶段 ② 逐篇检查 `<citing_eid>'sREFs.csv` 是否已存在，存在即跳过；
- 阶段 ② 有失败的目标记入 `data/interim/failed_c_eids.csv`，修好网络后单独重试：

```powershell
$eids = (Import-Csv data\interim\failed_c_eids.csv).EID
python scripts/collect_citations.py --stage 2 @eids
```

- 想强制重抓某批：加 `--overwrite`。

阶段 ② 的并发由滑动窗口控制（默认 16 线程、最多 500 个待处理任务），
单篇施引文献超过 3000 篇的目标也不会耗尽内存：

```powershell
python scripts/collect_citations.py --from-export --stage 2 --workers 24
```

### C3. 网络、汇总、出图

```powershell
python scripts/build_networks.py
python scripts/aggregate_sc.py --with-rate
python scripts/plot_rate.py --csv data/processed/yearly_stats.csv
python scripts/make_overview_figures.py --full-query
python scripts/verify_results.py
```

---

## 路径覆盖

所有路径都取自 `src/solo_citations/paths.py`，可用环境变量把数据放到别处
（例如放进内存盘或大容量磁盘）：

| 环境变量 | 默认值 | 含义 |
|---|---|---|
| `SOLOCITATIONS_ROOT` | 仓库根目录 | 项目根 |
| `SOLOCITATIONS_DATA_RAW` | `data/raw` | Scopus 原始导出 |
| `SOLOCITATIONS_DATA_INTERIM` | `data/interim` | 逐篇抓取结果（大） |
| `SOLOCITATIONS_DATA_PROCESSED` | `data/processed` | 汇总结果 |
| `SOLOCITATIONS_NETWORK_DIR` | `data/processed/network` | 节点表目录 |
| `SOLOCITATIONS_FIGURES_DIR` | `report/figures` | 图表输出 |
| `SOLOCITATIONS_SCOPUS_CFG` | `config/pybliometrics.generated.cfg` | 生成的配置文件 |

命令行参数（`--input`、`--output`、`--sample` 等）优先于环境变量。

---

## 编译报告

```powershell
cd report
xelatex main
bibtex main
xelatex main
xelatex main
```

需要 TeX Live 的 `ctex`、`xelatex`、`bibtex` 以及 `USTCReport.sty` 依赖的宏包
（`tcolorbox`、`fontawesome`、`pythonhighlight` 等）。两次 `xelatex` 是为了
让目录与交叉引用稳定。编译产物（`.aux`、`.log`、`.toc` 等）已在 `.gitignore` 中忽略。

### 报告源码中的一个已知问题

`report/reference.bib` 第 1 行是一条 biblatex 的 `\usepackage` 命令，
它不是合法的 BibTeX 语法。当前的编译方式（`bibliographystyle{unsrt}` + `bibtex`）
会忽略这一行，因此不影响 `main.pdf` 的生成；但如果改用 biblatex/biber，
需要先把这行删掉。
