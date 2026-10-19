"""快照更新必须保护人工修改，且安装产物不得依赖兄弟仓库。"""
import importlib.util
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_skills', ROOT / 'scripts/sync_skills.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SnapshotTest(unittest.TestCase):
    def source(self, root):
        source = root / 'source'
        source.mkdir()
        for name, text in {'catalog.json': '{"version":"0.1.0"}', 'source-lock.json': '{}',
                           'docs/upstream-repositories.json': '[]', 'NOTICE': 'notice', 'LICENSE': 'license',
                           'scripts/validate_package.py': 'pass',
                           'skills/easyeda-api/SKILL.md': 'first version'}.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return source

    def test_snapshot_is_self_contained_and_detects_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source(root)
            plugin = root / 'plugin'
            plugin.mkdir()
            module.sync(source, root=plugin)
            self.assertEqual((plugin / 'skills/easyeda-api/SKILL.md').read_text(), 'first version')
            self.assertFalse(any(p.is_symlink() for p in plugin.rglob('*')))
            module.sync(source, check=True, root=plugin)
            (plugin / 'skills/easyeda-api/SKILL.md').write_text('user edit')
            with self.assertRaisesRegex(ValueError, '人工修改'):
                module.sync(source, root=plugin)
            self.assertEqual((plugin / 'skills/easyeda-api/SKILL.md').read_text(), 'user edit')

    def test_tracked_update_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source(root)
            plugin = root / 'plugin'
            plugin.mkdir()
            module.sync(source, root=plugin)
            (source / 'skills/easyeda-api/SKILL.md').write_text('second version')
            module.sync(source, root=plugin)
            self.assertEqual((plugin / 'skills/easyeda-api/SKILL.md').read_text(), 'second version')

    def test_parent_symlink_cannot_overwrite_another_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source(root)
            plugin = root / 'plugin'
            plugin.mkdir()
            outside = root / 'outside'
            outside.mkdir()
            (outside / 'easyeda-api').mkdir()
            protected = outside / 'easyeda-api/SKILL.md'
            protected.write_text('first version')
            (plugin / 'skills').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, '目标'):
                module.sync(source, root=plugin)
            self.assertEqual(protected.read_text(), 'first version')


if __name__ == '__main__':
    unittest.main()
