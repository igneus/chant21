"""Unittests for the GABC to Volpiano converter

Todo:
    * Test conversion of example files
    * Test whether music can be empty
    * Test handling of accidentals at non-supported positions 
      (e.g. not b-flat or e-flat)
    * Test flat clefs
    * Test f2 clef
    * Test f1 clef?
"""
import unittest

from music21 import articulations
from music21 import converter
from music21 import note as note21
from music21 import clef as clef21

from chant21 import Note
from chant21 import Neume
from chant21 import Syllable
from chant21 import Alteration
from chant21 import Clef
from chant21 import NoMusic
from chant21 import ParserGABC
from chant21 import Pausa
from chant21 import PausaMinima
from chant21 import PausaMinor
from chant21 import PausaMajor
from chant21 import PausaFinalis

from arpeggio import visit_parse_tree as visitParseTree
from chant21.converterGABC import GABCVisitor
from chant21.converterGABC import gabcPositionToStep
from chant21.converterGABC import MissingClef

class TestFile(unittest.TestCase):
    def test_file(self):
        parser = ParserGABC(root='file')
        fileStr = 'title:Title!;\nattr1:value1;%%\n\n(c2) a(f)b(g) c(h)\ni(j)'
        parse = parser.parse(fileStr)
        chant = visitParseTree(parse, GABCVisitor())

        self.assertEqual(chant.metadata.title, 'Title!')

        ed = chant.editorial
        self.assertEqual(ed.title, 'Title!')
        self.assertEqual(ed.attr1, 'value1')
        
        notes = chant.flat.notes
        self.assertEqual(notes[0].name, 'C')
        self.assertEqual(notes[1].name, 'D')
        self.assertEqual(notes[2].name, 'E')
        self.assertEqual(notes[3].name, 'G')

    def test_fileWithoutHeader(self):
        parser = ParserGABC(root='file')
        fileStr = '(c2) a(f)b(g) c(h)\ni(j)'
        parse = parser.parse(fileStr)
        chant = visitParseTree(parse, GABCVisitor())
        notes = chant.flat.notes
        self.assertEqual(notes[0].name, 'C')
        self.assertEqual(notes[1].name, 'D')
        self.assertEqual(notes[2].name, 'E')
        self.assertEqual(notes[3].name, 'G')

    def test_header(self):
        parser = ParserGABC(root='header')
        parse = parser.parse('attr1: value1;\nattr2:value2;')
        header = visitParseTree(parse, GABCVisitor())
        target = dict(attr1='value1', attr2='value2')
        self.assertDictEqual(header, target)

    def test_multipleHeaders(self):
        parser = ParserGABC()
        fileStr = 'attr1:value1;\n%%\nattr2:value2;\n%%\n(c2) A(f)'
        parse = parser.parse(fileStr)
        chant = visitParseTree(parse, GABCVisitor())
        self.assertEqual(chant.editorial.attr1, 'value1')
        self.assertEqual(chant.editorial.attr2, 'value2')

class TestGABCPitchConversion(unittest.TestCase):
    def test_positions(self):
        self.assertEqual(gabcPositionToStep('c', 'c1'), 'B3')
        self.assertEqual(gabcPositionToStep('d', 'c1'), 'C4')
        self.assertEqual(gabcPositionToStep('e', 'c1'), 'D4')
        
        self.assertEqual(gabcPositionToStep('e', 'c2'), 'B3')
        self.assertEqual(gabcPositionToStep('f', 'c2'), 'C4')
        self.assertEqual(gabcPositionToStep('g', 'c2'), 'D4')
        self.assertEqual(gabcPositionToStep('h', 'c2'), 'E4')

        self.assertEqual(gabcPositionToStep('g', 'c3'), 'B4')
        self.assertEqual(gabcPositionToStep('h', 'c3'), 'C5')
        self.assertEqual(gabcPositionToStep('i', 'c3'), 'D5')

