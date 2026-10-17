"""plugins/*/skills/ 与仓库根 skills/ 逐字节一致（PR #32 拆分拷贝防漂移）。

PR #32 把 19 个 skill 拆成 5 个主题插件目录，plugins/<p>/skills/ 是
仓库根 skills/ 的实份拷贝。本测试断言两者逐字节一致：任何一边的
悄悄修改都会让测试变红，提醒同步另一边。

注意：PR #32 未合并时仓库里没有 plugins/ 目录，此时跳过（不是失败）。
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class PluginSync(unittest.TestCase):
    def test_plugin_skill_copies_in_sync(self):
        plugins_root = REPO / "plugins"
        copies = (sorted(plugins_root.glob("*/skills/*/*"))
                  if plugins_root.is_dir() else [])
        copies = [p for p in copies if p.is_file()]
        if not copies:
            self.skipTest("plugins/*/skills/ 不存在（PR #32 未合并），跳过")
        mismatched, missing = [], []
        for pf in copies:
            # pf = plugins/<plugin>/skills/<skill>/<file>
            rel = pf.relative_to(pf.parents[2] / "skills")
            root_f = REPO / "skills" / rel
            if not root_f.is_file():
                missing.append(str(pf))
            elif pf.read_bytes() != root_f.read_bytes():
                mismatched.append(str(pf))
        self.assertEqual(missing, [], "插件拷贝在根 skills/ 里找不到对应文件：%s" % missing)
        self.assertEqual(mismatched, [], "插件拷贝与根 skills/ 内容不一致（漂移）：%s" % mismatched)

    def test_every_root_skill_has_plugin_copy(self):
        """反向：根 skills/ 的每个 skill 至少被一个插件收录（防拆分遗漏）。"""
        plugins_root = REPO / "plugins"
        if not plugins_root.is_dir():
            self.skipTest("plugins/ 不存在（PR #32 未合并），跳过")
        covered = {p.name for p in plugins_root.glob("*/skills/*") if p.is_dir()}
        root_skills = {p.name for p in (REPO / "skills").iterdir() if p.is_dir()}
        self.assertEqual(root_skills - covered, set(),
                         "这些 skill 未被任何插件收录：%s" % (root_skills - covered))


if __name__ == "__main__":
    unittest.main()
