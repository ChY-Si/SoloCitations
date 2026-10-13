# SoloCitations

**激光惯性约束聚变能源（Inertial Confinement Fusion Energy, IFE）的独奏引用分析**

用独奏引用（Solo Citations, SC）指标衡量 2021 年 NIF 点火是否真正重构了惯性约束聚变领域的知识体系。
本仓库是《科学计量学导论》课程报告 **《激光惯性约束聚变能源文献计量分析》** 的配套代码、数据与报告源码。

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Report](https://img.shields.io/badge/report-11%20pages-b31b1b.svg)](report/main.pdf)

---

## 这是什么

2021 年美国国家点火装置（NIF）首次实现聚变增益 $Q>1$。判断这一里程碑是否构成"颠覆性创新"，
不能只看物理指标，还要看后续研究**如何引用它**。

本项目基于 Scopus 数据库构建 **243 篇核心文献**（被引 ≥ 50 次）的三层引文网络，
对每篇目标文献 $F$ 的每一篇施引文献 $C$ 判定：

| 引用类型 | 判定条件 | SC |
|---|---|---|
| **独奏式引用** Solo Citation | $C$ 引用 $F$，但**不**引用 $F$ 的任何一篇参考文献 | 1 |
| **二重引用** Duet Citation | $C$ 同时引用 $F$ 与其至少一篇参考文献 | 0 |
| **序曲引用** Prelude Citation | $C$ 只引用 $F$ 的参考文献 | — |

指标取 $R_{\mathrm{SC}} = \mathrm{SC}_{\mathrm{tot}} / \text{Cited by}$：**值越高，说明后续研究越倾向于绕过该文献的知识背景直接引用它本身，替代性越强。**

## 主要结论

- IFE 领域的 $R_{\mathrm{SC}}$ **自 1992 年以来整体波动下降**，知识积累呈渐进式发展，而非革命性跃迁；
- NIF 点火论文的 $R_{\mathrm{SC}} = 79/475 \approx 0.166$，**低于**当年（2021）样本均值 0.222，
  说明该成果**延续性强于颠覆性**——是既有范式的重要里程碑，而非路径创新；
- 知识产出高度集中于美（1350）、中（707）、法（348），体现大科学装置驱动的领域特征。

完整论证见 **[报告全文](report/main.pdf)**（11 页）。

---

## 快速开始

**成果复核完全离线，不需要网络，也不需要 Scopus API key：**

```powershell
pip install -r requirements.txt

python scripts/verify_results.py                                    # 一致性自检，几秒钟
python scripts/plot_rate.py --csv data/processed/yearly_stats.csv   # 图 3
python scripts/make_overview_figures.py --full-query                # 图 1、图 2
```

`verify_results.py` 会逐篇校验 243 篇的 `SCtot` 是否等于其引文网络节点文件 `SC` 列之和，
以及 `Rate == SCtot / Cited by`。预期输出：

```
检查 data\processed\base3.csv（243 行）
  [通过] 243 篇的 SCtot 与节点文件全部一致
  [通过] Rate == SCtot / Cited by

验证通过。
```

只有需要**重新采集数据**时才要配置密钥：

```powershell
$env:SCOPUS_API_KEYS = "你的32位key1,你的32位key2"      # 多个 key 自动轮询

python scripts/collect_citations.py --from-export --limit 5   # 先试 5 篇
python scripts/collect_citations.py --from-export             # 全量采集
python scripts/build_networks.py                              # 构建引文网络
python scripts/aggregate_sc.py --with-rate                    # 汇总 SC 与 R_SC
python scripts/plot_rate.py                                   # 出图
```

---

## 处理流水线

```
Scopus 导出（data/raw/scopus_export_*.csv）
      │
      │  ① collect_citations.py --stage 1
      ├─→ data/interim/<eid>/REFs.csv          目标文献的参考文献
      ├─→ data/interim/<eid>/Cits.csv          引用目标文献的施引文献
      │
      │  ② collect_citations.py --stage 2
      ├─→ data/interim/<eid>/<eid>'sCitsREF/<cit>'sREFs.csv
      │                                        每篇施引文献的参考文献
      │
      │  ③ build_networks.py
      ├─→ data/processed/network/<eid>_nodes.csv
      │                                        三层有向网络 + 每节点 SC 标记
      │
      └─ ④ aggregate_sc.py  → data/processed/eid_sc_tot.csv
         plot_rate.py       → report/figures/washed_yearly_rate.png
```

**工程要点**

- **断点续跑**：阶段 ①② 已完成的目标 EID 记入 `done_b_eids.txt` / `done_c_eids.txt`，
  中断后重新运行自动跳过，不必从头再来；
- **滑动窗口限流**：阶段 ② 用固定大小的待处理队列（默认 16 线程、最多 500 个任务），
  即使某篇目标文献有 3000+ 篇施引文献也不会耗尽内存；
- **请求缓存**：pybliometrics 的缓存落在 `data/interim/scopus_cache/`，
  重复调试不会浪费 API 配额。

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
├── data/
│   ├── raw/                     Scopus 导出数据（已提交，0.4 MB）
│   ├── processed/               243 篇最终结果与引文网络节点表（已提交，24 MB）
│   └── interim/                 逐篇抓取中间数据（可重新生成，不入库）
├── report/                      LaTeX 报告源码、图表与编译好的 PDF
│   ├── main.tex / main.pdf      正文与编译产物（11 页）
│   ├── USTCReport.sty           排版模板
│   ├── reference.bib            参考文献
│   └── figures/                 三张图 + 校徽素材
├── docs/
│   ├── DATA.md                  数据字段、来源与口径说明
│   └── REPRODUCE.md             三个层次的复现步骤
├── config/                      配置模板（真实密钥不入库）
└── pyproject.toml               可选的包安装配置
```

---

## 数据

检索式（记录于 `data/raw/overall.csv`）：

```
TITLE-ABS-KEY("Laser" AND "inertial confinement fusion" AND "energy")
```

命中 **3138 篇**；从中保留被引 ≥ 50 次且引用关系完整的 **243 篇**作为核心样本。

| 文件 | 内容 |
|---|---|
| `data/raw/overall.csv` | Refine results 面板导出：检索式与全量 3138 篇的年份/国家/类型计数 |
| `data/raw/scopus_export_…csv` | 262 条 Scopus 记录（被引 ≥ 50 次） |
| `data/processed/base3.csv` | **最终结果表**：243 篇的 `eid, SCtot, Cited by, Year, Title, Rate` |
| `data/processed/network/*_nodes.csv` | 243 篇各自的引文网络节点表 `EID, SC` |
| `data/processed/yearly_stats.csv` | 逐年 $R_{\mathrm{SC}}$ 均值与极值（图 3 的数值底稿） |
| `data/processed/base1.*`、`base2.xlsx` | 样本筛选过程中的中间版本 |

字段级说明、两种数据源的口径差别，见 **[docs/DATA.md](docs/DATA.md)**。

## 复现

| 层次 | 需要什么 | 能验证什么 | 耗时 |
|---|---|---|---|
| **A. 离线复核** | `pip install -r requirements.txt` | 全部报告数字与图表 | 秒级 |
| **B. 端到端重算** | 上一步 + `data/interim/` | 阶段 ③④ 与归档结果逐节点一致 | 分钟级 |
| **C. 完整重跑** | 上一步 + Scopus API key | 从检索式开始的全部流程 | 数小时 |

B 层可用一行命令验证：

```powershell
python scripts/verify_results.py --rebuild 2-s2.0-36449005127
```

它会从中间数据重建该论文的网络并与仓库中归档的结果逐节点比对：

```
重建 2-s2.0-36449005127 并与归档结果逐节点比对
  [通过] 40316 个节点完全一致，SC 合计 2068
```

逐步说明见 **[docs/REPRODUCE.md](docs/REPRODUCE.md)**。

## 编译报告

需要一个完整的 TeX Live（含 `ctex`、`xelatex`、`bibtex`）：

```powershell
cd report
latexmk -xelatex main.tex
```

## 关于 API key

**本仓库不包含任何 API key。** 采集脚本按优先级读取密钥：

1. 环境变量 `SCOPUS_API_KEYS`（多个 key 用逗号或空白分隔）
2. `config/scopus_keys.txt`（已被 `.gitignore` 忽略），每行一个 key

```powershell
Copy-Item config\scopus_keys.example.txt config\scopus_keys.txt
notepad config\scopus_keys.txt
```

脚本据此生成 `config/pybliometrics.generated.cfg`（同样被忽略），
把请求缓存指向 `data/interim/scopus_cache/`。

> `AbstractRetrieval(view="REF")` 获取参考文献列表通常需要机构订阅；
> 没有订阅时 `REFs.csv` 会为空，SC 将全部退化为 0。

## 引用

指标方法来自：

> Wu, Q. & Yan, Z. (2019). *Solo Citations, Duet Citations, and Prelude Citations:
> New Measures of the Disruption of Academic Papers.* arXiv:1905.03461

报告排版模板取自 [jweihe/USTC_Latex_Template](https://github.com/jweihe/USTC_Latex_Template)（CC BY 4.0），致谢原作者。

## 许可

代码以 [Apache License 2.0](LICENSE) 发布。
Scopus 数据版权归 Elsevier 所有，本仓库仅保留研究所需的派生结果。