class TestAlterations(unittest.TestCase):
    def test_alterations(self):
        parser = ParserGABC(root='alteration')
        for alteration in 'xy#':
            parse = parser.parse(f'f{alteration}')
            element = visitParseTree(parse, GABCVisitor())
            ed = element.editorial
            self.assertIsInstance(element, Alteration)
            self.assertEqual(ed.gabcPosition, 'f')
            self.assertEqual(ed.gabcAlteration, alteration)

    def test_flats(self):
        parser = ParserGABC(root='body')    
        parse = parser.parse('(c2) a(exee,e)')
        stream = visitParseTree(parse, GABCVisitor())
        notes = stream.flat.notes
        self.assertEqual(notes[0].name, 'B-')
        self.assertEqual(notes[0].pitch.accidental.name, 'flat')
        self.assertEqual(notes[1].name, 'B-')
        self.assertEqual(notes[1].pitch.accidental.name, 'flat')
        self.assertEqual(notes[2].name, 'B')
        self.assertIsNone(notes[2].pitch.accidental)
    
    def test_naturals(self): 
        parser = ParserGABC(root='body')    
        parse = parser.parse('(c2) a(eexeeyee,e)')
        stream = visitParseTree(parse, GABCVisitor())
        notes = stream.flat.notes
        self.assertEqual(notes[0].name, 'B')
        self.assertEqual(notes[1].name, 'B-')
        self.assertEqual(notes[2].name, 'B')
        self.assertEqual(notes[3].name, 'B')
        self.assertEqual(notes[4].name, 'B')

        self.assertIsNone(notes[0].pitch.accidental)
        self.assertEqual(notes[1].pitch.accidental.name, 'flat')
        self.assertEqual(notes[2].pitch.accidental.name, 'natural')
        self.assertEqual(notes[3].pitch.accidental.name, 'natural')
        self.assertIsNone(notes[4].pitch.accidental)

    def test_breath_mark(self):
        """Test whether breath marks reset the accidentals"""
        parser = ParserGABC(root='body')    
        parse = parser.parse('(c2) (exe,fe)')
        stream = visitParseTree(parse, GABCVisitor())
        notes = stream.flat.notes
        self.assertEqual(notes[0].name, 'B-')
        self.assertEqual(notes[1].name, 'C')
        self.assertEqual(notes[2].name, 'B')

    def test_wordBoundaries(self):
        """Test whether word boundaries reset accidentals"""
        parser = ParserGABC(root='body')    
        parse = parser.parse('(c2) a(exfe) c(e)')
        stream = visitParseTree(parse, GABCVisitor())
        notes = stream.flat.notes
        self.assertEqual(notes[0].name, 'C')
        self.assertEqual(notes[1].name, 'B-')
        self.assertEqual(notes[2].name, 'B')
    
    def test_syllableBoundaries(self):
        """Test whether flats are NOT reset by syllable boundaries"""
        parser = ParserGABC(root='body')    
        parse = parser.parse('(c2) a(exe)b(e)')
        stream = visitParseTree(parse, GABCVisitor())
        notes = stream.flat.notes
        self.assertEqual(notes[0].name, 'B-')
        self.assertEqual(notes[1].name, 'B-')

    def test_flatClefs(self):
        """Test whether flats are NOT reset by syllable boundaries"""
        parser = ParserGABC(root='body')    
        parse = parser.parse('(cb2) (e)')
        stream = visitParseTree(parse, GABCVisitor())
        notes = stream.flat.notes
        self.assertEqual(notes[0].name, 'B-')

    def test_naturalsInFlatClefs(self):
        """Test whether naturals work in flat clefs"""
        parser = ParserGABC(root='body')    
        parse = parser.parse('(cb2) (eeyee,e) (e)')
        stream = visitParseTree(parse, GABCVisitor())
        notes = stream.flat.notes
        self.assertEqual(notes[0].name, 'B-')
        self.assertEqual(notes[1].name, 'B')
        self.assertEqual(notes[1].pitch.accidental.name, 'natural')
        self.assertEqual(notes[2].name, 'B')
        self.assertEqual(notes[2].pitch.accidental.name, 'natural')
        self.assertEqual(notes[3].name, 'B-')
        self.assertEqual(notes[3].pitch.accidental.name, 'flat')
        self.assertEqual(notes[4].name, 'B-')
        self.assertEqual(notes[4].pitch.accidental.name, 'flat')

    def test_polyphonicAlterations(self):
        parser = ParserGABC(root='music')
        parse = parser.parse('f{ix}g')
        elements = visitParseTree(parse, GABCVisitor())
        n1, alt, n2 = elements
        self.assertIsInstance(n1, Neume)
        self.assertIsInstance(alt, Alteration)
        self.assertIsInstance(n2, Neume)

