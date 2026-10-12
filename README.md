# SoloCitations

激光惯性约束聚变能源（Inertial Confinement Fusion Energy, IFE）领域的**独奏引用（Solo Citations, SC）**分析代码。

本仓库是《科学计量学导论》课程报告 **《激光惯性约束聚变能源文献计量分析》** 的配套代码与数据。
全部结果可在无网络、无 Scopus API key 的情况下复核；只有两个采集阶段需要 API 访问。

---

## 目录

- [研究内容](#研究内容)
- [快速开始](#快速开始)
- [流水线](#流水线)
- [仓库结构](#仓库结构)
- [数据说明](#数据说明)
- [复现报告结果](#复现报告结果)
- [编译报告](#编译报告)
- [关于 API key](#关于-api-key)
- [已知问题](#已知问题)
- [引用与许可](#引用与许可)

---

## 研究内容

2021 年美国国家点火装置（NIF）首次实现聚变增益 $Q>1$。本研究以 Scopus 数据库为数据源，
构建包含 **243 篇核心文献**（被引 ≥ 50 次）的三层引文网络，用 Wu 与 Yan 提出的
独奏引用指标判断该领域是否发生了实质性的范式转型。

对目标文献 $F$ 的每一篇施引文献 $C$：

| 类型 | 条件 | SC |
|---|---|---|
| 独奏式引用（Solo Citation） | $C$ 引用 $F$，但不引用 $F$ 的任何一篇参考文献 | 1 |
| 二重引用（Duet Citation） | $C$ 同时引用 $F$ 与其至少一篇参考文献 | 0 |
| 序曲引用（Prelude Citation） | $C$ 只引用 $F$ 的参考文献 | — |

评估指标取 $R_{\mathrm{SC}} = \mathrm{SCtot} / \text{Cited by}$。

**主要结论**：IFE 领域的 $R_{\mathrm{SC}}$ 自 1992 年以来整体波动下降，知识积累呈渐进式发展；
NIF 点火论文的 $R_{\mathrm{SC}} = 79/475 \approx 0.166$ 低于当年均值 0.222，
说明该成果延续性强于颠覆性。详见 [`report/main.pdf`](report/main.pdf)。

---

## 快速开始

```powershell
# 1) 只需要复核结果：装三个基础依赖即可，不需要 API key
pip install -r requirements.txt

# 2) 一致性自检（离线，几秒钟）
python scripts/verify_results.py

# 3) 重绘报告中的图表
python scripts/plot_rate.py --csv data/processed/yearly_stats.csv   # 图 3
python scripts/make_overview_figures.py --full-query                 # 图 1、图 2
```

需要从 Scopus 重新采集数据时，先配置 API key，见[关于 API key](#关于-api-key)：

```powershell
python scripts/collect_citations.py --from-export --limit 5   # 先试 5 篇
python scripts/collect_citations.py --from-export             # 全量 243 篇
python scripts/build_networks.py                              # 构建引文网络
python scripts/aggregate_sc.py                                # 汇总 SC 与被引
python scripts/plot_rate.py
```

---

## 流水线

四个阶段与报告 4.2.4 节的处理流程一一对应：

```
                 ┌── data/raw/scopus_export_*.csv（Scopus 导出的 243 篇核心文献）
                 │
① 采集一级引用    │  collect_citations.py --stage 1
                 │  → data/interim/<eid>/REFs.csv        目标文献的参考文献
                 │  → data/interim/<eid>/Cits.csv        引用目标文献的施引文献
                 │
② 展开二级引用    │  collect_citations.py --stage 2
                 │  → data/interim/<eid>/<eid>'sCitsREF/<cit>'sREFs.csv
                 │                                       每篇施引文献的参考文献
                 │
③ 构建网络与 SC   │  build_networks.py      → data/processed/network/<eid>_nodes.csv
                 │                                       三层有向网络 + 每节点 SC 标记
                 │
④ 指标聚合        │  aggregate_sc.py        → data/processed/eid_sc_tot.csv
                 │  plot_rate.py           → report/figures/washed_yearly_rate.png
                 └─ make_overview_figures.py（仅用步骤 ① 的元数据，与网络无关）
```

采集阶段（① ②）支持断点续跑：已完成的目标 EID 记入
`data/interim/done_b_eids.txt` / `done_c_eids.txt`，重新运行会自动跳过。
多线程滑动窗口保证个别施引文献超过 3000 篇的目标论文也不会撑爆内存。

---

## 仓库结构

```
SoloCitations/
├── scripts/                     命令行入口（薄封装，不含研究逻辑）
│   ├── collect_citations.py     阶段 ①②：从 Scopus 采集引文关系
│   ├── build_networks.py        阶段 ③：三层引文网络 + SC 标记
│   ├── aggregate_sc.py          阶段 ④：SC 汇总与 R_SC 计算
│   ├── plot_rate.py             逐年 R_SC 折线图（报告图 3）
│   ├── make_overview_figures.py 发文量 / 国家分布图（报告图 1、2）
│   └── verify_results.py        离线一致性自检
├── src/solo_citations/          可复用的研究代码
│   ├── paths.py                 全部输入输出路径（可用环境变量覆盖）
│   ├── scopus.py                API key 读取与 pybliometrics 初始化
│   ├── collect.py               阶段 ①②的实现
│   ├── network.py               阶段 ③④的实现
│   ├── citation_ratio.py        逐年统计与绘图
│   └── figures.py               元数据图表
├── config/                      配置模板（真实密钥不入库）
├── data/
│   ├── raw/                     Scopus 导出数据（已提交，0.4 MB）
│   ├── processed/               243 篇的最终结果与引文网络节点表（已提交，24 MB）
│   └── interim/                 逐篇原始抓取结果（不入库，可重新生成）
├── report/                      LaTeX 课程报告源码、图表与编译好的 PDF
│   ├── main.tex                 报告正文
│   ├── USTCReport.sty           排版模板（取自 jweihe/USTC_Latex_Template）
│   ├── reference.bib            参考文献
│   ├── figures/                 三张图 + 校徽素材
│   └── main.pdf                 编译产物（11 页）
├── legacy/                      与本研究无关的旧数据，仅作溯源
└── docs/                        数据说明与复现指南
    ├── DATA.md                  每个数据文件的字段、来源与坑
    └── REPRODUCE.md             三个层次的复现步骤
```

---

## 数据说明

| 文件 | 内容 |
|---|---|
| `data/raw/overall.csv` | Scopus「Refine results」面板导出，检索式、全量 3138 篇的年份/国家/类型计数 |
| `data/raw/scopus_export_…csv` | 262 条 Scopus 记录（被引 ≥ 50 次），含标题/作者/年份/被引/DOI |
| `data/processed/base3.csv` | **最终结果表**：243 篇的 `eid, SCtot, Cited by, Year, Title, Rate` |
| `data/processed/network/*_nodes.csv` | 243 篇各自的引文网络节点表 `EID, SC` |
| `data/processed/yearly_stats.csv` | 逐年 $R_{\mathrm{SC}}$ 均值/极值，图 3 的数值底稿 |
| `data/processed/base1.csv` / `.xlsx` | 262 条导出的精简副本 / 100 篇的中间版本（含手工整理的 `SCtot`） |
| `data/processed/base2.xlsx` | 261 篇的中间版本 |
| `data/processed/eid_sc_tot_legacy.csv` | 早期脚本的输出，**数据源有误，见[已知问题](#已知问题)** |
| `legacy/MLNL.csv`、`legacy/MLandLang.csv` | 与本研究无关的机器学习论文导出，仅作为问题溯源保留 |

检索式（`overall.csv` 中记录）：

```
TITLE-ABS-KEY("Laser" AND "inertial confinement fusion" AND "energy")
```

需要注意 `overall.csv` 里的 **3138 篇**是检索式命中的全部文献，
而 262 条的记录导出只是其中被引 ≥ 50 次的部分；两者不能混用。
字段细节与两个数据源的差别见 [`docs/DATA.md`](docs/DATA.md)。

---

## 复现报告结果

两套检查都不需要网络与 API key：

```powershell
# ① 校验 base3.csv 的每个 SCtot 都等于对应节点文件 SC 列之和，且 Rate = SCtot / Cited by
python scripts/verify_results.py

# ② 端到端重算：从 data/interim 重建某篇论文的网络，与 data/processed/network 逐节点比对
python scripts/verify_results.py --rebuild 2-s2.0-36449005127
```

第 ② 项在开发时已通过：重建 `2-s2.0-36449005127` 得到 40 316 个节点、
SC 合计 2068，与归档结果**逐节点完全一致**（0 处差异）。

要完整重跑 ① ② 两个采集阶段还需要 `data/interim`（约 250 MB、5.3 万个文件，
未随仓库分发）。报告中的三个数字可直接复核：

```powershell
python scripts/plot_rate.py --csv data/processed/yearly_stats.csv
```

详细步骤见 [`docs/REPRODUCE.md`](docs/REPRODUCE.md)。

---

## 编译报告

需要一个完整的 TeX Live（含 `ctex`、`xelatex`、`bibtex`）：

```powershell
cd report
xelatex main && bibtex main && xelatex main && xelatex main
```

`main.pdf` 与最终版同名文件 `激光惯性约束聚变能源文献计量分析.pdf` 内容相同。

---

## 关于 API key

**本仓库不包含任何 API key。** 采集脚本按以下优先级读取密钥：

1. 环境变量 `SCOPUS_API_KEYS`（多个 key 用逗号或空白分隔）
2. `config/scopus_keys.txt`（已被 `.gitignore` 忽略），每行一个 key

```powershell
# 方式一：环境变量
$env:SCOPUS_API_KEYS = "key1,key2,key3"
python scripts/collect_citations.py --from-export

# 方式二：密钥文件
Copy-Item config\scopus_keys.example.txt config\scopus_keys.txt
notepad config\scopus_keys.txt
```

脚本会据此生成 `config/pybliometrics.generated.cfg`（同样被忽略），
把请求缓存指向 `data/interim/scopus_cache/`。多个 key 由 pybliometrics 自动轮询。

> 早期的 `pybliometrics.cfg` / `pybliometrics1.cfg` 曾把明文 key 写入文件并提交，
> 那两个文件已从仓库移除。**如果那些 key 仍在使用，请到
> <https://dev.elsevier.com/apikey/manage> 撤销并重新申请。**

---

## 已知问题

**`output/`、`network_output/`、`datasource/MLNL.csv` 与本研究无关。**
这些是机器学习论文（"Cheap and fast"、"Spark SQL"、"GCN" 等）的导出与抓取结果，
是流水线调试时留下的，`datasource/MLNL.csv` 曾被 `batch_b_parallel.py` 等脚本当作 EID 列表误用，
因而 `eid_sc_tot_legacy.csv` 的 134 行是无效数据。

报告结论全部来自 **`output0/` + `network_output0/`** 这一套（243 篇 IFE 文献），
对应仓库中的 `data/processed/base3.csv` 与 `data/processed/network/`。
`legacy/` 目录只保留两个 ML 导出文件用于溯源。

其他局限（与报告 4.5 节一致）：

- 样本仅 243 篇，未做结论稳定性与关键变量敏感性检验；
- 三层网络展开的数据量极大（5.3 万个 CSV、约 250 MB），复现成本高；
- 只用了 $R_{\mathrm{SC}}$ 一个指标，未讨论引用习惯、预印本等因素；
- 未与数据库平均基准或相似领域对比。

---

## 引用与许可

- 指标方法：Wu, Q. & Yan, Z. (2019). *Solo Citations, Duet Citations, and Prelude Citations:
  New Measures of the Disruption of Academic Papers.* arXiv:1905.03461
- 代码：Apache License 2.0，见 [`LICENSE`](LICENSE)
- 报告排版模板：[`report/USTCReport.sty`](report/USTCReport.sty) 取自
  [jweihe/USTC_Latex_Template](https://github.com/jweihe/USTC_Latex_Template)（CC BY 4.0），
  致谢原作者。

Scopus 数据版权归 Elsevier 所有，本仓库仅保留课程研究所需的派生结果。
