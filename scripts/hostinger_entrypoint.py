"""Resolve the shipped entry module; lazy chunks may also be named index-*.js."""
from html.parser import HTMLParser
from pathlib import Path


def entry_bundle(root=Path('.')):
    class Scripts(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sources = []

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == 'script' and values.get('type') == 'module' and values.get('src'):
                self.sources.append(values['src'])

    parser = Scripts()
    parser.feed((root / 'index.html').read_text())
    if len(parser.sources) != 1:
        raise SystemExit('Expected exactly one entry module in index.html')
    source = parser.sources[0]
    if not source.startswith('/assets/') or '?' in source or '#' in source:
        raise SystemExit('Entry module must be a local /assets/ file')
    entry = (root / source.lstrip('/')).resolve()
    if not entry.is_relative_to((root / 'assets').resolve()) or entry.suffix != '.js' or not entry.is_file():
        raise SystemExit('Entry module is missing or outside assets/')
    return entry