class TestText(unittest.TestCase):

    def test_text(self):
        parser = ParserGABC(root='body')    
        parse = parser.parse('a(c2) word(e)1(f) word2(g)')
        chant = visitParseTree(parse, GABCVisitor())
        w1, w2, w3 = chant[0]
        self.assertEqual(w1.text, 'a')
        self.assertEqual(w2.text, 'word1')
        self.assertEqual(w3.text, 'word2')

        syll1, syll2 = w2.elements
        self.assertEqual(syll1.text, 'word')
        self.assertEqual(syll2.text, '1')
        self.assertEqual(syll1.flat.notes[0].lyric, 'word')
        self.assertEqual(syll2.flat.notes[0].lyric, '1')

    def test_textAfterAccidental(self):
        parser = ParserGABC(root='body')    
        parse = parser.parse('(c2) bla(eye)')
        chant = visitParseTree(parse, GABCVisitor())
        word1, word2 = chant[0]
        self.assertIsNone(word1.text)
        self.assertEqual(word2.text, 'bla')
        note = word2.flat.notes[0]
        self.assertEqual(note.lyric, 'bla')
    
    def test_singleSyllable(self):
        parser = ParserGABC(root='word')    
        parse = parser.parse('s1(f)')
        word = visitParseTree(parse, GABCVisitor())
        n = word.flat.notes[0]
        self.assertEqual(n.lyrics[0].syllabic, 'single')

    def test_twoSyllables(self):
        parser = ParserGABC(root='word')    
        parse = parser.parse('s1(f)s2(f)')
        word = visitParseTree(parse, GABCVisitor())
        syll1, syll2 = word.syllables
        lyric1 = syll1.flat.notes[0].lyrics[0]
        lyric2 = syll2.flat.notes[0].lyrics[0]
        self.assertEqual(lyric1.syllabic, 'begin')
        self.assertEqual(lyric2.syllabic, 'end')

    def test_threeOrMoreSyllables(self):
        parser = ParserGABC(root='word')    
        parse = parser.parse('s1(f)s2(f)s3(g)s4(f)')
        word = visitParseTree(parse, GABCVisitor())
        s1, s2, s3, s4 = word.syllables
        lyric1 = s1.flat.notes[0].lyrics[0]
        lyric2 = s2.flat.notes[0].lyrics[0]
        lyric3 = s3.flat.notes[0].lyrics[0]
        lyric4 = s4.flat.notes[0].lyrics[0]
        self.assertEqual(lyric1.syllabic, 'begin')
        self.assertEqual(lyric2.syllabic, 'middle')
        self.assertEqual(lyric3.syllabic, 'middle')
        self.assertEqual(lyric4.syllabic, 'end')

