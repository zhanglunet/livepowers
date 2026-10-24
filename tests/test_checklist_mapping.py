"""PRD-147/T3：E 条目 ↔ PRD-094 C 条目映射文档的一致性测试。

校验 docs/engineering-checklist/prd-094-mapping.md：
- 映射引用的 ID 在两侧都存在（E 条目 ∈ scripts/eng_checklist.py 的 ITEMS；
  C 条目 ∈ docs/PRD-094-store-checklist.md 条目表）；
- 正向表 19 条 E 条目全量、无重复、无未知 ID；反向表 C-01–C-31 全量、无重复；
- 双向互查：正向表引用的 C 条目集合 == 反向表中标注了 E 条目的 C 条目集合，
  且逐条 E 列表一致（防止两表漂移）；
- 格式校验：E 编号 E-[TDXS]\\d{2}、C 编号 C-\\d{2}，关系列取值合法。
"""
import importlib.util
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAPPING = REPO / "docs" / "engineering-checklist" / "prd-094-mapping.md"
C_CHECKLIST = REPO / "docs" / "PRD-094-store-checklist.md"

SCRIPT = REPO / "scripts" / "eng_checklist.py"
_spec = importlib.util.spec_from_file_location("eng_checklist", SCRIPT)
ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ec)

E_ID = re.compile(r"^E-[TDXS]\d{2}$")
C_ID = re.compile(r"^C-\d{2}$")
RELATIONS = {"同判定", "延伸", "新增"}


def parse_table(text, start_marker, id_regex):
    """解析 start_marker 之后第一张 markdown 表：[(首列, 其余列 list), ...]。

    首列必须逐行匹配 id_regex（表头/分隔行跳过）；不匹配即抛 ValueError——
    表里混进未知编号属于文档错误，测试直接失败并指出行号。
    """
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if start_marker in ln)
    rows = []
    for i in range(start, len(lines)):
        ln = lines[i]
        if not ln.startswith("|"):
            if rows:
                break  # 表已结束
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ":", " "} or cells[0] in ("E 条目", "C 条目"):
            continue  # 表头或分隔行
        if not id_regex.match(cells[0]):
            raise ValueError("第 %d 行首列不是合法编号：%r" % (i + 1, cells[0]))
        rows.append((cells[0], cells[1:]))
    if not rows:
        raise ValueError("start_marker 之后没解析到表行：%s" % start_marker)
    return rows


def forward_c_ids(cells):
    """正向表「C 条目」列 -> C 编号列表（— 表示无）。"""
    col = cells[0]
    if col == "—":
        return []
    ids = col.split()
    for cid in ids:
        if not C_ID.match(cid):
            raise ValueError("正向表 C 列混入非法编号：%r" % col)
    return ids


class TestMappingDoc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MAPPING.read_text(encoding="utf-8")
        cls.forward = parse_table(cls.text, "## 2. 正向表", E_ID)
        cls.reverse = parse_table(cls.text, "## 3. 反向覆盖表", C_ID)
        # 两侧权威来源：机检脚本 ITEMS 与 PRD-094 条目表。
        cls.item_e = dict(ec.ITEMS)
        c_text = C_CHECKLIST.read_text(encoding="utf-8")
        cls.item_c = set(re.findall(r"^\| (C-\d{2}) \|", c_text, re.M))

    def test_doc_exists_and_mentions_t3(self):
        self.assertTrue(MAPPING.exists())
        self.assertIn("#737", self.text)

    # --- 正向表（E → C）---

    def test_forward_covers_all_items_exactly_once(self):
        ids = [r[0] for r in self.forward]
        self.assertEqual(sorted(ids), sorted(self.item_e))
        self.assertEqual(len(ids), len(set(ids)), "正向表 E 条目有重复")

    def test_forward_ids_exist_in_script(self):
        for eid, _ in self.forward:
            self.assertIn(eid, self.item_e, "%s 不在 eng_checklist.py ITEMS 里" % eid)

    def test_forward_relation_values(self):
        for eid, cells in self.forward:
            self.assertIn(cells[1], RELATIONS,
                          "%s 关系列非法：%r" % (eid, cells[1]))

    def test_forward_c_ids_exist_in_prd094(self):
        for eid, cells in self.forward:
            for cid in forward_c_ids(cells):
                self.assertIn(cid, self.item_c,
                              "%s 引用的 %s 不在 PRD-094 条目表里" % (eid, cid))

    # --- 反向覆盖表（C → 处置）---

    def test_reverse_covers_c01_to_c31_exactly_once(self):
        ids = [r[0] for r in self.reverse]
        expected = ["C-%02d" % i for i in range(1, 32)]
        self.assertEqual(ids, expected, "反向表必须按 C-01..C-31 全量且各一次")
        self.assertTrue(self.item_c.issuperset(set(expected)))

    def test_reverse_e_ids_exist_in_script(self):
        for cid, cells in self.reverse:
            if cells[1] == "—":
                continue
            for eid in cells[1].split():
                self.assertTrue(E_ID.match(eid),
                                "%s 的 E 列非法：%r" % (cid, cells[1]))
                self.assertIn(eid, self.item_e,
                              "%s 引用的 %s 不在 ITEMS 里" % (cid, eid))

    def test_reverse_disposition_values(self):
        for cid, cells in self.reverse:
            if cells[1] == "—":
                self.assertTrue(cells[2].startswith("收录侧自管"),
                                "%s 无 E 映射时处置必须是收录侧自管" % cid)
            else:
                self.assertNotIn("收录侧自管", cells[2],
                                 "%s 有 E 映射却标收录侧自管" % cid)

    # --- 双向互查 ---

    def test_bidirectional_consistency(self):
        fwd = {}
        for eid, cells in self.forward:
            for cid in forward_c_ids(cells):
                fwd.setdefault(cid, []).append(eid)
        for cid, cells in self.reverse:
            listed = [] if cells[1] == "—" else cells[1].split()
            self.assertEqual(sorted(listed), sorted(fwd.get(cid, [])),
                             "%s 两表不一致：正向=%s 反向=%s"
                             % (cid, sorted(fwd.get(cid, [])), sorted(listed)))

    def test_referenced_count_matches_summary(self):
        listed = [r[0] for r in self.reverse if r[1][1] != "—"]
        self.assertEqual(len(listed), 10, "文档口径：被 E 引用的 C 条目共 10 条")
        self.assertEqual(len(self.reverse) - len(listed), 21)


class TestParserGuards(unittest.TestCase):
    """parse_table 对坏表的护栏：防止测试本身静默放过漂移的文档。"""

    def test_rejects_bad_id_row(self):
        with self.assertRaises(ValueError):
            parse_table("| E-T01 | C-30 |\n| E-XX | C-30 |", "|", E_ID)

    def test_empty_table_raises(self):
        with self.assertRaises(ValueError):
            parse_table("## 没有表的小节\n\n只有文字。", "## 没有表", E_ID)

    def test_forward_c_ids_rejects_garbage(self):
        with self.assertRaises(ValueError):
            forward_c_ids(["C-30；C-31"])


if __name__ == "__main__":
    unittest.main()
