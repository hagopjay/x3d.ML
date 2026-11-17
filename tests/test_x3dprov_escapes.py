"""Provenance JSON is data, including backslashes and embedded newlines."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import x3dprov


class LiteralMetadata(unittest.TestCase):
    XML = '<X3D profile="Interchange" version="4.0"><head></head><Scene><WorldInfo title="fixture"/></Scene></X3D>'

    def check_note(self, note):
        stamped = x3dprov.add_step(self.XML, {'op': 'generate', 'note': note})
        self.assertEqual(x3dprov.summary(stamped)[0]['note'], note)
        linked = x3dprov.add_step(stamped, {'op': 'validate', 'note': note})
        self.assertEqual(x3dprov.summary(linked)[1]['note'], note)
        self.assertEqual(x3dprov.verify(linked)['status'], 'verified')
        self.assertEqual(x3dprov.content_hash(self.XML), x3dprov.content_hash(linked))

    def test_newline(self):
        self.check_note('first line\nsecond line')

    def test_windows_path(self):
        self.check_note(r'C:\research\new\unit')

    def test_literal_replacement_syntax(self):
        self.check_note(r'\g<0> and \1 remain literal')

    def test_quotes_markup_and_unicode(self):
        self.check_note('α / 科学 / "quoted" / <value> & more')

    def test_tab_and_control_escape(self):
        self.check_note('one\ttwo\u0001three')


if __name__ == '__main__':
    unittest.main()