class TestBarClefs(unittest.TestCase):
    def test_pausa(self):
        parser = ParserGABC(root='pausa')
        pausaTypes = [
            (PausaFinalis, ['::']),
            (PausaMajor, [':', ':?', ':\'']),
            (PausaMinor, [';', ';1', ';2']),
            (PausaMinima, [',', ',_', ',0', ',1', '`'])
        ]
        for pausaClass, examples in pausaTypes:
            for gabc in examples:
                parse = parser.parse(gabc)
                element = visitParseTree(parse, GABCVisitor())
                self.assertIsInstance(element, pausaClass)
                self.assertEqual(element.editorial.gabc, gabc)
        
    def test_measures(self):
        parser = ParserGABC(root='body')
        parse = parser.parse('(c2) a(f) (:) b(g)')
        ch = visitParseTree(parse, GABCVisitor())
        self.assertEqual(len(ch), 2)
        m1, m2 = ch
        ed = m1.rightBarline.editorial
        self.assertEqual(ed.gabc, ':')

    def test_clefs(self):
        parser = ParserGABC(root='clef')
        for clef in ['c1', 'c2', 'c3', 'c4', 'f3', 'f4', 'cb3', 'cb4']:
            parse = parser.parse(clef)
            element = visitParseTree(parse, GABCVisitor())
            self.assertIsInstance(element, clef21.TrebleClef)
            self.assertEqual(element.editorial.gabc, clef)

    def test_missingClef(self):
        parser = ParserGABC(root='body')
        parse = parser.parse('a(fgf)')
        test_fn = lambda: visitParseTree(parse, GABCVisitor())
        self.assertRaises(MissingClef, test_fn)

    # def test_barlinePosition(self):
    #     gabc = "(f3) AL(ef~)le(fg/hggf)lú(ef~)ia.(f.) <sp>V/</sp>.(::) Ve(e!fwg/hggf/e_f)ni(f.) (,) "
    #     # gabc = "(f3) AL(ef~)le(fg/hggf)lú(ef~)ia.(f.) <sp>V/</sp>.(::) <alt>Hic genuflectitur.</alt>Ve(e!fwg/hggf/e_f)ni(f.) (,) San(f)cte(g!hwi) Spí(iv./hig/hfg)ri(gef)tus,(f.)"
    #     gabc = "(f3) A(fg/gh) *(:) B(f)C(g) (:) D(h) (::)"
    #     parser = ParserGABC(root='body')
    #     parse = parser.parse(gabc)

    #     ch = visitParseTree(parse, GABCVisitor())

    #     print(ch)

class TestSyllables(unittest.TestCase):
    def test_syllable(self):
        parser = ParserGABC(root='syllable')
        parse = parser.parse('A(fg)')
        syllable = visitParseTree(parse, GABCVisitor())
        self.assertEqual(syllable.text, 'A')
        self.assertEqual(len(syllable.flat.notes), 2)
        self.assertEqual(len(syllable), 1)

    def test_multipleNeumes(self):
        parser = ParserGABC(root='syllable')
        parse = parser.parse('A(fg/fg)')
        syllable = visitParseTree(parse, GABCVisitor())
        self.assertEqual(syllable.text, 'A')
        self.assertEqual(len(syllable.flat.notes), 4)
        self.assertEqual(len(syllable), 2)
        
    def test_syllablesWithCommas(self):
        parser = ParserGABC(root='word')    
        gabc = 'a(f)(,)(f)b(f)(,)(f)c(g)'
        parse = parser.parse(gabc)
        word = visitParseTree(parse, GABCVisitor())
        self.assertEqual(len(word), 3)
        syll1, syll2, syll3 = word.elements
        self.assertEqual(len(syll1.flat), 3)
        self.assertIsInstance(syll1.flat[1], Pausa)
        self.assertEqual(len(syll2.flat), 3)
        self.assertIsInstance(syll2.flat[1], Pausa)
        self.assertEqual(len(syll3.flat), 1)
                
class TestNeumes(unittest.TestCase):

    def test_singleNeume(self):
        parser = ParserGABC(root='music')
        parse = parser.parse('fgf')
        elements = visitParseTree(parse, GABCVisitor())
        self.assertEqual(len(elements), 1)
        
        neume = elements[0]
        self.assertEqual(len(neume), 3)
        self.assertIsInstance(neume[0], note21.Note)
        self.assertIsInstance(neume[1], note21.Note)
        self.assertIsInstance(neume[2], note21.Note)
        self.assertEqual(neume[0].editorial.gabcPosition, 'f')
        self.assertEqual(neume[1].editorial.gabcPosition, 'g')
        self.assertEqual(neume[2].editorial.gabcPosition, 'f')

    def test_multipleNeumes(self):
        parser = ParserGABC(root='music')
        parse = parser.parse('eh/hi')
        elements = visitParseTree(parse, GABCVisitor())
        self.assertEqual(len(elements), 2)
        self.assertIsInstance(elements[0], Neume)
        self.assertEqual(len(elements[0]), 2)
        self.assertIsInstance(elements[1], Neume)
        self.assertEqual(len(elements[1]), 2)

    def test_articulationBeforeComma(self):
        parser = ParserGABC(root='body')
        parse = parser.parse("(c2) A(a,d)")
        ch = visitParseTree(parse, GABCVisitor())
        clef, n1, pausa, n2 = ch.flat
        self.assertIsInstance(clef, Clef)
        self.assertIsInstance(n1, Note)
        self.assertIsInstance(pausa, PausaMinima)
        self.assertIsInstance(n2, Note)
        self.assertEqual(len(n1.articulations), 1)
        self.assertEquals(n1.articulations[0], pausa)
    
