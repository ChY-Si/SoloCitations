# 数据说明

本次研究的数据全部来自 Elsevier Scopus 数据库。仓库中保留的是**派生结果与小型原始导出**，
体积较大的逐篇抓取中间数据（`data/interim/`）可用采集脚本重新生成。

---

## 1. 检索式与样本

`data/raw/overall.csv` 是 Scopus 结果页「Refine results」面板的导出，记录了检索式本身：

```
TITLE-ABS-KEY("Laser" AND "inertial confinement fusion" AND "energy")
```

该文件的结构不是标准 CSV：先是一行标题、一行检索式，随后是一张**宽表**，
表头给出维度名，数据行每个维度给出「取值, 数量」一对。解析后的计数如下
（`solo_citations.figures.refine_panel()` 可完整解析）：

| 维度 | 部分取值 |
|---|---|
| **YEAR（合计 3138）** | 2026: 61、2025: 179、2024: 131、2023: 106、2022: 111、2016: 233、2008: 179 |
| COUNTRY | United States 1350、China 707、France 348、Japan 294、United Kingdom 229 |
| DOCUMENT TYPE | Article 1913、Conference Paper 1063、Review 105 |
| SOURCE TYPE | Journal 2155、Conference Proceeding 931、Book 20 |
| OPEN ACCESS | All Open Access 1217、Green 737、Green Accepted 731、Gold 505 |
| SUBJECT AREA | Physics and Astronomy 90、Engineering 84、Materials Science 79 |
| LANGUAGE | English 2833、Chinese 265、French 3 |

**报告正文所述的 3138 篇即 YEAR 维度各年计数之和**（1977–2026），
报告中「作者国籍分布集中于美、中、法」直接对应上表的 COUNTRY 前三名。

> 需要注意：仓库中那份 Scopus 记录导出（见下一节）只有 **262 行**，是「被引 ≥ 50 次」
> 的子集，不是全部 3138 篇；国家分布这类全量统计只能从 `overall.csv` 的面板得到。

## 2. 样本筛选

`data/raw/scopus_export_*.csv` 的 262 条记录，其 `Cited by` 全部 ≥ 50。
从中剔除引文网络数据不全的篇目后，最终得到 **243 篇核心文献**，
由 `base3.csv` 与 `data/processed/network/` 中 243 个 `_nodes.csv` 文件共同界定
（243 个 EID 全部包含在 262 条导出记录中）。

---

## 3. `data/raw/` —— Scopus 原始导出

### `scopus_export_May 26-2026_1368e081-84f1-42f9-aa2a-c851febd6f38.csv`

大小 402 KB，**262 行 × 19 列**，UTF-8（带 BOM）。这 262 条是被引次数 ≥ 50 次的
文献，不是检索式命中的全部 3138 篇。列含义：

| 列名 | 说明 | 本研究的用途 |
|---|---|---|
| `Authors` | 作者缩写列表 | — |
| `Author full names` | 作者全名及 Scopus 作者 ID | — |
| `Author(s) ID` | 作者 ID | — |
| `Title` | 文献标题 | 结果表中保留 |
| `Year` | 发表年份（1980–2024，无缺失） | 年份分组 |
| `Source title` | 来源期刊/会议 | — |
| `Volume` / `Issue` / `Art. No.` / `Page start` / `Page end` | 卷期页码 | — |
| `Cited by` | 总被引次数（全部 ≥ 50） | $R_{\mathrm{SC}}$ 的分母 |
| `DOI` | DOI | — |
| `Link` | Scopus 详情页链接 | — |
| `Document Type` | 文献类型 | — |
| `Publication Stage` | 最终稿/在印 | — |
| `Open Access` | 开放获取类型 | — |
| `Source` | 来源 | — |
| `EID` | Scopus 文献 ID，形如 `2-s2.0-85009319792` | **全流程的主键** |

