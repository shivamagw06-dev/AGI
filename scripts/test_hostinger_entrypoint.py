import tempfile
import unittest
from pathlib import Path
from hostinger_entrypoint import entry_bundle


class EntrypointTests(unittest.TestCase):
    def test_uses_html_entry_not_last_alphabetic_chunk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            (root / 'assets/index-aaa.js').write_text('application')
            (root / 'assets/index-zzz.js').write_text('library')
            (root / 'index.html').write_text('<script crossorigin src="/assets/index-aaa.js" type="module"></script>')
            self.assertEqual(entry_bundle(root).read_text(), 'application')

    def test_missing_ambiguous_and_external_entries_fail_closed(self):
        for html in ['', '<script type="module" src="https://example.com/a.js"></script>',
                     '<script type="module" src="/assets/missing.js"></script>',
                     '<script type="module" src="/assets/a.js"></script><script type="module" src="/assets/b.js"></script>']:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'index.html').write_text(html)
                with self.assertRaises(SystemExit):
                    entry_bundle(root)


if __name__ == '__main__':
    unittest.main()