class TestNotes(unittest.TestCase):
    
    def test_noteSuffixes(self):
        parser = ParserGABC(root='note')
        parse = parser.parse('fs<.')
        note = visitParseTree(parse, GABCVisitor())
        ed = note.editorial
        self.assertEqual(ed.gabcPosition, 'f')
        self.assertTrue({'neumeShape': 's<'} in ed.gabcSuffixes)
        self.assertTrue({'rhythmicSign': '.'} in ed.gabcSuffixes)
    
    def test_notePrefix(self):
        parser = ParserGABC(root='note')
        parse = parser.parse('-f')
        note = visitParseTree(parse, GABCVisitor())
        ed = note.editorial
        self.assertEqual(ed.gabcPosition, 'f')
        self.assertEqual(ed.gabcPrefix, '-')
        self.assertTrue(ed.liquescence)

    def test_positions(self):
        parser = ParserGABC(root='position')
        for position in 'abcdefghijklmABCDEFGHIJKLM':
            parse = parser.parse(position)
            output = visitParseTree(parse, GABCVisitor())
            self.assertEqual(output, position)

    def test_emptyNotes(self):
        parser = ParserGABC(root='note')
        parse = parser.parse('gr')
        n = visitParseTree(parse, GABCVisitor())
        self.assertFalse(n.noteheadFill, False)
        self.assertTrue({'emptyNote': 'r'} in n.editorial.gabcSuffixes)

    def test_multipleSuffixes(self):
        parser = ParserGABC(root='note')
        parse = parser.parse('go1')
        n = visitParseTree(parse, GABCVisitor())
        suffixes = n.editorial.gabcSuffixes
        self.assertTrue({'neumeShape': 'o'} in suffixes)
        self.assertTrue({'neumeShape': '1'} in suffixes)
        self.assertEqual(n.editorial.gabcPosition, 'g')

        print(n)

class TestIgnoredFeatures(unittest.TestCase):
    def test_macros(self):
        """Test whether a file with macro's is converted properly despite them"""
        parser = ParserGABC(root='file')
        parse = parser.parse('%%\ndef-m1:\grealign;\ndef-m2:\grealign;\n(c2) a(f)')
        elements = visitParseTree(parse, GABCVisitor())
        self.assertTrue(True)

class TestConverter(unittest.TestCase):

    def test_conversion(self):
        gabc = '(c2) a(f)b(g) c(h)\ni(j)'
        chant = converter.parse(gabc, format='GABC')
        notes = chant.flat.notes
        self.assertEqual(notes[0].name, 'C')
        self.assertEqual(notes[1].name, 'D')
        self.assertEqual(notes[2].name, 'E')
        self.assertEqual(notes[3].name, 'G')


    def test_conversionFileContents(self):
        fileStr = 'title:Title!;\nattr1:value1;%%\n\n(c2) a(f)b(g) c(h)\ni(j)'
        chant = converter.parse(fileStr, format='GABC')
        notes = chant.flat.notes
        self.assertEqual(notes[0].name, 'C')
        self.assertEqual(notes[1].name, 'D')
        self.assertEqual(notes[2].name, 'E')
        self.assertEqual(notes[3].name, 'G')

if __name__ == '__main__':
    unittest.main()