> **该文件没有机构/国家字段**（`Affiliations`、`Authors with affiliations` 都不存在），
> 因此报告图 2「作者国籍分布」改由 `overall.csv` 的面板数据生成，见
> [`REPRODUCE.md`](REPRODUCE.md#图-2作者国籍分布的数据来源)。
> 同名 `.xlsx` 版本未入库（内容相同，体积更大）。

### `overall.csv`

大小 33 KB，Scopus「Refine results」面板导出。结构为：标题行 + 检索式行 + 一张宽表，
表头形如 `"OPEN ACCESS",,"YEAR",,"AUTHOR NAME",...,`。
**不是标准 CSV，`pandas.read_csv` 会直接报错**，需要用 `csv` 模块按位解析，
因为数据行里含带逗号的引号字段（如 `"Regan, S.P."`）。
仓库中的 `solo_citations.figures.refine_panel()` 已实现该解析。

该文件不参与引文网络流水线，但它是报告图 1（全量发文量）与图 2（国家分布）的数据源。

---

## 4. `data/processed/` —— 最终结果

### `base3.csv`（**报告结论所依据的表**）

243 行 × 6 列：

| 列名 | 类型 | 说明 |
|---|---|---|
| `eid` | str | 目标文献 EID |
| `SCtot` | int | 独奏引用总数，等于 `network/<eid>_nodes.csv` 中 `SC` 列之和 |
| `Cited by` | int | 总被引次数 |
| `Year` | int | 发表年份，范围 1992–2024 |
| `Title` | str | 标题 |
| `Rate` | float | $R_{\mathrm{SC}} = \mathrm{SCtot} / \text{Cited by}$ |

已校验：243/243 行的 `SCtot` 与节点文件一致，`Rate` 与 `SCtot / Cited by` 完全吻合。

### `network/<eid>_nodes.csv`（243 个文件）

每篇目标文献一张节点表，约 24 MB / 266 个文件（含 23 个未进入 `base3.csv` 的论文）：

| 列名 | 说明 |
|---|---|
| `EID` | 网络中的节点，只保留合法 EID 格式 |
| `SC` | 1 = 该节点是目标文献的独奏式施引者；0 = 二重引用或其他 |

节点集合包含四类：目标文献自身、其参考文献、其施引文献、施引文献的参考文献。
规模差异很大，最大的 `2-s2.0-36449005127` 有 40 316 个节点、SC 合计 2068。

### `base1.csv` / `base1.xlsx` / `base2.xlsx`

结果的中间版本，保留用于溯源：

- `base1.csv`：**262 行 × 7 列**，即上述 Scopus 导出的精简副本
  （`Title, Year, Cited by, DOI, Link, Open Access, EID`），不含 SC 数据；
- `base1.xlsx`：**100 行 × 9 列**，在 `base1.csv` 的列之外加了手工整理的 `SCtot`、`rate`；
- `base2.xlsx`：**261 行 × 6 列**，`eid, SCtot, Cited by, Year, Title, Rate`。

三者都是最终 243 篇之前的中间版本，保留用于溯源；报告结论一律以 `base3.csv` 为准。

### `yearly_stats.csv`

由 `python scripts/plot_rate.py --csv data/processed/yearly_stats.csv` 生成，
每行一年（1992–2024），列为
`Year, rate, max_rate, min_rate, max_eid, max_eid_rate, min_eid, min_eid_rate, up_len, down_len, n, small`，
其中 `n` 是当年文献数，`small` 标记 `n < 3` 的年份。它是图 3 的数值底稿。

### `eid_sc_tot_legacy.csv` —— **历史产物，勿用于分析**

134 行 × 4 列（`eid, Year, SCtot, Cited by`），是流水线早期版本输出的汇总表。
它与 `base3.csv` 的 243 个 EID **零重叠**，来自另一个与本课题无关的文献集合，
因此不能与 `base3.csv` 混用。保留此文件只为记录开发过程，任何分析都不应引用它。

> 该文件的具体来源（哪一批文献、由哪个脚本误用）记录在
> [本地私人说明](PRIVATE-NOTES.md)中，不随仓库公开。

---

## 5. `legacy/` —— 历史数据留存

| 文件 | 内容 |
|---|---|
| `MLNL.csv` | 134 行 × 12 列，Scopus 导出，**与本研究无关** |
| `MLandLang.csv` | 109 行 × 12 列，同类导出 |

这两个文件是流水线早期调试期遗留的输入数据，不属于本研究的 243 篇样本，
仅作溯源保留。对应的 EID 与 `base3.csv` 无交集。

---

## 6. `data/interim/` —— 未入库的中间数据

采集阶段 ① ② 的输出，约 **250 MB、5.3 万个 CSV**，因此不随仓库分发：

```
data/interim/
├── <target_eid>/
│   ├── REFs.csv                        目标文献的参考文献，列 EID, DOI
│   ├── Cits.csv                        施引文献，列 EID, DOI
│   └── <target_eid>'sCitsREF/
│       └── <citing_eid>'sREFs.csv      某篇施引文献的参考文献，列 EID, DOI
├── done_b_eids.txt                     阶段①已完成的目标 EID
├── done_c_eids.txt                     阶段②已完成的目标 EID
├── failed_c_eids.csv                   阶段②有失败的目标 EID
└── scopus_cache/                       pybliometrics 请求缓存
```

规模分布（原课程目录中同一套数据的实测值）：

| 目录 | 文件数 | 大小 |
|---|---|---|
| 243 篇的逐篇抓取结果 | 40 755 | 84 MB |
| 134 篇的早期抓取结果 | 12 370 | 167 MB |

要重建全部数据，见 [`REPRODUCE.md`](REPRODUCE.md)。

---

## 7. 图表产物

| 文件 | 生成脚本 | 数据来源 |
|---|---|---|
| `report/figures/article_year.png` | `make_overview_figures.py --full-query` | `overall.csv` 的 `YEAR` 面板（全量 3138 篇），叠加 `base3.csv` 的 243 篇 |
| `report/figures/author_nation.png` | `make_overview_figures.py` | `overall.csv` 的 `COUNTRY` 面板 |
| `report/figures/washed_yearly_rate.png` | `plot_rate.py` | `base3.csv` |
| `report/figures/ustc_logo_*.{eps,pdf}` | — | 校徽素材，报告模板自带 |

> `article_year.png` 与 `author_nation.png` 是本次整理时**重新生成**的
> （原课程目录中没有生成它们的脚本）。重新生成的版本用全量 3138 篇替换了原先
> 只含 262 篇导出的版本，与报告正文「根据检索到的 3138 篇文献元数据绘制」的表述一致；
> 国家分布的新旧版本数值完全一致（1350/707/348/294/229）。
