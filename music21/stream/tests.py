# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Name:         stream/tests.py
# Purpose:      Tests for streams
#
# Authors:      Michael Scott Asato Cuthbert
#               Christopher Ariza
#
# Copyright:    Copyright © 2009-2024 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
from __future__ import annotations

import copy
import os
import random
import unittest

import music21
from music21.note import GeneralNote

from music21.stream.base import StreamException
from music21.stream.base import Stream
from music21.stream.base import Voice
from music21.stream.base import Measure
from music21.stream.base import Score
from music21.stream.base import Part
from music21.stream.base import Opus

from music21 import bar
from music21 import beam
from music21 import chord
from music21 import clef
from music21 import common
from music21 import converter
from music21 import corpus
from music21 import defaults
from music21 import duration
from music21 import dynamics
from music21 import environment
from music21 import expressions
from music21 import instrument
from music21 import interval
from music21 import layout
from music21 import key
from music21 import metadata
from music21 import meter
from music21 import note
from music21 import pitch
from music21 import sites
from music21 import spanner
from music21 import tempo
from music21 import text
from music21 import tie
from music21 import variant

from music21.base import Music21Exception, _SplitTuple

from music21.musicxml import m21ToXml

from music21.midi import translate as midiTranslate

environLocal = environment.Environment('stream.tests')


# ------------------------------------------------------------------------------
class TestExternal(unittest.TestCase):
    show = True

    def testLilySimple(self):
        a = Stream()
        ts = meter.TimeSignature('3/4')

        b = Stream()
        q = note.Note(type='quarter')
        q.octave = 5
        b.repeatInsert(q, [0, 1, 2, 3])

        bestC = clef.bestClef(b, allowTreble8vb=True)
        a.insert(0, bestC)
        a.insert(0, ts)
        a.insert(0, b)

        if self.show:
            a.show('lily.png')

    def testLilySemiComplex(self):
        a = Stream()
        ts = meter.TimeSignature('3/8')

        b = Stream()
        q = note.Note(type='eighth')

        dur1 = duration.Duration()
        dur1.type = 'eighth'

        tup1 = duration.Tuplet()
        tup1.tupletActual = [5, dur1]
        tup1.tupletNormal = [3, dur1]

        q.octave = 2
        q.duration.appendTuplet(tup1)

        for i in range(5):
            b.append(copy.deepcopy(q))
            b.elements[i].accidental = pitch.Accidental(i - 2)

        b.elements[0].duration.tuplets[0].type = 'start'
        b.elements[-1].duration.tuplets[0].type = 'stop'
        b.elements[2].lyric = 'a real C'

        bestC = clef.bestClef(b, allowTreble8vb=True)
        a.insert(0, bestC)
        a.insert(0, ts)
        a.insert(0, b)
        if self.show:
            a.show('lily.png')

    def testScoreLily(self):
        '''
        Test the lilypond output of various score operations.
        '''
        c = note.Note('C4')
        d = note.Note('D4')
        ts = meter.TimeSignature('2/4')
        s1 = Part()
        s1.append(copy.deepcopy(c))
        s1.append(copy.deepcopy(d))
        s2 = Part()
        s2.append(copy.deepcopy(d))
        s2.append(copy.deepcopy(c))
        score1 = Score()
        score1.insert(ts)
        score1.insert(s1)
        score1.insert(s2)
        if self.show:
            score1.show('lily.png')

    def testMXOutput(self):
        '''
        A simple test of adding notes to measures in a stream.
        '''
        c = Stream()
        for dummy in range(4):
            b = Measure()
            for p in ['a', 'g', 'c#', 'a#']:
                a = note.Note(p)
                b.append(a)
            c.append(b)
        if self.show:
            c.show()

    def testMxMeasures(self):
        '''
        A test of the automatic partitioning of notes in a measure and the creation of ties.
        '''

        n = note.Note()
        n.quarterLength = 3
        a = Stream()
        a.repeatInsert(n, list(range(0, 120, 3)))
        # a.show()  # default time signature used

        a.insert(0, meter.TimeSignature('5/4'))
        a.insert(10, meter.TimeSignature('2/4'))
        a.insert(3, meter.TimeSignature('3/16'))
        a.insert(20, meter.TimeSignature('9/8'))
        a.insert(40, meter.TimeSignature('10/4'))
        if self.show:
            a.show()

    def testMultipartStreams(self):
        '''
        Test the creation of multipart streams by simply having streams within streams.
        '''
        q = Stream()
        r = Stream()
        for x in ['c3', 'a3', 'g#4', 'd2'] * 10:
            n = note.Note(x)
            n.quarterLength = 0.25
            q.append(n)

            m = note.Note(x)
            m.quarterLength = 1.125
            r.append(m)

        s = Stream()  # container
        s.insert(q)
        s.insert(r)
        s.insert(0, meter.TimeSignature('3/4'))
        s.insert(3, meter.TimeSignature('5/4'))
        s.insert(8, meter.TimeSignature('3/4'))

        if self.show:
            s.show()

    def testMultipartMeasures(self):
        '''
        This demonstrates obtaining slices from a stream and layering
        them into individual parts.
        '''
        k155_score = corpus.parse('mozart/k155', 2)
        start_measure = 0
        end_measure = 16

        violin_i_id = k155_score.parts[0].id
        violin_i_part = k155_score[violin_i_id]
        violin_i_part_slice = violin_i_part[start_measure:end_measure + 1]

        violin_ii_id = k155_score.parts[1].id
        violin_ii_part = k155_score[violin_ii_id]
        violin_ii_part_slice = violin_ii_part[start_measure:end_measure + 1]

        viola_part_id = k155_score.parts[2].id
        viola_part = k155_score[viola_part_id]
        viola_part_slice = viola_part[start_measure:end_measure + 1]

        s = Stream()
        s.append(violin_i_part_slice)
        s.append(violin_ii_part_slice)
        s.append(viola_part_slice)
        if self.show:
            s.show()

    def testCanons(self):
        '''
        A test of creating a canon with shifted presentations of a source melody.
        This also demonstrates
        the addition of rests to parts that start late or end early.

        The addition of rests happens with makeRests(), which is called in
        musicxml generation of a Stream.
        '''

        a = ['c', 'g#', 'd-', 'f#', 'e', 'f'] * 4

        s = Stream()
        partOffsetShift = 1.25
        partOffset = 0
        for junk in range(6):
            p = Stream()
            for pitchName in a:
                n = note.Note(pitchName)
                n.quarterLength = 1.5
                p.append(n)
            p.offset = partOffset
            s.insert(p)
            partOffset += partOffsetShift

        if self.show:
            s.show()

    def testBeamsPartial(self):
        '''
        This demonstrates a partial beam; a beam that is not connected between more than one note.
        '''
        q = Stream()
        for x in [0.125, 0.25, 0.25, 0.125, 0.125, 0.125] * 30:
            n = note.Note('c')
            n.quarterLength = x
            q.append(n)

        s = Stream()  # container
        s.insert(q)

        s.insert(0, meter.TimeSignature('3/4'))
        s.insert(3, meter.TimeSignature('5/4'))
        s.insert(8, meter.TimeSignature('4/4'))

        if self.show:
            s.show()

    def testBeamsStream(self):
        '''
        A test of beams applied to different time signatures.
        '''
        q = Stream()
        r = Stream()
        p = Stream()
        for x in ['c3', 'a3', 'c#4', 'd3'] * 30:
            n = note.Note(x)
            # n.quarterLength = random.choice([0.25, 0.125, 0.5])
            n.quarterLength = random.choice([0.25])
            q.append(n)
            m = note.Note(x)
            m.quarterLength = 0.5
            r.append(m)
            o = note.Note(x)
            o.quarterLength = 0.125
            p.append(o)

        s = Stream()  # container
        s.append(q)
        s.append(r)
        s.append(p)

        s.insert(0, meter.TimeSignature('3/4'))
        s.insert(3, meter.TimeSignature('5/4'))
        s.insert(8, meter.TimeSignature('4/4'))
        self.assertEqual(len(s.recurse().notes), 360)

        if self.show:
            s.show()

    def testBeamsMeasure(self):
        aMeasure = Measure()
        aMeasure.timeSignature = meter.TimeSignature('4/4')
        aNote = note.Note()
        aNote.quarterLength = 0.25
        aMeasure.repeatAppend(aNote, 16)
        bMeasure = aMeasure.makeBeams()
        if self.show:
            bMeasure.show()


# ------------------------------------------------------------------------------
class Test(unittest.TestCase):

    def testIsFlat(self):
        a = Stream()
        for dummy in range(5):
            a.insert(0, music21.Music21Object())
        self.assertTrue(a.isFlat)
        a[2] = note.Note('C#')
        self.assertTrue(a.isFlat)
        a[3] = Stream()
        self.assertFalse(a.isFlat)

    def testAppendFails(self):
        a = Stream()
        others = [music21.Music21Object(), 'hello']
        with self.assertRaises(StreamException) as context:
            a.append(others)
        self.assertIn("'hello'", str(context.exception))


    def testSort(self):
        s = Stream()
        s.repeatInsert(note.Note('C#'), [0.0, 2.0, 4.0])
        s.repeatInsert(note.Note('D-'), [1.0, 3.0, 5.0])
        self.assertFalse(s.isSorted)
        y = s.sorted()
        self.assertTrue(y.isSorted)
        g = ''
        for myElement in y:
            g += f'{myElement.offset}: {myElement.name}; '
        self.assertEqual(g, '0.0: C#; 1.0: D-; 2.0: C#; 3.0: D-; 4.0: C#; 5.0: D-; ')

    def testFlatSimple(self):
        s1 = Score()
        s1.id = 's1'

        p1 = Part()
        p1.id = 'p1'

        p2 = Part()
        p2.id = 'p2'

        n1 = note.Note('C', type='half')
        n2 = note.Note('D', type='quarter')
        n3 = note.Note('E', type='quarter')
        n4 = note.Note('F', type='half')
        n1.id = 'n1'
        n2.id = 'n2'
        n3.id = 'n3'
        n4.id = 'n4'

        p1.append(n1)
        p1.append(n2)

        p2.append(n3)
        p2.append(n4)

        p2.offset = 20.0

        s1.insert(p1)
        s1.insert(p2)

        sf1 = s1.flatten()
        sf1.id = 'flat s1'

#        for site in n4.sites.get():
#            print(site.id,)
#            print(n4.sites.getOffsetBySite(site))

        self.assertEqual(len(sf1), 4)
        assert sf1[1] is n2

    def testActiveSiteCopiedStreams(self):
        srcStream = Stream()
        srcStream.insert(3, note.Note())
        # the note's activeSite is srcStream now
        self.assertEqual(srcStream[0].activeSite, srcStream)

        midStream = Stream()
        for x in range(2):
            srcNew = copy.deepcopy(srcStream)
#             for n in srcNew:
#                 offset = n.getOffsetBySite(srcStream)

            # gt = srcNew[0].getOffsetBySite(srcStream)

            # for n in srcNew: pass

            srcNew.offset = x * 10
            midStream.insert(srcNew)
            self.assertEqual(srcNew.offset, x * 10)

        # no offset is set yet
        self.assertEqual(midStream.offset, 0)

        # component streams have offsets
        self.assertEqual(midStream[0].getOffsetBySite(midStream), 0)
        self.assertEqual(midStream[1].getOffsetBySite(midStream), 10.0)

        # component notes still have a location set to srcStream
        # self.assertEqual(midStream[1][0].getOffsetBySite(srcStream), 3.0)

        # component notes still have a location set to midStream[1]
        self.assertEqual(midStream[1][0].getOffsetBySite(midStream[1]), 3.0)

        # one location in midstream
        self.assertEqual(len(midStream.sites), 1)

        # environLocal.printDebug(['srcStream', srcStream])
        # environLocal.printDebug(['midStream', midStream])
        x = midStream.flatten()

    def testSimpleRecurse(self):
        st1 = Stream()
        st2 = Stream()
        n1 = note.Note()
        st2.insert(10, n1)
        st1.insert(12, st2)
        self.assertIs(st1.flatten()[0], n1)
        self.assertEqual(st1.flatten()[0].offset, 22.0)

    def testStreamExceptionsOnAssert(self):
        with self.assertRaises(StreamException):
            n1 = note.Note()
            Stream([n1, 0])

    def testStreamRecursion(self):
        srcStream = Stream()
        for x in range(6):
            n = note.Note('G#')
            n.duration = duration.Duration('quarter')
            n.offset = x * 1
            srcStream.insert(n)

        self.assertEqual(len(srcStream), 6)
        self.assertEqual(len(srcStream.recurse()), 6)
        self.assertEqual(srcStream.flatten()[1].offset, 1.0)

#        self.assertEqual(len(srcStream.getOverlaps()), 0)

        midStream = Stream()
        for x in range(4):
            srcNew = copy.deepcopy(srcStream)
            srcNew.offset = x * 10
            midStream.insert(srcNew)

        self.assertEqual(len(midStream), 4)
        # environLocal.printDebug(['pre flat of mid stream'])
        self.assertEqual(len(midStream.flatten()), 24)
#        self.assertEqual(len(midStream.getOverlaps()), 0)
        mfs = midStream.flatten()
        self.assertEqual(mfs[7].getOffsetBySite(mfs), 11.0)

        farStream = Stream()
        for x in range(7):
            midNew = copy.deepcopy(midStream)
            midNew.offset = x * 100
            farStream.insert(midNew)

        self.assertEqual(len(farStream), 7)
        self.assertEqual(len(farStream.flatten()), 168)
        # self.assertEqual(len(farStream.getOverlaps()), 0)
        # get just offset times
        # elementsSorted returns offset, dur, element
        offsets = [a.offset for a in farStream.flatten()]

        # create what we expect to be the offsets
        offsetsMatch = list(range(6))
        offsetsMatch += [x + 10 for x in range(6)]
        offsetsMatch += [x + 20 for x in range(6)]
        offsetsMatch += [x + 30 for x in range(6)]
        offsetsMatch += [x + 100 for x in range(6)]
        offsetsMatch += [x + 110 for x in range(6)]

        self.assertEqual(offsets[:len(offsetsMatch)], offsetsMatch)

    def testStreamSortRecursion(self):
        farStream = Stream()
        for x in range(4):
            midStream = Stream()
            for y in range(4):
                nearStream = Stream()
                for z in range(4):
                    n = note.Note('G#')
                    n.duration = duration.Duration('quarter')
                    nearStream.insert(z * 2, n)  # 0, 2, 4, 6
                midStream.insert(y * 5, nearStream)  # 0, 5, 10, 15
            farStream.insert(x * 13, midStream)  # 0, 13, 26, 39

        # get just offset times
        # elementsSorted returns offset, dur, element
        fs_fs = farStream.flatten()
        offsets = [a.offset for a in fs_fs]  # safer is a.getOffsetBySite(fs_fs)
        offsetsBrief = offsets[:20]
        self.assertEqual(offsetsBrief,
                          [0, 2, 4, 5, 6, 7, 9, 10,
                           11, 12, 13, 14, 15, 15, 16, 17, 17, 18, 19, 19])

    def testOverlapsA(self):
        a = Stream()
        # here, the third item overlaps with the first
        for offset, dur in [(0, 12), (3, 2), (11, 3)]:
            n = note.Note('G#')
            n.duration = duration.Duration()
            n.duration.quarterLength = dur
            n.offset = offset
            a.insert(n)

        overlapMap = a._findLayering()
        self.assertEqual(overlapMap, [[1, 2], [0], [0]])

        dummy = a._consolidateLayering(overlapMap)
        # print(dummy)

    def testOverlapsB(self):

        a = Stream()
        for x in range(4):
            n = note.Note('G#')
            n.duration = duration.Duration('quarter')
            n.offset = x * 1
            a.insert(n)
        d = a.getOverlaps()
        # no overlaps
        self.assertEqual(len(d), 0)
        # a = Stream()
        # for x in [0, 0, 0, 0, 13, 13, 13]:
        #     n = note.Note('G#')
        #     n.duration = duration.Duration('half')
        #     n.offset = x
        #     a.insert(n)
        # d = a.getOverlaps()
        # len(d[0])
        # 4
        # len(d[13])
        # 3
        # a = Stream()
        # for x in [0, 0, 0, 0, 3, 3, 3]:
        #     n = note.Note('G#')
        #     n.duration = duration.Duration('whole')
        #     n.offset = x
        #     a.insert(n)
        #
        # # default is to not include coincident boundaries
        # d = a.getOverlaps()
        # len(d[0])
        # 7

    def testStreamDuration(self):
        a = Stream()
        q = note.Note(type='quarter')
        a.repeatInsert(q, [0, 1, 2, 3])
        self.assertEqual(a.highestOffset, 3)
        self.assertEqual(a.highestTime, 4)
        self.assertEqual(a.duration.quarterLength, 4.0)

        newDuration = duration.Duration('half')
        self.assertEqual(newDuration.quarterLength, 2.0)

        a.duration = newDuration
        self.assertEqual(a.duration.quarterLength, 2.0)
        self.assertEqual(a.highestTime, 4)

    def testStreamDurationRecalculated(self):
        from fractions import Fraction

        s = Stream()
        n = note.Note(quarterLength=1.0)
        s.append(n)
        self.assertEqual(s.duration.quarterLength, 1.0)

        tup = duration.Tuplet()
        n.duration.tuplets = (tup,)
        self.assertEqual(n.duration.quarterLength, Fraction(2, 3))
        self.assertEqual(s.duration.quarterLength, Fraction(2, 3))

        # Also (regression) test clearing the cache
        # https://github.com/cuthbertLab/music21/issues/957
        n.duration.tuplets = (tup, tup)
        self.assertEqual(s.duration.quarterLength, Fraction(4, 9))
        s.coreElementsChanged()
        self.assertEqual(s.duration.quarterLength, Fraction(4, 9))

    def testMeasureStream(self):
        '''
        An approach to setting TimeSignature measures in offsets and durations
        '''
        a = meter.TimeSignature('3/4')
        b = meter.TimeSignature('5/4')
        c = meter.TimeSignature('2/4')

        a.duration = duration.Duration()
        b.duration = duration.Duration()
        c.duration = duration.Duration()

        # 20 measures of 3/4
        a.duration.quarterLength = 20 * a.barDuration.quarterLength
        # 10 measures of 5/4
        b.duration.quarterLength = 10 * b.barDuration.quarterLength
        # 5 measures of 2/4
        c.duration.quarterLength = 5 * c.barDuration.quarterLength

        m = Stream()
        m.append(a)
        m.append(b)
        m.append(c)

        self.assertEqual(m[1].offset, (20 * a.barDuration.quarterLength))
        self.assertEqual(m[2].offset, ((20 * a.barDuration.quarterLength)
                                       + (10 * b.barDuration.quarterLength)))

    def testMultipartStream(self):
        '''
        Test the creation of streams with multiple parts. See versions
        of this tests in TestExternal for more details
        '''
        q = Stream()
        r = Stream()
        for x in ['c3', 'a3', 'g#4', 'd2'] * 10:
            n = note.Note(x)
            n.quarterLength = 0.25
            q.append(n)

            m = note.Note(x)
            m.quarterLength = 1
            r.append(m)

        s = Stream()  # container
        s.insert(q)
        s.insert(r)
        s.insert(0, meter.TimeSignature('3/4'))
        s.insert(3, meter.TimeSignature('5/4'))
        s.insert(8, meter.TimeSignature('3/4'))
        self.assertEqual(len(s.recurse().notes), 80)

        thisWork = corpus.getWork('corelli/opus3no1/1grave')
        a = converter.parse(thisWork)

        b = a[7][5:10]
        # environLocal.printDebug(['b', b, b.sites.getSiteIds()])
        c = a[7][10:15]
        # environLocal.printDebug(['c', c, c.sites.getSiteIds()])
        d = a[7][15:20]
        # environLocal.printDebug(['d', d, d.sites.getSiteIds()])

        s2 = Stream()
        # environLocal.printDebug(['s2', s2, id(s2)])

        for stream_case in (b, c, d):
            for e in stream_case:
                s2.insert(e.offset, e)

    def testActiveSites(self):
        '''
        Test activeSite relationships.

        Note that here we see why sometimes qualified class names are needed.
        This test passes fine with class names Part and Measure when run interactively,
        creating a Test instance. When run from the command line
        Part and Measure do not match, and instead music21.stream.Part has to be
        employed instead.
        '''
        a = corpus.parse('corelli/opus3no1/1grave')
        # test basic activeSite relationships
        b = a[8]
        self.assertIsInstance(b, Part)
        self.assertEqual(b.activeSite, a)

        # this, if called, actively destroys the activeSite relationship!
        # on the measures (as new Elements are not created)
        # m = b.getElementsByClass(Measure)[5]
        # self.assertIsInstance(m, Measure)

        # this false b/c, when getting the measures, activeSites are lost
        # self.assertEqual(m.activeSite, b)  # measures activeSite should be part
        # NOTE: this is dependent on raw element order, and might change
        # due to importing changes
        # b.show('t')
        self.assertIsInstance(b[15], Measure)
        self.assertIs(b[8].activeSite, b)  # measures activeSite should be part

        # a different test derived from a TestExternal
        q = Stream()
        r = Stream()
        for x in ['c3', 'a3', 'c#4', 'd3'] * 30:
            n = note.Note(x)
            n.quarterLength = random.choice([0.25])
            q.append(n)
            m = note.Note(x)
            m.quarterLength = 0.5
            r.append(m)
        s = Stream()  # container
        s.insert(q)
        s.insert(r)

        self.assertEqual(q.activeSite, s)
        self.assertEqual(r.activeSite, s)

    def testActiveSitesMultiple(self):
        '''
        Test an object having multiple activeSites.
        '''
        a = Stream()
        b = Stream()
        n = note.Note('G#')
        n.offset = 10
        a.insert(n)
        b.insert(n)
        # the objects elements has been transferred to each activeSite
        # stream in the same way
        self.assertEqual(n.getOffsetBySite(a), n.getOffsetBySite(b))
        self.assertEqual(n.getOffsetBySite(a), 10)

    def testExtractedNoteAssignLyric(self):
        a = converter.parse(corpus.getWork('corelli/opus3no1/1grave'))
        b = a.parts[1]
        c = b.flatten()
        for thisNote in c.getElementsByClass(note.Note):
            thisNote.lyric = thisNote.name
        textStr = text.assembleLyrics(b)
        self.assertEqual(textStr.startswith('A A G F E'),
                         True)

    def testGetInstrumentFromMxl(self):
        '''
        Test getting an instrument from an mxl file
        '''

        # manually set activeSite to associate
        a = corpus.parse('corelli/opus3no1/1grave.xml')

        b = a.parts[2]
        # by calling the .part property, we create a new stream; thus, the
        # activeSite of b is no longer a
        # self.assertEqual(b.activeSite, None)
        instObj = b.getInstrument()
        self.assertEqual(instObj.partName, 'Violone e Organo')
        self.assertEqual(b.partName, 'Violone e Organo')

    def testGetInstrumentManual(self):
        # import pdb; pdb.set_trace()
        # search activeSite from a measure within

        # a different test derived from a TestExternal
        q = Stream()
        r = Stream()
        for x in ['c3', 'a3', 'c#4', 'd3'] * 15:
            n = note.Note(x)
            n.quarterLength = random.choice([0.25])
            q.append(n)
            m = note.Note(x)
            m.quarterLength = 0.5
            r.append(m)
        s = Stream()  # container

        s.insert(q)
        s.insert(r)

        instObj = q.getInstrument()
        self.assertEqual(instObj.partName, defaults.partName)

        instObj = r.getInstrument()
        self.assertEqual(instObj.partName, defaults.partName)

        instObj = s.getInstrument()
        self.assertEqual(instObj.partName, defaults.partName)

        # test mx generation of parts
        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(q).decode('utf-8')
        unused_mx = GEX.parse(r).decode('utf-8')

        # test mx generation of score
        unused_mx = GEX.parse(s).decode('utf-8')

    def testMeasureAndTieCreation(self):
        '''
        A test of the automatic partitioning of notes in a measure and the creation of ties.
        '''

        n = note.Note()
        n.quarterLength = 3
        a = Stream()
        a.repeatInsert(n, list(range(0, 120, 3)))
        a.insert(0, meter.TimeSignature('5/4'))
        a.insert(10, meter.TimeSignature('2/4'))
        a.insert(3, meter.TimeSignature('3/16'))
        a.insert(20, meter.TimeSignature('9/8'))
        a.insert(40, meter.TimeSignature('10/4'))

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(a).decode('utf-8')

    def testStreamCopy(self):
        '''
        Test copying a stream
        '''
        # import pdb; pdb.set_trace()
        # search activeSite from a measure within

        # a different test derived from a TestExternal
        q = Stream()
        r = Stream()
        for x in ['c3', 'a3', 'c#4', 'd3'] * 30:
            n = note.Note(x)
            n.quarterLength = random.choice([0.25])
            q.append(n)
            m = note.Note(x)
            m.quarterLength = 0.5
            r.append(m)
        s = Stream()  # container

        s.insert(q)
        s.insert(r)

        # copying the whole: this works
        unused_w = copy.deepcopy(s)

        post = Stream()
        # copying while looping: this gets increasingly slow
        for aElement in s:
            environLocal.printDebug(['copying and inserting an element',
                                     aElement, len(aElement.sites)])
            bElement = copy.deepcopy(aElement)
            post.insert(aElement.offset, bElement)

    def testIteration(self):
        '''
        This test was designed to illustrate a past problem with stream
        Iterations.
        '''
        q = Stream()
        r = Stream()
        for x in ['c3', 'a3', 'c#4', 'd3'] * 5:
            n = note.Note(x)
            n.quarterLength = random.choice([0.25])
            q.append(n)
            m = note.Note(x)
            m.quarterLength = 0.5
            r.append(m)
        src = Stream()  # container
        src.insert(q)
        src.insert(r)

        a = Stream()

        for obj in src.getElementsByClass(Stream):
            a.insert(obj)

        environLocal.printDebug(['expected length', len(a)])
        counter = 0
        for x in a:
            if counter >= 4:
                environLocal.printDebug(['infinite loop', counter])
                break
            environLocal.printDebug([x])
            junk = x.getInstrument(searchActiveSite=True)
            del junk
            counter += 1

    def testGetTimeSignatures(self):
        n = note.Note()
        n.quarterLength = 3
        a = Stream()
        a.autoSort = False
        a.insert(0, meter.TimeSignature('5/4'))
        a.insert(10, meter.TimeSignature('2/4'))
        a.insert(3, meter.TimeSignature('3/16'))
        a.insert(20, meter.TimeSignature('9/8'))
        a.insert(40, meter.TimeSignature('10/4'))

        offsets = [x.offset for x in a]
        self.assertEqual(offsets, [0.0, 10.0, 3.0, 20.0, 40.0])

        # fill with notes
        a.repeatInsert(n, list(range(0, 120, 3)))

        b = a.getTimeSignatures(sortByCreationTime=False)

        self.assertEqual(len(b), 5)
        self.assertEqual(b[0].numerator, 5)
        self.assertEqual(b[4].numerator, 10)

        self.assertEqual(b[4].activeSite, b)

        # none of the offsets are being copied
        offsets = [x.offset for x in b]
        # with autoSort is passed on from elements search
        # self.assertEqual(offsets, [0.0, 3.0, 10.0, 20.0, 40.0])
        self.assertEqual(offsets, [0.0, 10.0, 3.0, 20.0, 40.0])

    def testElements(self):
        '''
        Test basic Elements wrapping non music21 objects
        '''
        a = Stream()
        a.insert(50, music21.Music21Object())
        self.assertEqual(len(a), 1)

        # there are two locations, default and the one just added
        self.assertEqual(len(a[0].sites), 2)
        # this works
#        self.assertEqual(a[0].sites.getOffsetByIndex(-1), 50.0)

#        self.assertEqual(a[0].sites.getSiteByIndex(-1), a)
        self.assertEqual(a[0].getOffsetBySite(a), 50.0)
        self.assertEqual(a[0].offset, 50.0)

    def testClefs(self):
        s = Stream()
        for x in ['c3', 'a3', 'c#4', 'd3'] * 5:
            n = note.Note(x)
            s.append(n)
        clefObj = clef.bestClef(s)
        self.assertEqual(clefObj.sign, 'F')
        measureStream = s.makeMeasures()
        clefObj = measureStream[0].clef
        self.assertEqual(clefObj.sign, 'F')

    def testFindConsecutiveNotes(self):
        s = Stream()
        n1 = note.Note('c3')
        n1.quarterLength = 1
        n2 = chord.Chord(['c4', 'e4', 'g4'])
        n2.quarterLength = 4
        s.insert(0, n1)
        s.insert(1, n2)
        l1 = s.findConsecutiveNotes()
        self.assertIs(l1[0], n1)
        self.assertIs(l1[1], n2)
        l2 = s.findConsecutiveNotes(skipChords=True)
        self.assertEqual(len(l2), 1)
        self.assertIs(l2[0], n1)

        r1 = note.Rest()
        s2 = Stream()
        s2.insert([0.0, n1,
                   1.0, r1,
                   2.0, n2])
        l3 = s2.findConsecutiveNotes()
        self.assertIsNone(l3[1])
        l4 = s2.findConsecutiveNotes(skipRests=True)
        self.assertEqual(len(l4), 2)
        s3 = Stream()
        s3.insert([0.0, n1,
                   1.0, r1,
                   10.0, n2])
        l5 = s3.findConsecutiveNotes(skipRests=False)
        self.assertEqual(len(l5), 3)  # not 4 because two Nones allowed in a row!
        l6 = s3.findConsecutiveNotes(skipRests=True, skipGaps=True)
        self.assertEqual(len(l6), 2)

        n1.quarterLength = 10
        n3 = note.Note('B-')
        s4 = Stream()
        s4.insert([0.0, n1,
                   1.0, n2,
                   10.0, n3])
        l7 = s4.findConsecutiveNotes()
        self.assertEqual(len(l7), 2)  # n2 is hidden because it is in an overlap
        l8 = s4.findConsecutiveNotes(getOverlaps=True)
        self.assertEqual(len(l8), 3)
        self.assertIs(l8[1], n2)
        l9 = s4.findConsecutiveNotes(getOverlaps=True, skipChords=True)
        self.assertEqual(len(l9), 3)
        self.assertIsNone(l9[1])

        n4 = note.Note('A#')
        n1.quarterLength = 1
        n2.quarterLength = 1

        s5 = Stream()
        s5.insert([0.0, n1,
                   1.0, n2,
                   2.0, n3,
                   3.0, n4])
        l10 = s5.findConsecutiveNotes()
        self.assertEqual(len(l10), 4)
        l11 = s5.findConsecutiveNotes(skipUnisons=True)
        self.assertEqual(len(l11), 3)

        self.assertIs(l11[2], n3)

        n5 = note.Note('c4')
        s6 = Stream()
        s6.insert([0.0, n1,  # C3
                   1.0, n5,  # C4
                   2.0, n2])  # Chord C4, E4, G4
        l12 = s6.findConsecutiveNotes(noNone=True)
        self.assertEqual(len(l12), 3)
        l13 = s6.findConsecutiveNotes(noNone=True, skipUnisons=True)
        self.assertEqual(len(l13), 3)
        l14 = s6.findConsecutiveNotes(noNone=True, skipOctaves=True)
        self.assertEqual(len(l14), 2)
        self.assertIs(l14[0], n1)
        self.assertIs(l14[1], n2)

        s7 = Stream()
        s7.append(clef.Clef())  # Stream without Notes
        s7.append(key.Key('B'))
        l15 = s7.findConsecutiveNotes()
        self.assertSequenceEqual(l15, [])

        # with voices in a measure
        m = Measure()
        m.repeatAppend(note.Note(), 4)
        m.repeatInsert(note.Note(), [0, 1, 2, 3])
        m.makeVoices(inPlace=True)

        for i, elem in enumerate(list(m.recurse().notes)):
            elem.transpose(i, inPlace=True)

        consec = m.findConsecutiveNotes()

        self.assertEqual([repr(x) for x in consec],
            ['<music21.note.Note C>',
             '<music21.note.Note C#>',
             '<music21.note.Note D>',
             '<music21.note.Note E->',
             'None',
             '<music21.note.Note E>',
             '<music21.note.Note F>',
             '<music21.note.Note F#>',
             '<music21.note.Note G>',
             ]
        )

        # with voices in each of two measures
        m.insert(meter.TimeSignature('2/4'))
        p = Part(m)
        p.makeMeasures(inPlace=True)
        for mm in list(p[Measure]):
            mm.makeVoices(inPlace=True)
        consec2 = p.findConsecutiveNotes()

        expected2 = ['<music21.note.Note C>',
                     '<music21.note.Note C#>',
                     'None',
                     '<music21.note.Note E>',
                     '<music21.note.Note F>',
                     'None',
                     '<music21.note.Note D>',
                     '<music21.note.Note E->',
                     'None',
                     '<music21.note.Note F#>',
                     '<music21.note.Note G>',
                     ]

        self.assertEqual([repr(x) for x in consec2], expected2)

        # with two identical parts
        p2 = copy.deepcopy(p)
        s = Score([p, p2])
        consec3 = s.findConsecutiveNotes()

        self.assertEqual([repr(x) for x in consec3], expected2 + ['None'] + expected2)

    def testMelodicIntervals(self):
        c4 = note.Note('C4')
        d5 = note.Note('D5')
        r1 = note.Rest()
        b4 = note.Note('B4')
        s1 = Stream()
        s1.append([c4, d5, r1, b4])
        intS1 = s1.melodicIntervals(skipRests=True)
        self.assertEqual(len(intS1), 2)
        M9 = intS1[0]
        self.assertEqual(M9.niceName, 'Major Ninth')

        self.assertIs(M9.noteStart.activeSite, s1)

        # Simple chord example
        ch1 = chord.Chord('C4 E4 G4')
        ch2 = chord.Chord('D4 F4 A4')
        s2 = Stream([ch1, ch2])
        intS2 = s2.melodicIntervals()
        self.assertEqual(len(intS2), 1)
        major_second = intS2.first()
        self.assertEqual(major_second.niceName, 'Major Second')
        self.assertIs(major_second.noteStart, ch1.notes[0])
        self.assertIs(major_second.noteEnd, ch2.notes[0])

        # TODO: Many more tests

    def testMelodicIntervalsB(self):
        s1 = converter.parse("tinynotation: 3/4 c4 d' r b b'", makeNotation=False)
        intS1 = s1.melodicIntervals()
        self.assertEqual(len(intS1), 2)

    def testStripTiesBuiltA(self):
        s1 = Stream()
        n1 = note.Note('D#2')
        n1.quarterLength = 6
        s1.append(n1)
        self.assertEqual(len(s1.notes), 1)

        s1 = s1.makeMeasures()
        s1.makeTies(inPlace=True)  # makeTies but no end tie positions!
        # flat version has 2 notes
        self.assertEqual(len(s1.recurse().notes), 2)

        sUntied = s1.stripTies()
        self.assertEqual(len(sUntied.recurse().notes), 1)
        self.assertEqual(sUntied.recurse().notes[0].quarterLength, 6)

        s2 = Stream()
        n2 = note.Note('A4')
        n2.quarterLength = 12
        s2.append(n2)
        s2 = s2.makeMeasures()
        s2.makeTies(inPlace=True)
        s2.flatten().notes[1].tie = tie.Tie('start')  # two start ties -> continuation
        s2Untied = s2.stripTies()
        self.assertEqual(len(s2Untied.recurse().notes), 1)

        n = note.Note()
        n.quarterLength = 3
        a = Stream()
        a.repeatInsert(n, list(range(0, 120, 3)))

        self.assertEqual(len(a), 40)

        a.insert(0, meter.TimeSignature('5/4'))
        a.insert(10, meter.TimeSignature('2/4'))
        a.insert(3, meter.TimeSignature('3/16'))
        a.insert(20, meter.TimeSignature('9/8'))
        a.insert(40, meter.TimeSignature('10/4'))

        b = a.makeMeasures()
        b.makeTies(inPlace=True)

        # we now have 65 notes, as ties have been created
        self.assertEqual(len(b.recurse().notes), 65)

        c = b.stripTies()
        self.assertEqual(len(c.recurse().notes), 40)

    def testStripTiesImportedA(self):
        from music21.musicxml import testPrimitive

        a = converter.parse(testPrimitive.multiMeasureTies)

        p1 = a.parts[0]
        self.assertEqual(len(p1.recurse().notesAndRests), 16)
        p1.stripTies(inPlace=True)
        self.assertEqual(len(p1.recurse().notesAndRests), 6)

        p2 = a.parts[1]
        self.assertEqual(len(p2.recurse().notesAndRests), 16)
        p2Stripped = p2.stripTies(inPlace=False)
        self.assertEqual(len(p2Stripped.recurse().notesAndRests), 5)
        # original part should not be changed
        self.assertEqual(len(p2.recurse().notesAndRests), 16)

        p3 = a.parts[2]
        self.assertEqual(len(p3.recurse().notesAndRests), 16)
        p3.stripTies(inPlace=True)
        self.assertEqual(len(p3.recurse().notesAndRests), 3)

        p4 = a.parts[3]
        self.assertEqual(len(p4.recurse().notesAndRests), 16)
        p4Notes = p4.stripTies().flatten()
        # original should be unchanged
        self.assertEqual(len(p4.recurse().notesAndRests), 16)
        # lesser notes
        self.assertEqual(len(p4Notes.notesAndRests), 10)

    def testStripTiesNonMeasureContainers(self):
        '''
        Testing that ties are stripped from containers that are not Measures.
        https://github.com/cuthbertLab/music21/issues/266
        '''
        s = Stream()
        v = Voice()
        s.append(v)

        n = note.Note('C4', quarterLength=1.0)
        n.tie = tie.Tie('start')
        n2 = note.Note('C4', quarterLength=1.0)
        n2.tie = tie.Tie('continue')
        n3 = note.Note('C4', quarterLength=1.0)
        n3.tie = tie.Tie('stop')
        n4 = note.Note('C4', quarterLength=1.0)
        v.append([n, n2, n3, n4])

        s.stripTies(inPlace=True)
        self.assertEqual(len(s.recurse().notesAndRests), 2)

        stripped = s.stripTies(inPlace=False)
        self.assertEqual(len(stripped.recurse().notesAndRests), 2)

    def testStripTiesUnlinked(self):
        '''
        After stripping ties, unlinked durations become linked.
        '''
        m1 = Measure(number=1)
        m2 = Measure(number=2)
        n1 = note.Note(type='whole')
        n2 = note.Note(type='quarter')
        n2.duration.linked = False
        n2.duration.quarterLength = 0.75
        n1.tie = tie.Tie('start')
        n2.tie = tie.Tie('stop')
        m1.insert(0, n1)
        m2.insert(0, n2)
        p = Part([m1, m2])
        p_stripped = p.stripTies()
        n = p_stripped[note.Note].first()
        d = n.duration
        self.assertTrue(d.linked)
        self.assertEqual(d.type, 'complex')
        self.assertEqual(d.quarterLength, 4.75)
        self.assertFalse(n2.duration.linked)


    def testStripTiesConsecutiveInVoiceNotContainer(self):
        '''
        Testing that ties are stripped from notes consecutive in a voice
        but not consecutive in a flattened parent stream.
        https://github.com/cuthbertLab/music21/issues/568
        '''
        s = Score()
        p = Part()
        v1 = Voice()
        v2 = Voice()

        v1n1 = note.Note(quarterLength=2)
        v1n1.tie = tie.Tie('start')
        v1n2 = note.Note(quarterLength=2)
        v1n2.tie = tie.Tie('stop')
        v2n1 = note.Rest(quarterLength=1)
        v2n2 = note.Note(quarterLength=1)
        v2n2.tie = tie.Tie('start')  # Tie begins in v2 before tie in v1 stops
        v2n3 = note.Note(quarterLength=2)
        v2n3.tie = tie.Tie('stop')

        v1.append([v1n1, v1n2])
        v2.append([v2n1, v2n2, v2n3])
        p.append(v1)
        p.insert(0, v2)
        s.append(p)

        stripped = s.stripTies()
        self.assertEqual(len(stripped.flatten().notesAndRests), 3)

        voice1Note = stripped.parts[0].voices[0].notesAndRests[0]
        self.assertEqual(voice1Note.quarterLength, 4)
        self.assertIsNone(voice1Note.tie)
        voice2Note = stripped.parts[0].voices[1].notesAndRests[1]
        self.assertEqual(voice2Note.quarterLength, 3)
        self.assertIsNone(voice2Note.tie)

    def testStripTiesChordMembersSomeTied(self):
        '''
        Testing ties NOT stripped where only some chord members are tied.
        https://github.com/cuthbertLab/music21/issues/502
        '''
        s = Stream()
        n1 = note.Note('C5', quarterLength=0.5)
        n2 = note.Note('Bb4', quarterLength=0.5)
        n3 = note.Note('C3', quarterLength=0.5)
        n3.tie = tie.Tie('start')
        n4 = note.Note('C3', quarterLength=0.5)
        n4.tie = tie.Tie('stop')

        c1 = chord.Chord([n1, n3])
        c2 = chord.Chord([n2, n4])
        s.append([c1, c2])
        stripped = s.stripTies()

        self.assertIsNotNone(stripped.notes[0].tie)

    def testStripTiesChordMembersAllTied(self):
        '''
        Testing ties stripped where all chord members are tied.
        '''

        s = Stream()
        c = chord.Chord(['C3', 'C5'])
        s.append(meter.TimeSignature('1/8'))
        s.append(c)
        s.makeNotation(inPlace=True)  # makes ties
        stripped = s.stripTies()
        self.assertEqual(len(stripped.flatten().notes), 1)

    def testStripTiesReplaceSpannedElements(self):
        '''
        Testing elements in spanners replaced when stripTies removes them.
        '''

        s = Stream()
        c = chord.Chord(['C3', 'C5'])
        s.append(meter.TimeSignature('1/16'))
        s.append(c)
        s.makeNotation(inPlace=True)  # makes ties
        n1, unused_n2, n3, n4 = s.flatten().notes
        s.insert(0, music21.spanner.Slur(n1, n4))
        s.insert(0, music21.dynamics.Crescendo(n1, n3))
        stripped = s.stripTies(inPlace=False)
        sn1 = stripped.flatten().notes[0]

        self.assertEqual(len(stripped.spanners[0]), 1)
        self.assertEqual(len(stripped.spanners[1]), 1)

        self.assertTrue(stripped.spanners[0].isFirst(sn1))
        self.assertTrue(stripped.spanners[0].isLast(sn1))
        self.assertTrue(stripped.spanners[1].isFirst(sn1))
        self.assertTrue(stripped.spanners[1].isLast(sn1))

        # original unchanged
        self.assertIsNot(s.spanners[0], stripped.spanners[0])
        self.assertTrue(s.spanners[0].isFirst(n1))
        self.assertTrue(s.spanners[0].isLast(n4))
        self.assertTrue(s.spanners[1].isFirst(n1))
        self.assertTrue(s.spanners[1].isLast(n3))

    def testStripTiesClearBeaming(self):
        p = converter.parse('tinyNotation: c2~ c8 c8 c8 c8')
        p.makeNotation(inPlace=True)
        self.assertEqual(p.streamStatus.beams, True)
        p.stripTies(inPlace=True)
        self.assertEqual(p.streamStatus.beams, False)
        p = p.splitAtDurations(recurse=True)[0]
        p.makeBeams(inPlace=True)
        self.assertEqual([repr(el.beams) for el in p[note.Note]],
            ['<music21.beam.Beams>',
             '<music21.beam.Beams <music21.beam.Beam 1/start>>',
             '<music21.beam.Beams <music21.beam.Beam 1/stop>>',
             '<music21.beam.Beams <music21.beam.Beam 1/start>>',
             '<music21.beam.Beams <music21.beam.Beam 1/stop>>'
             ]
        )

    def testStripTiesStopTieChordFollowsRest(self):
        '''
        Ensure stripTies() gracefully handles "stop" or "continue" tie types
        following rests as it flattens a stream.
        '''
        v1 = Voice([note.Rest()])
        v2 = Voice([chord.Chord('C4 E-4 B-4')])
        m = Measure([v1, v2])
        p = Part(m)
        v2.notes.first().tie = tie.Tie('stop')
        _ = p.stripTies(inPlace=False, matchByPitch=False)
        v2.notes.first().tie = tie.Tie('continue')
        _ = p.stripTies(inPlace=False, matchByPitch=False)

    def testGetElementsByOffsetZeroLength(self):
        '''
        Testing multiple zero-length elements with mustBeginInSpan:
        '''

        c = clef.TrebleClef()
        ts = meter.TimeSignature('4/4')
        ks = key.KeySignature(2)
        s = Stream()
        s.insert(0.0, c)
        s.insert(0.0, ts)
        s.insert(0.0, ks)
        l1 = len(s.getElementsByOffset(0.0, mustBeginInSpan=True))
        l2 = len(s.getElementsByOffset(0.0, mustBeginInSpan=False))
        self.assertEqual(l1, 3)
        self.assertEqual(l2, 3)

    def testStripTiesScore(self):
        '''
        Test stripTies using the Score method
        '''
        from music21.musicxml import testPrimitive

        # This score has 4 parts, each with eight measures, and 2 half-notes
        # per measure, equaling 16 half notes, but with differing tie type.

        # 1: .  .~|~.  .~|~.~~.~|~.  .~|~.  .~|~.~~. | .~~.~|~.~~. ||
        # 2: .~~.~|~.~~. | .~~.~|~.~~. | .~~.~|~.~~. | .~~.~|~.  . ||
        # 3: .~~.~|~.  .~|~.~~. | .~~.~|~.~~.~|~.~~.~|~.~~.~|~.~~. ||
        # 4: .  . | .~~. | .  .~|~.~~. | .  .~|~.  .~|~.  .~|~.  . ||

        s = converter.parse(testPrimitive.multiMeasureTies)

        self.assertEqual(len(s.parts), 4)

        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 16)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 16)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 16)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 16)

        # first, in place false
        sPost = s.stripTies(inPlace=False)

        self.assertEqual(len(sPost.parts[0].flatten().notesAndRests), 6)
        self.assertEqual(len(sPost.parts[1].flatten().notesAndRests), 5)
        self.assertEqual(len(sPost.parts[2].flatten().notesAndRests), 3)
        self.assertEqual(len(sPost.parts[3].flatten().notesAndRests), 10)

        # make sure original is unchanged
        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 16)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 16)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 16)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 16)

        # second, in place true
        s.stripTies(inPlace=True)
        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 6)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 5)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 3)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 10)

        # just two ties here
        s = corpus.parse('bach/bwv66.6')
        self.assertEqual(len(s.parts), 4)

        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 37)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 42)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 45)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 41)

        # perform strip ties in place
        s.stripTies(inPlace=True)

        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 36)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 42)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 44)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 41)

    def testStripTiesChords(self):
        '''
        Test whether strip ties merges some chords that are the same and
        some that are not.
        '''
        ch0 = chord.Chord('C4 E4 G4')
        ch1 = chord.Chord('C4 E4 G4')
        ch2 = chord.Chord('C3 E3 G3')
        ch3 = chord.Chord('C3 E-3 G3')
        ch4 = chord.Chord('D4 F#4 A4')
        ch5 = chord.Chord('D4 F#4')
        chords = [ch0, ch1, ch2, ch3, ch4, ch5]
        p = Part()
        p.append(meter.TimeSignature('1/4'))
        for i in range(6):
            c = chords[i]
            if not i % 2:
                t = tie.Tie('start')
                c.tie = t
            m = Measure(number=i + 1)
            m.append(c)
            p.append(m)
        p2 = p.stripTies(matchByPitch=True)
        chordsOut = list(p2.flatten().getElementsByClass(chord.Chord))
        self.assertEqual(len(chordsOut), 5)
        self.assertEqual(chordsOut[0].pitches, ch0.pitches)
        self.assertEqual(chordsOut[0].duration.quarterLength, 2.0)
        self.assertEqual(chordsOut[1].pitches, ch2.pitches)
        self.assertEqual(chordsOut[2].pitches, ch3.pitches)
        self.assertEqual(chordsOut[3].pitches, ch4.pitches)
        self.assertEqual(chordsOut[4].pitches, ch5.pitches)

    def testStripTiesChordsAccidentals(self):
        '''
        Make sure chords are matched even if some have 'natural' accidentals and some
        have None accidentals.
        '''
        sch = corpus.parse('schoenberg/opus19', 2)
        self.assertEqual(len(sch.stripTies().flatten().notes), 46)
        measure = sch.stripTies().parts[0].getElementsByClass('Measure')[6]
        self.assertEqual(len(measure.notes), 3)
        self.assertEqual(measure.notes[0].offset, 0.5)
        self.assertEqual(measure.notes[1].offset, 2.5)
        self.assertEqual(measure.notes[2].offset, 3.0)

    def testStripTiesComplexTies(self):
        '''
        Make sure tie types of "stop" or "continue" are not taken at face value
        for Chords if matchByPitch=False; they only represent that SOME
        chord member has that tie type.
        '''
        n0 = note.Note('C4')
        n0.tie = tie.Tie('start')

        n1 = note.Note('C4')
        n2 = note.Note('F4')
        n1.tie = tie.Tie('continue')

        n3 = note.Note('C4')
        n4 = note.Note('F4')
        n3.tie = tie.Tie('stop')

        c1 = chord.Chord([n1, n2])
        c2 = chord.Chord([n3, n4])

        s = Stream()
        s.append(n0)
        s.append(c1)
        s.append(c2)

        stripped1 = s.stripTies(matchByPitch=True)
        # pitches of c1 don't match pitch of n0,
        # so disregard the "continue" and treat instead as a start
        # and match against the pitches of c2
        self.assertEqual(len(stripped1), 2)  # previously was 1

        stripped2 = s.stripTies(matchByPitch=False)
        # strict mode: this shouldn't do anything,
        # because the middle element isn't uniform-continue
        # and the last element isn't uniform-stop
        self.assertEqual(len(stripped2), 3)

        n2.tie = tie.Tie('continue')

        stripped3 = s.stripTies(matchByPitch=True)
        # number of pitches in c1 doesn't match n0
        # but does match c2, so lack of uniform-tie stop is irrelevant
        self.assertEqual(len(stripped3), 2)  # previously was 1
        self.assertEqual(
            str(stripped3.elements),
            '(<music21.note.Note C>, <music21.chord.Chord C4 F4>)'
        )

        stripped4 = s.stripTies(matchByPitch=False)
        # matchByPitch=False requires last element to be uniform-stop
        self.assertEqual(len(stripped4), 3)

        n4.tie = tie.Tie('stop')

        stripped5 = s.stripTies(matchByPitch=False)
        # notice the note STILL isn't merged to the chords -- because different # of notes
        self.assertEqual(len(stripped5), 2)

        self.assertEqual(
            str(stripped5.elements),
            '(<music21.note.Note C>, <music21.chord.Chord C4 F4>)'
        )

        # replace the first note with a Chord bearing a start tie, and everything can be merged
        s.replace(n0, chord.Chord('C4 F4'))
        s.first().tie = tie.Tie('start')

        stripped6 = s.stripTies(matchByPitch=False)
        self.assertEqual(
            str(stripped6.elements),
            '(<music21.chord.Chord C4 F4>,)'
        )

        # make sure matchByPitch=True is still picky about pitch but merges the rest,
        # including a "continue" tie, which becomes ersatz-start
        s.first().transpose(6, inPlace=True)
        stripped7 = s.stripTies(matchByPitch=True)
        self.assertEqual(
            str(stripped7.elements),
            '(<music21.chord.Chord F#4 B4>, <music21.chord.Chord C4 F4>)'
        )  # previously was 1 element

        # also transpose the "continue" chord
        # to ensure the link from continue -> stop matches pitch
        s[1].transpose(7, inPlace=True)
        stripped8 = s.stripTies(matchByPitch=True)
        self.assertEqual(
            str(stripped8.elements),
            '(<music21.chord.Chord F#4 B4>, '
            + '<music21.chord.Chord G4 C5>, <music21.chord.Chord C4 F4>)'
        )  # previously was 1 element

    def testStripTiesIgnoresUnrealizedChordSymbol(self):
        from music21 import harmony

        n0 = note.Note('C')
        n0.tie = tie.Tie('start')
        n1 = note.Note('C')
        n1.tie = tie.Tie('stop')

        # Create ChordSymbol having one pitch only
        cs0 = harmony.ChordSymbol()
        cs0.bass('C', allow_add=True)
        s = Stream()
        s.insert(0.0, n0)
        s.insert(1.0, cs0)
        s.insert(1.0, n1)
        s.makeNotation(inPlace=True)
        stripped = s.stripTies(matchByPitch=True)

        self.assertEqual(len(stripped[note.Note]), 1)
        self.assertEqual(stripped[note.Note].first().quarterLength, 2)
        self.assertEqual(len(stripped[harmony.ChordSymbol]), 1)
        self.assertEqual(stripped[harmony.ChordSymbol].first().quarterLength, 0)

    def testTwoStreamMethods(self):
        from music21.note import Note

        (n11, n12, n13, n14) = (Note(), Note(), Note(), Note())
        (n21, n22, n23, n24) = (Note(), Note(), Note(), Note())
        n11.step = 'C'
        n12.step = 'D'
        n13.step = 'E'
        n14.step = 'F'
        n21.step = 'G'
        n22.step = 'A'
        n23.step = 'B'
        n24.step = 'C'
        n24.octave = 5

        n11.duration.type = 'half'
        n12.duration.type = 'whole'
        n13.duration.type = 'eighth'
        n14.duration.type = 'half'

        n21.duration.type = 'half'
        n22.duration.type = 'eighth'
        n23.duration.type = 'whole'
        n24.duration.type = 'eighth'

        stream1 = Stream()
        stream1.append([n11, n12, n13, n14])
        stream2 = Stream()
        stream2.append([n21, n22, n23, n24])

        attackedTogether = stream1.simultaneousAttacks(stream2)
        self.assertEqual(len(attackedTogether), 3)  # nx1, nx2, nx4
        thisNote = stream2.getElementsByOffset(attackedTogether[1]).first()
        self.assertIs(thisNote, n22)

        playingWhenAttacked = stream1.playingWhenAttacked(n23)
        self.assertIs(playingWhenAttacked, n12)

        allPlayingWhileSounding = stream2.allPlayingWhileSounding(n14)
        self.assertEqual(len(allPlayingWhileSounding), 1)
        self.assertIs(allPlayingWhileSounding[0], n24)

    #    trimPlayingWhileSounding = stream2.trimPlayingWhileSounding(n12)
    #    assert trimPlayingWhileSounding[0] == n22
    #    assert trimPlayingWhileSounding[1].duration.quarterLength == 3.5

    def testMeasureRange(self):
        a = corpus.parse('bach/bwv324.xml')
        b = a.parts[3].measures(4, 6)
        self.assertEqual(len(b.getElementsByClass(Measure)), 3)
        # b.show('t')
        # first measure now has a key sig
        unused_bMeasureFirst = b.getElementsByClass(Measure).first()

        self.assertEqual(len(b.flatten().getElementsByClass(
            key.KeySignature)), 1)
        # first measure now has a meter
        self.assertEqual(len(b.flatten().getElementsByClass(
            meter.TimeSignature)), 1)
        # first measure now has a clef
        self.assertEqual(len(b.flatten().getElementsByClass(clef.Clef)), 1)

        # b.show()
        # get first part
        p1 = a.parts[0]
        # get measure by class; this will not manipulate the measure
        mExRaw = p1.getElementsByClass(Measure)[5]
        self.assertEqual(str(list(mExRaw.notes)), '[<music21.note.Note B>, <music21.note.Note D>]')
        self.assertEqual(len(mExRaw.flatten()), 3)

        # get measure by using method; this will add elements
        mEx = p1.measure(6)
        self.assertEqual(str(list(mEx.notes)), '[<music21.note.Note B>, <music21.note.Note D>]')
        self.assertEqual(len(mEx.flatten()), 3)

        # make sure source has not changed
        mExRaw = p1.getElementsByClass(Measure)[5]
        self.assertEqual(str(list(mExRaw.notes)), '[<music21.note.Note B>, <music21.note.Note D>]')
        self.assertEqual(len(mExRaw.flatten()), 3)

        # test measures with no measure numbers
        c = Stream()
        for dummy in range(4):
            m = Measure()
            n = note.Note()
            m.repeatAppend(n, 4)
            c.append(m)
        # c.show()
        d = c.measures(2, 3)
        self.assertEqual(len(d), 2)
        # d.show()

        # try the score method
        a = corpus.parse('bach/bwv324.xml')
        b = a.measures(2, 4)
        self.assertEqual(len(b[0][clef.Clef]), 1)
        self.assertEqual(len(b[1][clef.Clef]), 1)
        self.assertEqual(len(b[2][clef.Clef]), 1)
        self.assertEqual(len(b[3][clef.Clef]), 1)

        self.assertEqual(len(b[0][key.KeySignature]), 1)
        self.assertEqual(len(b[1][key.KeySignature]), 1)
        self.assertEqual(len(b[2][key.KeySignature]), 1)
        self.assertEqual(len(b[3][key.KeySignature]), 1)

        # b.show()

    def testMeasureOffsetMap(self):
        a = corpus.parse('bach/bwv324.xml')

        mOffsetMap = a.parts[0].measureOffsetMap()

        self.assertEqual(sorted(list(mOffsetMap.keys())),
                         [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0, 34.0, 38.0])

        # try on a complete score
        a = corpus.parse('bach/bwv324.xml')
        mOffsetMap = a.measureOffsetMap()
        # environLocal.printDebug([mOffsetMap])
        self.assertEqual(sorted(list(mOffsetMap.keys())),
                         [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0, 34.0, 38.0])

        for unused_key, value in mOffsetMap.items():
            # each key contains 4 measures, one for each part
            self.assertEqual(len(value), 4)

        # we can get this information from Notes too!
        a = corpus.parse('bach/bwv324.xml')
        # get notes from one measure

        mOffsetMap = a.parts[0].flatten().measureOffsetMap([note.Note])
        self.assertEqual(sorted(list(mOffsetMap.keys())),
                         [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0, 34.0, 38.0])

        self.assertEqual(str(mOffsetMap[0.0]), '[<music21.stream.Measure 1 offset=0.0>]')

        self.assertEqual(str(mOffsetMap[4.0]), '[<music21.stream.Measure 2 offset=4.0>]')

        # TODO: getting inconsistent results with these
        # instead of storing a time value for locations, use an index
        # count

        m1 = a.parts[0].getElementsByClass(Measure)[1]
        # m1.show('text')
        mOffsetMap = m1.measureOffsetMap([note.Note])
        # offset here is that of measure that originally contained this note
        # environLocal.printDebug(['m1', m1, 'mOffsetMap', mOffsetMap])
        self.assertEqual(sorted(list(mOffsetMap.keys())), [4.0])

        m2 = a.parts[0].getElementsByClass(Measure)[2]
        mOffsetMap = m2.measureOffsetMap([note.Note])
        # offset here is that of measure that originally contained this note
        self.assertEqual(sorted(list(mOffsetMap.keys())), [8.0])

        mOffsetMap = a.flatten().measureOffsetMap(['Note'])
        self.assertEqual(sorted(mOffsetMap.keys()),
                         [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0, 34.0, 38.0])

    def testMeasureOffsetMapPostTie(self):
        a = corpus.parse('bach/bwv4.8')
        # alto line syncopated/tied notes across bars
        # a.show()
        alto = a.parts[1]
        countedAltoNotes = 52
        self.assertEqual(len(alto.flatten().notesAndRests), countedAltoNotes)

        correctMeasureOffsetMap = [0.0, 1.0, 5.0, 9.0, 13.0, 16.0, 20.0, 24.0,
                                   28.0, 31.0, 32.0, 36.0, 40.0, 44.0]
        # offset map for measures looking at the part's Measures
        # note that pickup bar is taken into account
        post = alto.measureOffsetMap()
        self.assertEqual(sorted(list(post.keys())), correctMeasureOffsetMap)

        # looking at Measure and Notes: no problem
        post = alto.flatten().measureOffsetMap([Measure, note.Note])
        self.assertEqual(sorted(list(post.keys())), correctMeasureOffsetMap)

        # after stripping ties, we have a stream with fewer notes
        altoPostTie = a.parts[1].stripTies()
        self.assertEqual(len(altoPostTie.flatten().notesAndRests), countedAltoNotes - 2)

        # we can still get measure numbers:
        mNo = altoPostTie.flatten().notesAndRests[3].getContextByClass(Measure).number
        self.assertEqual(mNo, 1)
        mNo = altoPostTie.flatten().notesAndRests[8].getContextByClass(Measure).number
        self.assertEqual(mNo, 2)
        mNo = altoPostTie.flatten().notesAndRests[15].getContextByClass(Measure).number
        self.assertEqual(mNo, 4)

        # can we get an offset Measure map by looking for measures
        post = altoPostTie.measureOffsetMap([Measure])
        # yes, retainContainers defaults to True
        self.assertEqual(list(post.keys()), correctMeasureOffsetMap)

    def testMusicXMLGenerationViaPropertyA(self):
        '''
        Test output tests above just by calling the musicxml attribute
        '''
        a = ['c', 'g#', 'd-', 'f#', 'e', 'f'] * 4

        partOffset = 7.5
        p = Stream()
        for pitchName in a:
            n = note.Note(pitchName)
            n.quarterLength = 1.5
            p.append(n)
        p.offset = partOffset

        p.transferOffsetToElements()

        junk = p.getTimeSignatures(searchContext=True, sortByCreationTime=True)
        p.makeRests(refStreamOrTimeRange=[0, 100], inPlace=True)

        self.assertEqual(p.lowestOffset, 0)
        self.assertEqual(p.highestTime, 100.0)

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(p).decode('utf-8')

        # can only recreate problem in the context of two Streams
        s = Stream()
        partOffsetShift = 1.25
        partOffset = 7.5
        for unused_x in range(2):
            p = Stream()
            for pitchName in a:
                n = note.Note(pitchName)
                n.quarterLength = 1.5
                p.append(n)
            p.offset = partOffset
            s.insert(p)
            partOffset += partOffsetShift

        # s.show()
        unused_mx = GEX.parse(p).decode('utf-8')

    def testMusicXMLGenerationViaPropertyB(self):
        '''
        Test output tests above just by calling the musicxml attribute
        '''
        n = note.Note()
        n.quarterLength = 3
        a = Stream()
        a.repeatInsert(n, list(range(0, 120, 3)))
        # a.show()  # default time signature used
        a.insert(0, meter.TimeSignature('5/4'))
        a.insert(10, meter.TimeSignature('2/4'))
        a.insert(3, meter.TimeSignature('3/16'))
        a.insert(20, meter.TimeSignature('9/8'))
        a.insert(40, meter.TimeSignature('10/4'))

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(a).decode('utf-8')

    def testMusicXMLGenerationViaPropertyC(self):
        '''
        Test output tests above just by calling the musicxml attribute
        '''

        a = ['c', 'g#', 'd-', 'f#', 'e', 'f'] * 4

        s = Stream()
        partOffsetShift = 1.25
        partOffset = 0
        p = None
        for unused_part in range(6):
            p = Stream()
            for pitchName in a:
                n = note.Note(pitchName)
                n.quarterLength = 1.5
                p.append(n)
            p.offset = partOffset
            s.insert(p)
            partOffset += partOffsetShift
        # s.show()
        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(p).decode('utf-8')

    def testContextNestedA(self):
        '''
        Testing getting clefs from higher-level streams
        '''
        s1 = Stream()
        s2 = Stream()
        n1 = note.Note()
        c1 = clef.AltoClef()
        c1.priority = -1  # perhaps clefs should sort before streams?

        s1.append(n1)  # this is the model of a stream with a single part
        s2.append(s1)
        s2.insert(0, c1)

        # from the lower level stream, we should be able to get to the
        # higher level clef
        post = s1.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)
        # environLocal.printDebug(['sites.get() of s1', s1.sites.get()])

        # attempting to move the substream into a new stream
        s3 = Stream()
        s3.insert(s1)  # insert at same offset as s2

        # we cannot get the alto clef from s3; this makes sense
        post = s3.getContextByClass(clef.Clef)
        self.assertIsNone(post)  # was TrebleClef in virtue of getClefs() giving default

        # s1 has both streams as sites
        self.assertIn(s3, s1.sites)
        self.assertIn(s2, s1.sites)

        # if we search s1, we should find an alto clef
        post = s1.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

        sMeasures = s2.makeMeasures(finalBarline='regular')
        self.assertEqual(len(sMeasures), 2)  # AltoClef and substream
        self.assertEqual(len(sMeasures.last().getElementsByClass(Measure)), 1)
        madeMeasure = sMeasures.recurse().getElementsByClass(Measure).first()
        self.assertEqual(len(madeMeasure), 3)
        # first is clef
        self.assertIsInstance(madeMeasure.first(), clef.AltoClef)
        # second is sig
        self.assertEqual(str(madeMeasure[1]), '<music21.meter.TimeSignature 4/4>')
        # sMeasures.show('t')
        # the third element is a Note; we get it from flattening during
        # makeMeasures
        self.assertIsInstance(madeMeasure[2], note.Note)

        # this shows the proper output with the proper clef.
        # sMeasures.show()

        # new in v7 -- we can still get the topmost clef
        # because the substream was preserved rather than flattened
        # no need to destroy the global elements (clef) either
        post = sMeasures.getElementsByClass(clef.Clef)
        self.assertEqual(len(post), 1)

    def testContextNestedB(self):
        '''
        Testing getting clefs from higher-level streams
        '''
        sInner = Stream()
        sInner.id = 'innerStream'
        n1 = note.Note()
        sInner.append(n1)  # this is the model of a stream with a single part

        sOuter = Stream()
        sOuter.id = 'outerStream'
        sOuter.append(sInner)
        c1 = clef.AltoClef()
        c1.priority = -1
        sOuter.insert(0, c1)

        # this works fine
        post = sInner.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

        # if we flatten sInner, we cannot still get the clef: why?
        sInnerFlat = sInner.flatten()
        sInnerFlat.id = 'sInnerFlat'

        # # but it has sOuter has a context
        # self.assertIn(sOuter, sInnerFlat.sites)
        # # environLocal.printDebug(['sites.get() of sInnerFlat', sInnerFlat.sites.get()])
        # # environLocal.printDebug(['sites.siteDict of sInnerFlat', sInnerFlat.sites.siteDict])
        # self.assertIn(sOuter, sInnerFlat.sites)

        # # this returns the proper dictionary entry
        # # environLocal.printDebug(
        # #    ['sInnerFlat.sites.siteDict[id(sInner)', sInnerFlat.sites.siteDict[id(sOuter)]])
        # # we can extract out the same reference
        # unused_sOuterOut = sInnerFlat.sites.getById(id(sOuter))

        # this works
        post = sInnerFlat.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

        # 2014 April -- tree version -- not needed
        # this will only work if the callerFirst is manually set to sInnerFlat
        # otherwise, this interprets the DefinedContext object as the first
        # caller
        # pst = sInnerFlat.sites.getObjByClass(clef.Clef, callerFirst=sInnerFlat)
        # self.assertIsInstance(post, clef.AltoClef)

    def testContextNestedC(self):
        '''
        Testing getting clefs from higher-level streams
        '''
        from music21.common.enums import ElementSearch

        s1 = Stream(id='s1')
        n1 = note.Note()

        s1.append(n1)  # this is the model of a stream with a single part

        s2 = Stream(id='s2')
        s2.append(s1)

        c1 = clef.AltoClef()
        c1.priority = -1
        s2.insert(0, c1)

        # this works fine
        post = s1.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

        # this is a key tool of the serial reverse search
        post = s2.getElementAtOrBefore(0, [clef.Clef])
        self.assertIsInstance(post, clef.AltoClef)

        # this is a key tool of the serial reverse search
        post = s2.flatten().getElementAtOrBefore(0, [clef.Clef])
        self.assertIsInstance(post, clef.AltoClef)

        # s1 is in s2; but s1.flatten() is not in s2! -- not true if isFlat is true
        self.assertEqual(s2.elementOffset(s1), 0.0)
        self.assertRaises(sites.SitesException, s2.elementOffset, s1.flatten())

        post = s2.getContextByClass(clef.Clef, getElementMethod=ElementSearch.ALL)
        self.assertIsInstance(post, clef.AltoClef)

        self.assertIsInstance(s2.clef, clef.AltoClef)

        # we can find the clef from the flat version of s1 also:
        post = s1.flatten().getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

    def testContextNestedD(self):
        '''
        Testing getting clefs from higher-level streams
        '''
        n1 = note.Note()
        n2 = note.Note()

        s1 = Part()
        s1.id = 's1'
        s2 = Part()
        s2.id = 's2'

        sOuter = Score()
        sOuter.id = 'sOuter'

        s1.append(n1)
        s2.append(n2)
        sOuter.insert(0, s1)
        sOuter.insert(0, s2)

        self.assertIs(s1.activeSite, sOuter)

        ac = clef.AltoClef()
        ac.priority = -1
        sOuter.insert(0, ac)
        # both output parts have alto clefs
        # get clef from higher level stream; only option
        self.assertIs(s1.activeSite, sOuter)
        post = s1.getContextByClass(clef.Clef)

        self.assertIsInstance(post, clef.AltoClef)
        self.assertIs(s1.activeSite, sOuter)

        post = s2.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

        # now we insert a clef in s2; s2 will get this clef first
        tenorC = clef.TenorClef()
        tenorC.priority = -1
        s2.insert(0, tenorC)
        # only second part should have tenor clef
        post = s2.getElementsByClass(clef.Clef)
        self.assertIsInstance(post[0], clef.TenorClef)

        # but stream s1 should get the alto clef still
        # print(list(s1.contextSites()))
        post = s1.getContextByClass(clef.Clef)
        # print(post)
        self.assertIsInstance(post, clef.AltoClef)

        # s2 flat gets the tenor clef; it was inserted in it
        post = s2.flatten().getElementsByClass(clef.Clef)
        self.assertIsInstance(post[0], clef.TenorClef)

        # a copy copies the clef; so we still get the same clef
        s2FlatCopy = copy.deepcopy(s2.flatten())
        post = s2FlatCopy.getElementsByClass(clef.Clef)
        self.assertIsInstance(post[0], clef.TenorClef)

        # s1 flat will get the alto clef; it still has a pathway
        post = s1.flatten().getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

        # once we create a deepcopy of s1, it is no longer connected to
        # its parent if we purge orphans and it is not in sOuter
        s1Flat = s1.flatten()
        s1Flat.id = 's1Flat'
        s1FlatCopy = copy.deepcopy(s1Flat)
        s1FlatCopy.id = 's1FlatCopy'
        self.assertIsNotNone(s1FlatCopy.getContextByClass(clef.Clef))
        post = s1FlatCopy.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef)

        post = s1Flat.getContextByClass(clef.Clef)
        self.assertIsInstance(post, clef.AltoClef, post)
        # environLocal.printDebug(['s1.activeSite', s1.activeSite])
        self.assertIn(sOuter, s1.sites.get())
        s1Measures = s1.makeMeasures()
        # print(s1Measures[0].clef)

        self.assertIsInstance(s1Measures[0].clef, clef.AltoClef)
        # this used to be False, then True, and the tiniest change to makeMeasures made it False
        # again.  I think it's better as "False" now
        # self.assertIsInstance(s1Measures[0].clef, clef.TrebleClef)

        s2Measures = s2.makeMeasures()
        self.assertIsInstance(s2Measures[0].clef, clef.TenorClef)

        # try making a deep copy of s3

        s3copy = copy.deepcopy(sOuter)
        # sMeasures = s3copy[0].makeMeasures()

        # TODO: had to comment out with changes to getElementAtOrBefore
        # problem is sort order of found elements at or before
        # if two elements of the same class are found at the same offset
        # they cannot be distinguished
        # perhaps need to return more than one;
        # or getElementAtOrBefore needs to return a list

        s2Measures = s3copy.getElementsByClass(Stream)[1].makeMeasures()
        self.assertIsInstance(s2Measures[0].clef, clef.TenorClef)
        # s2Measures.show()  # this shows the proper clef

        # TODO: this still returns tenor clef for both parts
        # need to examine

        # now we insert a clef in s2; s2 will get this clef first
        s1.insert(0, clef.BassClef())
        post = s1.getElementsByClass(clef.Clef)
        self.assertIsInstance(post[0], clef.BassClef)

        # s3.show()

    def testMakeRestsA(self):
        a = ['c', 'g#', 'd-', 'f#', 'e', 'f'] * 4
        partOffsetShift = 1.25
        partOffset = 2  # start at non zero
        for unused_part in range(6):
            p = Stream()
            for pitchName in a:
                n = note.Note(pitchName)
                n.quarterLength = 1.5
                p.append(n)
            p.offset = partOffset

            self.assertEqual(p.lowestOffset, 0)

            p.transferOffsetToElements()
            self.assertEqual(p.lowestOffset, partOffset)

            p.makeRests(inPlace=True)

            # environLocal.printDebug(['first element', p[0], p[0].duration])
            # by default, initial rest should be made
            sub = p.getElementsByClass(note.Rest).stream()
            self.assertEqual(len(sub), 1)

            self.assertEqual(sub.duration.quarterLength, partOffset)

            # first element should have offset of first dur
            self.assertEqual(p[1].offset, sub.duration.quarterLength)

            partOffset += partOffsetShift

    def testMakeRestsB(self):
        # test makeRests fillGaps
        s = Stream()
        m1 = Measure()
        m1.timeSignature = meter.TimeSignature('4/4')
        m1.insert(2, note.Note())
        m2 = Measure()
        m2.insert(1, note.Note())
        self.assertTrue(m2.isSorted)

        s.insert(0, m1)
        s.insert(4, m2)
        s.makeRests(inPlace=True, fillGaps=True, timeRangeFromBarDuration=True)
        self.assertTrue(m2.isSorted)
        # m2.sort()

        match = str([(n.offset, n, n.duration) for n in m2.flatten().notesAndRests])
        self.assertEqual(match,
                         '[(0.0, <music21.note.Rest quarter>, <music21.duration.Duration 1.0>), '
                         + '(1.0, <music21.note.Note C>, <music21.duration.Duration 1.0>), '
                         + '(2.0, <music21.note.Rest half>, <music21.duration.Duration 2.0>)]')

        match = str([(n.offset, n, n.duration) for n in m2.flatten()])
        self.assertEqual(match,
                         '[(0.0, <music21.note.Rest quarter>, <music21.duration.Duration 1.0>), '
                         + '(1.0, <music21.note.Note C>, <music21.duration.Duration 1.0>), '
                         + '(2.0, <music21.note.Rest half>, <music21.duration.Duration 2.0>)]')

        # m2.show()

        match = str(list(s.flatten().notesAndRests))
        self.assertEqual(match, '[<music21.note.Rest half>, <music21.note.Note C>, '
                                  + '<music21.note.Rest quarter>, <music21.note.Rest quarter>, '
                                  + '<music21.note.Note C>, <music21.note.Rest half>]')
        match = str([(n, n.duration) for n in s.flatten().notesAndRests])
        self.assertEqual(match,
                         '[(<music21.note.Rest half>, <music21.duration.Duration 2.0>), '
                          + '(<music21.note.Note C>, <music21.duration.Duration 1.0>), '
                          + '(<music21.note.Rest quarter>, <music21.duration.Duration 1.0>), '
                          + '(<music21.note.Rest quarter>, <music21.duration.Duration 1.0>), '
                          + '(<music21.note.Note C>, <music21.duration.Duration 1.0>), '
                          + '(<music21.note.Rest half>, <music21.duration.Duration 2.0>)]')

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(s).decode('utf-8')
        # s.show('text')
        # s.show()

    def testMakeRestsInMeasures(self):
        p = Part()
        m1 = Measure()
        m1.timeSignature = meter.TimeSignature('4/4')
        m1.insert(2, note.Note())
        m2 = Measure()
        m2.insert(1, note.Note())
        p.append(m1)
        p.append(m2)

        self.assertEqual(m1.duration.quarterLength, 3.0)
        self.assertEqual(m2.duration.quarterLength, 2.0)
        self.assertEqual(p.duration.quarterLength, 5.0)

        for m in (m1, m2):
            m.makeRests(inPlace=True, timeRangeFromBarDuration=True)

        self.assertEqual(m1.duration.quarterLength, 4.0)
        self.assertEqual(m2.duration.quarterLength, 4.0)

        # m2 was never repositioned in p
        self.assertEqual(p.duration.quarterLength, 7.0)

        p.makeRests(inPlace=True)
        self.assertEqual(p.duration.quarterLength, 8.0)

    def testMakeRestsInMeasuresWithVoices(self):
        p = Part()
        m = Measure(meter.TimeSignature('4/4'), number=1)
        v1 = Voice(note.Note(quarterLength=3.5))
        v2 = Voice(note.Note(quarterLength=3.75))
        m.insert(0, v1)
        m.insert(0, v2)
        p.insert(0, m)

        post = p.makeRests(inPlace=False, timeRangeFromBarDuration=True)

        # No loose rests outside voices
        self.assertEqual(len(post.first().getElementsByClass(note.Rest)), 0)
        # Total of two rests, one in each voice
        self.assertEqual(len(post.recurse().getElementsByClass(note.Rest)), 2)

        # Wrap into Score
        sc = Score([p])
        post = sc.makeRests(inPlace=False, timeRangeFromBarDuration=True)
        # No loose rests outside parts
        self.assertEqual(len(post.first().getElementsByClass(note.Rest)), 0)
        # ... or outside measures
        self.assertEqual(len(post.first().measure(1).getElementsByClass(note.Rest)), 0)
        # Total of two rests, one in each voice
        self.assertEqual(len(post.recurse().getElementsByClass(note.Rest)), 2)

    def testMakeRestsByMakingVoices(self):
        # Create incomplete measure with overlaps, like a MIDI file
        m = Measure(meter.TimeSignature('4/4'), number=1)
        m.insert(0, note.Note(quarterLength=3.5))
        m.insert(0, note.Note(quarterLength=3.75))
        m.makeVoices(inPlace=True)

        # No loose rests outside voices
        self.assertEqual(len(m.getElementsByClass(note.Rest)), 0)
        # Total of two rests, one in each voice. Recursive search.
        self.assertEqual(len(m[note.Rest]), 2)

    def testMakeMeasuresInPlace(self):
        sScr = Stream()
        sScr.insert(0, clef.TrebleClef())
        sScr.insert(0, meter.TimeSignature('3/4'))
        sScr.append(note.Note('C4', quarterLength=3.0))
        sScr.append(note.Note('D4', quarterLength=3.0))
        sScr.makeMeasures(inPlace=True)
        self.assertEqual(len(sScr.getElementsByClass(Measure)), 2)
        self.assertEqual(sScr.measure(1).notes[0].name, 'C')
        self.assertEqual(sScr.measure(2).notes[0].name, 'D')

    def testMakeMeasuresMeterStream(self):
        '''
        Testing making measures of various sizes with a supplied single element meter stream.
        This illustrates an approach to partitioning elements by various sized windows.
        '''
        sBach = corpus.parse('bach/bwv324.xml')
        meterStream = Stream()
        meterStream.insert(0, meter.TimeSignature('2/4'))
        # need to call make ties to allocate notes
        sPartitioned = sBach.flatten().makeMeasures(meterStream).makeTies(
            inPlace=False)
        self.assertEqual(len(sPartitioned.getElementsByClass(Measure)), 21)

        meterStream = Stream()
        meterStream.insert(0, meter.TimeSignature('1/4'))
        # need to call make ties to allocate notes
        sPartitioned = sBach.flatten().makeMeasures(meterStream).makeTies(
            inPlace=False)
        self.assertEqual(len(sPartitioned.getElementsByClass(Measure)), 42)

        meterStream = Stream()
        meterStream.insert(0, meter.TimeSignature('3/4'))
        # need to call make ties to allocate notes
        sPartitioned = sBach.flatten().makeMeasures(meterStream).makeTies(
            inPlace=False)
        self.assertEqual(len(sPartitioned.getElementsByClass(Measure)), 14)

        meterStream = Stream()
        meterStream.insert(0, meter.TimeSignature('12/4'))
        # need to call make ties to allocate notes
        sPartitioned = sBach.flatten().makeMeasures(meterStream).makeTies(
            inPlace=False)
        self.assertEqual(len(sPartitioned.getElementsByClass(Measure)), 4)

        meterStream = Stream()
        meterStream.insert(0, meter.TimeSignature('48/4'))
        # need to call make ties to allocate notes
        sPartitioned = sBach.flatten().makeMeasures(meterStream).makeTies(
            inPlace=False)
        self.assertEqual(len(sPartitioned.getElementsByClass(Measure)), 1)

    def testMakeMeasuresWithBarlines(self):
        '''
        Test makeMeasures with optional barline parameters.
        '''
        s = Stream()
        s.repeatAppend(note.Note(quarterLength=0.5), 20)
        s.insert(0, meter.TimeSignature('5/8'))

        # default is no normal barlines, but a final barline
        barred1 = s.makeMeasures()
        self.assertEqual(
            str(barred1.getElementsByClass(Measure).last().rightBarline),
            '<music21.bar.Barline type=final>')
        # barred1.show()

        barred2 = s.makeMeasures(innerBarline='dashed', finalBarline='double')
        match = [str(m.rightBarline) for m in
                 barred2.getElementsByClass(Measure)]
        self.assertEqual(match, ['<music21.bar.Barline type=dashed>',
                                 '<music21.bar.Barline type=dashed>',
                                 '<music21.bar.Barline type=dashed>',
                                 '<music21.bar.Barline type=double>'])
        # barred2.show()

        # try using bar objects
        bar1 = bar.Barline('none')
        bar2 = bar.Barline('short')
        barred3 = s.makeMeasures(innerBarline=bar1, finalBarline=bar2)
        # barred3.show()
        match = [str(m.rightBarline) for m in
                 barred3.getElementsByClass(Measure)]
        self.assertEqual(match, ['<music21.bar.Barline type=none>',
                                 '<music21.bar.Barline type=none>',
                                 '<music21.bar.Barline type=none>',
                                 '<music21.bar.Barline type=short>'])

        # setting to None will not set a barline object at all
        barred4 = s.makeMeasures(innerBarline=None, finalBarline=None)
        match = [str(m.rightBarline) for m in
                 barred4.getElementsByClass(Measure)]
        self.assertEqual(match, ['None', 'None', 'None', 'None'])

    def testMakeMeasuresLastElementNoDuration(self):
        s = Stream()
        s.append(meter.TimeSignature('3/4'))
        obj = expressions.TextExpression('FREEZE')
        s.insert(3, obj)
        s.makeMeasures(inPlace=True)
        self.assertEqual(len(s['Expression']), 1)

    def testRemove(self):
        '''
        Test removing components from a Stream.
        '''
        s = Stream()
        n1 = note.Note('g')
        n2 = note.Note('g#')
        n3 = note.Note('a')

        s.insert(0, n1)
        s.insert(10, n3)
        s.insert(5, n2)

        self.assertEqual(len(s), 3)

        self.assertEqual(n1.activeSite, s)
        s.remove(n1)
        self.assertEqual(len(s), 2)
        # activeSite is Now sent to None
        self.assertEqual(n1.activeSite, None)

        expected = "clef.TrebleClef is not a Music21Object; got <class 'str'>"
        with self.assertRaisesRegex(TypeError, expected):
            # noinspection PyTypeChecker
            s.remove('clef.TrebleClef')  # cannot remove by Class str.

    def testRemoveByClass(self):
        s = Stream()
        s.repeatAppend(clef.BassClef(), 2)
        s.repeatAppend(note.Note(), 2)
        s.repeatAppend(clef.TrebleClef(), 2)

        self.assertEqual(len(s), 6)
        s.removeByClass('BassClef')
        self.assertEqual(len(s), 4)
        self.assertEqual(len(s.notes), 2)
        s.removeByClass(clef.Clef)
        self.assertEqual(len(s), 2)
        self.assertEqual(len(s.notes), 2)
        s.removeByClass(['Music21Object'])
        self.assertEqual(len(s.notes), 0)

    def testReplace(self):
        '''
        Test replacing components from a Stream.
        '''
        s = Stream()
        n1 = note.Note('g')
        n2 = note.Note('g#')
        n3 = note.Note('a')
        n4 = note.Note('c')

        s.insert(0, n1)
        s.insert(5, n2)

        self.assertEqual(len(s), 2)

        s.replace(n1, n3)
        self.assertEqual([s[0], s[1]], [n3, n2])

        s.replace(n2, n4)
        self.assertEqual([s[0], s[1]], [n3, n4])

        s.replace(n4, n1)
        self.assertEqual([s[0], s[1]], [n3, n1])

        expected = f'{n3} already in {s}'
        with self.assertRaisesRegex(StreamException, expected):
            s.replace(n4, n3)

    def testReplaceA1(self):
        sBach = corpus.parse('bach/bwv324.xml')
        partSoprano = sBach.parts.first()

        c1 = partSoprano.flatten().getElementsByClass(clef.Clef).first()
        self.assertIsInstance(c1, clef.TrebleClef)

        # now, replace with a different clef
        c2 = clef.AltoClef()
        partSoprano.flatten().replace(c1, c2, allDerived=True)

        # all views of the Stream have been updated
        cTest = sBach.parts.first().flatten().getElementsByClass(clef.Clef).first()
        self.assertIsInstance(cTest, clef.AltoClef)

    def testReplaceB(self):
        n1 = note.Note('g')
        n2 = note.Note('g#')

        s0 = Stream()
        s1 = copy.deepcopy(s0)
        s2 = copy.deepcopy(s1)
        s3 = Stream()
        s0.insert(0, n1)
        s1.insert(10, n1)
        s2.insert(20, n1)
        s3.insert(30, n1)

        s1.replace(n1, n2, allDerived=True)

        # s1 is derived from s0 so n1 is replaced
        self.assertIs(s0[0], n2)
        self.assertEqual(s0[0].getOffsetBySite(s0), 0)

        # s1 was the replacement stream, so definitely n1 becomes n2
        self.assertIs(s1[0], n2)
        self.assertEqual(s1[0].getOffsetBySite(s1), 10)

        # s2 was derived from s0, not vice versa, so n1 is left alone.
        self.assertIs(s2[0], n1)
        self.assertEqual(s2[0].getOffsetBySite(s2), 20)

        # s3 is completely out of any derivation chain, so left alone
        self.assertIs(s3[0], n1)
        self.assertEqual(s3[0].getOffsetBySite(s3), 30)

    def testReplaceDerived(self):
        qj = corpus.parse('ciconia/quod_jactatur').parts[0].measures(1, 2)
        qj.id = 'measureExcerpt'

        qj_flat = qj.flatten()
        dc = list(qj_flat.derivation.chain())
        self.assertIs(dc[0], qj)

        k1 = qj_flat.getElementsByClass(key.KeySignature).first()
        self.assertEqual(k1.sharps, -1)
        k3flats = key.KeySignature(-3)

        # put k1 in an unrelated site:
        mUnrelated = Measure()
        mUnrelated.insert(0, k1)

        # here's the big one
        qj_flat.replace(k1, k3flats, allDerived=True)

        kWhich = qj_flat.getElementsByClass(key.KeySignature).first()
        self.assertIs(kWhich, k3flats)
        self.assertEqual(kWhich.sharps, -3)

        kWhich2 = qj.recurse().getElementsByClass(key.KeySignature).first()
        self.assertIs(kWhich2, k3flats)
        self.assertEqual(kWhich2.sharps, -3)

        # check that unrelated is untouched
        self.assertIs(mUnrelated[0], k1)

    def testDoubleStreamPlacement(self):
        n1 = note.Note()
        s1 = Stream()
        s1.insert(n1)

        # environLocal.printDebug(['n1.siteIds after one insertion', n1,
        #            n1.sites.get(), n1.sites.getSiteIds()])

        s2 = Stream()
        s2.insert(s1)

        # environLocal.printDebug(['n1.siteIds after container insertion', n1,
        #                n1.sites.get(), n1.sites.getSiteIds()])

        s2Flat = s2.flatten()

        # environLocal.printDebug(['s1', s1, id(s1)])
        # environLocal.printDebug(['s2', s2, id(s2)])
        # environLocal.printDebug(['s2flat', s2Flat, id(s2Flat)])

        # environLocal.printDebug(['n1.siteIds', n1, n1.sites.get(), n1.sites.getSiteIds()])

        # previously, one of these raised an error
        unused_s3 = copy.deepcopy(s2Flat)

        s3 = copy.deepcopy(s2.flatten())
        unused_s3Measures = s3.makeMeasures()

    def testBestTimeSignature(self):
        '''
        Get a time signature based on components in a measure.
        '''
        m = Measure()
        for ql in [2, 3, 2]:
            n = note.Note()
            n.quarterLength = ql
            m.append(n)
        ts = m.bestTimeSignature()
        self.assertEqual(ts.numerator, 7)
        self.assertEqual(ts.denominator, 4)

        m = Measure()
        for ql in [1.5, 1.5]:
            n = note.Note()
            n.quarterLength = ql
            m.append(n)
        ts = m.bestTimeSignature()
        self.assertEqual(ts.numerator, 6)
        self.assertEqual(ts.denominator, 8)

        m = Measure()
        for ql in [0.25, 1.5]:
            n = note.Note()
            n.quarterLength = ql
            m.append(n)
        ts = m.bestTimeSignature()
        self.assertEqual(ts.numerator, 7)
        self.assertEqual(ts.denominator, 16)

    def testGetKeySignatures(self):
        '''
        Searching contexts for key signatures
        '''
        s = Stream()
        ks1 = key.KeySignature(1)
        ks2 = key.KeySignature(-2)
        s.append(ks1)
        s.append(ks2)
        post = s.getElementsByClass(key.KeySignature)
        self.assertEqual(post[0], ks1)
        self.assertEqual(post[1], ks2)

        # try creating a key signature in one of two measures
        # try to get last active key signature
        ks1 = key.KeySignature(3)
        m1 = Measure()
        n1 = note.Note()
        n1.quarterLength = 4
        m1.append(n1)
        m1.keySignature = ks1  # assign to measure via property

        m2 = Measure()
        n2 = note.Note()
        n2.quarterLength = 4
        m2.append(n2)

        s = Stream()
        s.append(m1)
        s.append(m2)

        # can get from measure
        post = m1.getElementsByClass(key.KeySignature)
        self.assertIs(post[0], ks1)

        # we can get from the Stream by flattening
        post = s.flatten().getElementsByClass(key.KeySignature)
        self.assertIs(post[0], ks1)

        # we can get the key signature in m1 from m2
        post = m2.getContextByClass(key.KeySignature)
        self.assertIs(post, ks1)

    def testGetKeySignaturesThreeMeasures(self):
        '''
        Searching contexts for key signatures
        '''

        ks1 = key.KeySignature(1)
        ks3 = key.KeySignature(3)

        m1 = Measure()
        n1 = note.Note()
        n1.quarterLength = 4
        m1.append(n1)
        m1.keySignature = ks1  # assign to measure via property

        m2 = Measure()
        n2 = note.Note()
        n2.quarterLength = 4
        m2.append(n2)

        m3 = Measure()
        n3 = note.Note()
        n3.quarterLength = 4
        m3.append(n3)
        m3.keySignature = ks3  # assign to measure via property

        s = Stream()
        s.append(m1)
        s.append(m2)
        s.append(m3)

        # can get from measure
        post = m1.getElementsByClass(key.KeySignature)
        self.assertIs(post[0], ks1)

        # we can get the key signature in m1 from m2
        post = m2.getContextByClass(key.KeySignature)
        self.assertIs(post, ks1)

        # if we search m3, we get the key signature in m3
        post = m3.getContextByClass(key.KeySignature)
        self.assertIs(post, ks1)

    def testMakeAccidentalsA(self):
        '''
        Test accidental display setting
        '''
        s = Stream()
        n1 = note.Note('a#')
        n2 = note.Note('a4')
        r1 = note.Rest()
        c1 = chord.Chord(['a#2', 'a4', 'a5'])
        n3 = note.Note('a4')
        s.append(n1)
        s.append(r1)
        s.append(n2)
        s.append(c1)
        s.append(n3)
        s.makeAccidentals(inPlace=True)

        self.assertTrue(n2.pitch.accidental.displayStatus)
        # Both A-naturals in the chord show accidentals
        self.assertTrue(c1.pitches[1].accidental.displayStatus)
        self.assertTrue(c1.pitches[2].accidental.displayStatus)

        # not necessary to repeat the natural afterward
        self.assertIsNone(n3.pitch.accidental, None)

        s = Stream()
        n1 = note.Note('a#')
        n2 = note.Note('a')
        r1 = note.Rest()
        c1 = chord.Chord(['a#2', 'a4', 'a5'])
        s.append(n1)
        s.append(r1)
        s.append(n2)
        s.append(c1)
        s.makeAccidentals(cautionaryPitchClass=False, inPlace=True)

        # a's in the chord do not have naturals
        self.assertEqual(c1.pitches[1].accidental, None)
        self.assertEqual(c1.pitches[2].accidental, None)

    def testMakeAccidentalsB(self):
        s = corpus.parse('monteverdi/madrigal.5.3.rntxt')
        m34 = s.parts[0].getElementsByClass(Measure)[33]
        c = m34.getElementsByClass(chord.Chord)
        # assuming not showing accidental b/c of key
        self.assertEqual(str(c[1].pitches), '(<music21.pitch.Pitch B-4>, '
                            + '<music21.pitch.Pitch D5>, <music21.pitch.Pitch F5>)')
        # because of key
        self.assertEqual(str(c[1].pitches[0].accidental.displayStatus), 'False')

        s = corpus.parse('monteverdi/madrigal.5.4.rntxt')
        m74 = s.parts[0].getElementsByClass(Measure)[73]
        c = m74.getElementsByClass(chord.Chord)
        # has correct pitches but natural not showing on C
        self.assertEqual(str(c[0].pitches),
                         '(<music21.pitch.Pitch C5>, <music21.pitch.Pitch E5>, '
                            + '<music21.pitch.Pitch G5>)')
        self.assertEqual(str(c[0].pitches[0].accidental), 'None')

    def testMakeAccidentalsC(self):
        # this isolates the case where a new measure uses an accidental
        # that was used in a past measure

        m1 = Measure()
        m1.repeatAppend(note.Note('f4'), 2)
        m1.repeatAppend(note.Note('f#4'), 2)
        m2 = Measure()
        m2.repeatAppend(note.Note('f#4'), 4)

        ex = Part()
        ex.append([m1, m2])
        # without applying make accidentals, all sharps are shown
        self.assertEqual(len(ex.flatten().notes), 8)
        self.assertEqual(len(ex.flatten().notes[2:]), 6)
        # ex.flatten().notes[2:].show()

        # all sharps, unknown display status (displayStatus is None)
        acc = [str(n.pitch.accidental) for n in ex.flatten().notes[2:]]
        self.assertEqual(acc, ['sharp'] * 6)
        display = [n.pitch.accidental.displayStatus for n in ex.flatten().notes[2:]]
        self.assertEqual(display, [None, None, None, None, None, None])

        # call make accidentals
        # cautionaryNotImmediateRepeat=True is default
        # cautionaryPitchClass=True is default
        ex.makeAccidentals(inPlace=True)

        display = [n.pitch.accidental.displayStatus for n in ex.flatten().notes[2:]]
        # need the second true b/c it is the start of a new measure
        self.assertEqual(display, [True, False, True, False, False, False])

        p = Part()
        p.insert(0, meter.TimeSignature('2/4'))
        tuplet1 = note.Note('E-4', quarterLength=1 / 3)
        tuplet2 = note.Note('F#4', quarterLength=2 / 3)
        p.repeatAppend(tuplet1, 10)
        p.repeatAppend(tuplet2, 7)
        ex = p.makeNotation()
        # ex.show('text')

        display = [n.pitch.accidental.displayStatus for n in ex.flatten().notes]
        self.assertEqual(display, [1, 0, 0, 0, 0, 0,
                                   1, 0, 0, 0, 1,
                                   1, 0, 0,
                                   1, 0, 0])

    def testMakeAccidentalsD(self):
        p1 = Part()
        m1 = Measure()
        m1.append(meter.TimeSignature('4/4'))
        m1.append(note.Note('C#', type='half'))
        m1.append(note.Note('C#', type='half'))
        m1.rightBarline = 'final'
        p1.append(m1)
        p1.makeNotation(inPlace=True)

        match = [p.accidental.displayStatus for p in p1.pitches]
        self.assertEqual(match, [True, False])
        m = p1.measure(1)
        self.assertEqual(str(m.rightBarline), '<music21.bar.Barline type=final>')

    def testMakeAccidentalsInScore(self):
        '''
        Making accidentals on a score having a part with measures
        should still reiterate accidentals measure by measure.
        '''
        n1 = note.Note('f#', type='whole')
        n2 = note.Note('f#', type='whole')
        m1 = Measure(n1)
        m2 = Measure(n2)
        p = Part([m1, m2])
        s = Score(p)
        s.makeAccidentals(inPlace=True)
        self.assertIs(s[note.Note].last().pitch.accidental.displayStatus, True)

    def testMakeAccidentalsWithKeysInMeasures(self):
        scale1 = ['c4', 'd4', 'e4', 'f4', 'g4', 'a4', 'b4', 'c5']
        scale2 = ['c', 'd', 'e-', 'f', 'g', 'a-', 'b-', 'c5']
        scale3 = ['c#', 'd#', 'e#', 'f#', 'g#', 'a#', 'b#', 'c#5']

        s = Stream()
        for scale in [scale1, scale2, scale3]:
            for ks in [key.KeySignature(0), key.KeySignature(2),
                       key.KeySignature(4), key.KeySignature(7), key.KeySignature(-1),
                       key.KeySignature(-3)]:

                m = Measure()
                m.timeSignature = meter.TimeSignature('4/4')
                m.keySignature = ks
                for p in scale * 2:
                    n = note.Note(p)
                    n.quarterLength = 0.25
                    n.addLyric(n.pitch.name)
                    m.append(n)
                m.makeBeams(inPlace=True)
                m.makeAccidentals(inPlace=True)
                s.append(m)
        # TODO: add tests
        # s.show()

    def testMakeAccidentalsTies(self):
        '''
        tests to make sure that Accidental display status is correct after a tie.
        '''
        bm = converter.parse(
            "tinynotation: 4/4 c#'2 b-2~ b-8 c#'8~ c#'8 b-8 c#'8 b-8~ b-8~ b-8",
            makeNotation=False)
        bm.makeNotation(inPlace=True, cautionaryNotImmediateRepeat=False)
        allNotes = bm.flatten().notes
        #      0C#  1B-~  | 2B-  3C#~  4C#    6B-     7C#    8B-~   9B-~   10B-
        ds = [True, True, False, True, False, True, False, False, False, False]
        for i, (dsi, thisNote) in enumerate(zip(ds, allNotes)):
            self.assertEqual(thisNote.pitch.accidental.displayStatus,
                             dsi,
                             f'{i} failed, {thisNote.pitch.accidental.displayStatus} != {dsi}')

        # add another B-flat just after the tied one
        bm = converter.parse(
            "tinynotation: 4/4 c#'2 b-2~ b-8 b-8 c#'8~ c#'8 b-8 c#'8 b-8~ b-8~ b-8",
            makeNotation=False)
        bm.makeNotation(inPlace=True, cautionaryNotImmediateRepeat=False)
        allNotes = bm.flatten().notes
        #      0C#  1B-~  | 2B-   3B-  4C#~  5C#    6B-     7C#    8B-~   9B-~  | 10B-
        ds = [True, True, False, True, True, False, False, False, False, False, False]
        for i, (dsi, thisNote) in enumerate(zip(ds, allNotes)):
            self.assertEqual(thisNote.pitch.accidental.displayStatus,
                             dsi,
                             f'{i} failed, {thisNote.pitch.accidental.displayStatus} != {dsi}')

    def testMakeAccidentalsRespectsDisplayType(self):
        n = note.Note('D#')
        n.pitch.accidental.displayType = 'never'
        s = Stream(n)
        self.assertIsNone(n.pitch.accidental.displayStatus)
        s.makeAccidentals(inPlace=True)
        self.assertIs(n.pitch.accidental.displayStatus, False)

        # TODO: other types

    def testMakeAccidentalsOnChord(self):
        c = chord.Chord('F# A# C#')
        s = Stream(c)
        self.assertFalse(any(n.pitch.accidental.displayStatus for n in c))
        s.makeAccidentals(inPlace=True)
        self.assertTrue(all(n.pitch.accidental.displayStatus for n in c))

        augmented_octave = chord.Chord('F4 F#5')
        s2 = Stream(augmented_octave)
        self.assertIsNone(augmented_octave[0].pitch.accidental)
        s2.makeAccidentals(inPlace=True)
        self.assertTrue(augmented_octave[0].pitch.accidental.displayStatus)

        # Repeat the test without octaves and reset state
        low, high = augmented_octave.pitches
        low.octave = None
        low.accidental = None
        high.octave = None
        high.accidental.displayStatus = None

        s2.makeAccidentals(inPlace=True)
        self.assertTrue(all(n.pitch.accidental.displayStatus for n in augmented_octave))

        # Repeat the test with two F#'s in key of 1 sharp
        two_f_sharps = chord.Chord('F#4 F#5')
        s3 = Stream([key.KeySignature(1), two_f_sharps])
        s3.makeAccidentals(inPlace=True)
        self.assertTrue(all(n.pitch.accidental.displayStatus is False for n in two_f_sharps))

    def testMakeNotationTiesKeyless(self):
        p = converter.parse('tinynotation: 4/4 f#1~ f#1')
        # Key of no sharps/flats
        p.measure(1).insert(0, key.KeySignature(sharps=0))
        # calls makeAccidentalsInMeasureStream()
        p.makeNotation(inPlace=True)
        self.assertIs(p.measure(2).notes.first().pitch.accidental.displayStatus, False)

    def testMakeNotationTiesKeyChange(self):
        p = converter.parse('tinynotation: 4/4 f#1~ f#1')
        # Insert key change where held-over note is diatonic
        p.measure(2).insert(0, key.KeySignature(sharps=1))
        made = p.makeNotation()
        self.assertIs(made.measure(2).notes.first().pitch.accidental.displayStatus, False)

        p = converter.parse('tinynotation: 4/4 f#1~ f#1')
        # Insert key change where held-over note is chromatic
        p.measure(2).insert(0, key.KeySignature(sharps=-1))
        made = p.makeNotation()
        self.assertIs(made.measure(2).notes.first().pitch.accidental.displayStatus, True)

        p = converter.parse('tinynotation: 4/4 b1~ b1')
        # Same, but with a natural
        p.measure(2).insert(0, key.KeySignature(sharps=-1))
        made = p.makeNotation()
        self.assertIs(made.measure(2).notes.first().pitch.accidental.displayStatus, True)

        p = converter.parse('tinynotation: 4/4 f#1~ f#1')
        p.measure(1).insert(0, key.KeySignature(sharps=-1))
        # This is no longer a key "change", should still work based on the tie
        made = p.makeNotation()
        self.assertIs(made.measure(2).notes.first().pitch.accidental.displayStatus, False)

        # Wipe out the tie; accidental should be reiterated
        for n in p.flatten().notes:
            n.tie = None
        made_no_ties = p.makeNotation()
        self.assertIs(made_no_ties.measure(2).notes.first().pitch.accidental.displayStatus, True)

    def testMakeAccidentalsOctaveKS(self):
        s = Stream()
        k = key.KeySignature(-3)
        s.append(k)
        s.append(note.Note('B-2'))
        s.append(note.Note('B-1'))
        for n in s.notes:
            self.assertEqual(n.pitch.accidental.displayStatus, None)

        s.makeAccidentals(inPlace=True)
        for n in s.notes:
            self.assertFalse(n.pitch.accidental.displayStatus)

    def testScaleOffsetsBasic(self):
        def procCompare(s_inner, scalar, match):
            oListSrc = [e.offset for e in s_inner]
            oListSrc.sort()
            sNew = s_inner.scaleOffsets(scalar, inPlace=False)
            oListPost = [e.offset for e in sNew]
            oListPost.sort()

            # environLocal.printDebug(['scaleOffsets', oListSrc,
            #  '\n' + 'post scaled by:', scalar, oListPost])
            self.assertEqual(oListPost[:len(match)], match)

        # test equally spaced half notes starting at zero
        n = note.Note()
        n.quarterLength = 2
        s = Stream()
        s.repeatAppend(n, 10)

        # provide start of resulting values
        # half not spacing becomes whole note spacing
        procCompare(s, 2, [0.0, 4.0, 8.0])
        procCompare(s, 4, [0.0, 8.0, 16.0, 24.0])
        procCompare(s, 3, [0.0, 6.0, 12.0, 18.0])
        procCompare(s, 0.5, [0.0, 1.0, 2.0, 3.0])
        procCompare(s, 0.25, [0.0, 0.5, 1.0, 1.5])

        # test equally spaced quarter notes start at non-zero
        n = note.Note()
        n.quarterLength = 1
        s = Stream()
        s.repeatInsert(n, list(range(100, 110)))

        procCompare(s, 1, [100, 101, 102, 103])
        procCompare(s, 2, [100, 102, 104, 106])
        procCompare(s, 4, [100, 104, 108, 112])
        procCompare(s, 1.5, [100, 101.5, 103.0, 104.5])
        procCompare(s, 0.5, [100, 100.5, 101.0, 101.5])
        procCompare(s, 0.25, [100, 100.25, 100.5, 100.75])

        # test non equally spaced notes starting at zero
        s = Stream()
        n1 = note.Note()
        n1.quarterLength = 1
        s.repeatInsert(n, list(range(0, 30, 3)))
        n2 = note.Note()
        n2.quarterLength = 2
        s.repeatInsert(n, list(range(1, 30, 3)))
        # procCompare will  sort offsets; this test non-sorted operation
        procCompare(s, 1, [0.0, 1.0, 3.0, 4.0, 6.0, 7.0])
        procCompare(s, 0.5, [0.0, 0.5, 1.5, 2.0, 3.0, 3.5])
        procCompare(s, 2, [0.0, 2.0, 6.0, 8.0, 12.0, 14.0])

        # test non equally spaced notes starting at non-zero
        s = Stream()
        n1 = note.Note()
        n1.quarterLength = 1
        s.repeatInsert(n, list(range(100, 130, 3)))
        n2 = note.Note()
        n2.quarterLength = 2
        s.repeatInsert(n, list(range(101, 130, 3)))
        # procCompare will  sort offsets; this test non-sorted operation
        procCompare(s, 1, [100.0, 101.0, 103.0, 104.0, 106.0, 107.0])
        procCompare(s, 0.5, [100.0, 100.5, 101.5, 102.0, 103.0, 103.5])
        procCompare(s, 2, [100.0, 102.0, 106.0, 108.0, 112.0, 114.0])
        procCompare(s, 6, [100.0, 106.0, 118.0, 124.0, 136.0, 142.0])

    def testScaleOffsetsBasicInPlaceA(self):
        def procCompare(scalar, match):
            # test equally spaced half notes starting at zero
            n = note.Note()
            n.quarterLength = 2
            s = Stream()
            s.repeatAppend(n, 10)

            oListSrc = [e.offset for e in s]
            oListSrc.sort()
            s.scaleOffsets(scalar, inPlace=True)
            oListPost = [e.offset for e in s]
            oListPost.sort()
            # environLocal.printDebug(['scaleOffsets', oListSrc,
            #    '\n' + 'post scaled by:', scalar, oListPost])
            self.assertEqual(oListPost[:len(match)], match)

        # provide start of resulting values
        # half not spacing becomes whole note spacing
        procCompare(2, [0.0, 4.0, 8.0])
        procCompare(4, [0.0, 8.0, 16.0, 24.0])
        procCompare(3, [0.0, 6.0, 12.0, 18.0])
        procCompare(0.5, [0.0, 1.0, 2.0, 3.0])
        procCompare(0.25, [0.0, 0.5, 1.0, 1.5])

    def testScaleOffsetsBasicInPlaceB(self):
        def procCompare(scalar, match):
            # test equally spaced quarter notes start at non-zero
            n = note.Note()
            n.quarterLength = 1
            s = Stream()
            s.repeatInsert(n, list(range(100, 110)))

            oListSrc = [e.offset for e in s]
            oListSrc.sort()
            s.scaleOffsets(scalar, inPlace=True)
            oListPost = [e.offset for e in s]
            oListPost.sort()
            # environLocal.printDebug(['scaleOffsets', oListSrc,
            #  '\n' + 'post scaled by:', scalar, oListPost])
            self.assertEqual(oListPost[:len(match)], match)

        procCompare(1, [100, 101, 102, 103])
        procCompare(2, [100, 102, 104, 106])
        procCompare(4, [100, 104, 108, 112])
        procCompare(1.5, [100, 101.5, 103.0, 104.5])
        procCompare(0.5, [100, 100.5, 101.0, 101.5])
        procCompare(0.25, [100, 100.25, 100.5, 100.75])

    def testScaleOffsetsBasicInPlaceC(self):
        def procCompare(scalar, match):
            # test non equally spaced notes starting at zero
            s = Stream()
            n1 = note.Note()
            n1.quarterLength = 1
            s.repeatInsert(n1, list(range(0, 30, 3)))
            n2 = note.Note()
            n2.quarterLength = 2
            s.repeatInsert(n2, list(range(1, 30, 3)))

            oListSrc = [e.offset for e in s]
            oListSrc.sort()
            s.scaleOffsets(scalar, inPlace=True)
            oListPost = [e.offset for e in s]
            oListPost.sort()
            # environLocal.printDebug(['scaleOffsets', oListSrc,
            #  '\n' + 'post scaled by:', scalar, oListPost])
            self.assertEqual(oListPost[:len(match)], match)

        # procCompare will sort offsets; this test non-sorted operation
        procCompare(1, [0.0, 1.0, 3.0, 4.0, 6.0, 7.0])
        procCompare(0.5, [0.0, 0.5, 1.5, 2.0, 3.0, 3.5])
        procCompare(2, [0.0, 2.0, 6.0, 8.0, 12.0, 14.0])

    def testScaleOffsetsBasicInPlaceD(self):
        def procCompare(scalar, match):
            # test non equally spaced notes starting at non-zero
            s = Stream()
            n1 = note.Note()
            n1.quarterLength = 1
            s.repeatInsert(n1, list(range(100, 130, 3)))
            n2 = note.Note()
            n2.quarterLength = 2
            s.repeatInsert(n2, list(range(101, 130, 3)))

            oListSrc = [e.offset for e in s]
            oListSrc.sort()
            s.scaleOffsets(scalar, inPlace=True)
            oListPost = [e.offset for e in s]
            oListPost.sort()
            # environLocal.printDebug(['scaleOffsets', oListSrc,
            # '\n' + 'post scaled by:', scalar, oListPost])
            self.assertEqual(oListPost[:len(match)], match)

        # procCompare will sort offsets; this test non-sorted operation
        procCompare(1, [100.0, 101.0, 103.0, 104.0, 106.0, 107.0])
        procCompare(0.5, [100.0, 100.5, 101.5, 102.0, 103.0, 103.5])
        procCompare(2, [100.0, 102.0, 106.0, 108.0, 112.0, 114.0])
        procCompare(6, [100.0, 106.0, 118.0, 124.0, 136.0, 142.0])

    def testScaleOffsetsNested(self):
        def scaleOffsetMap(s):  # lists of offsets, with lists of lists
            post = []
            for e in s:
                sub = []
                sub.append(e.offset)
                # if hasattr(e, 'elements'):
                if e.isStream:
                    sub.append(scaleOffsetMap(e))
                post.append(sub)
            return post

        def procCompare(s, scalar, anchorZeroRecurse, match):
            oListSrc = scaleOffsetMap(s)
            oListSrc.sort()
            sNew = s.scaleOffsets(scalar,
                                  anchorZeroRecurse=anchorZeroRecurse,
                                  inPlace=False)
            oListPost = scaleOffsetMap(sNew)
            oListPost.sort()

            # environLocal.printDebug(['scaleOffsets', oListSrc,
            #                          '\n' + 'post scaled by:', scalar, oListPost])
            self.assertEqual(oListPost[:len(match)], match)

        # test equally spaced half notes starting at zero
        n1 = note.Note()
        n1.quarterLength = 2
        s1 = Stream()
        s1.repeatAppend(n1, 4)

        n2 = note.Note()
        n2.quarterLength = 0.5
        s2 = Stream()
        s2.repeatAppend(n2, 4)
        s1.append(s2)

        # offset map gives us a nested list presentation of all offsets
        # useful for testing
        self.assertEqual(scaleOffsetMap(s1),
                         [[0.0], [2.0], [4.0], [6.0],
                          [8.0, [[0.0], [0.5], [1.0], [1.5]]]])

        # provide start of resulting values
        # half not spacing becomes whole note spacing
        procCompare(s1, 2, 'lowest',
                    [[0.0], [4.0], [8.0], [12.0],
                     [16.0, [[0.0], [1.0], [2.0], [3.0]]]])
        procCompare(s1, 4, 'lowest',
                    [[0.0], [8.0], [16.0], [24.0],
                     [32.0, [[0.0], [2.0], [4.0], [6.0]]]])
        procCompare(s1, 0.25, 'lowest',
                    [[0.0], [0.5], [1.0], [1.5],
                     [2.0, [[0.0], [0.125], [0.25], [0.375]]]])

        # test unequally spaced notes starting at non-zero
        n1 = note.Note()
        n1.quarterLength = 1
        s1 = Stream()
        s1.repeatInsert(n1, [10, 14, 15, 17])

        n2 = note.Note()
        n2.quarterLength = 9.5
        s2 = Stream()
        s2.repeatInsert(n2, [40, 40.5, 41, 41.5])
        self.assertEqual(s2.highestTime, 51)
        s1.append(s2)
        self.assertEqual(s1.highestTime, 17 + 1 + 51)
        s1.append(copy.deepcopy(s2))
        s1.append(copy.deepcopy(s2))

        # note that, with these nested streams,
        # the first value of an embedded stream stays in the same
        # position relative to that stream.

        # it might be necessary, in this case, to scale the start
        # time of the first element
        # that is, it should have no shift

        # provide anchorZeroRecurse value
        self.assertEqual(scaleOffsetMap(s1),
                         [[10.0], [14.0], [15.0], [17.0],
                          [18.0, [[40.0], [40.5], [41.0], [41.5]]],
                          [69.0, [[40.0], [40.5], [41.0], [41.5]]],
                          [120.0, [[40.0], [40.5], [41.0], [41.5]]]]
                         )

        procCompare(s1, 2, 'lowest',
                    [[10.0], [18.0], [20.0], [24.0],
                     [26.0, [[40.0], [41.0], [42.0], [43.0]]],
                     [128.0, [[40.0], [41.0], [42.0], [43.0]]],
                     [230.0, [[40.0], [41.0], [42.0], [43.0]]]]
                    )

        # if anchorZeroRecurse is None, embedded stream that do not
        # start at zero are scaled proportionally
        procCompare(s1, 2, None,
                    [[10.0], [18.0], [20.0], [24.0],
                     [26.0, [[80.0], [81.0], [82.0], [83.0]]],
                     [128.0, [[80.0], [81.0], [82.0], [83.0]]],
                     [230.0, [[80.0], [81.0], [82.0], [83.0]]]]
                    )

        procCompare(s1, 0.25, 'lowest',
                    [[10.0], [11.0], [11.25], [11.75],
                     [12.0, [[40.0], [40.125], [40.25], [40.375]]],
                     [24.75, [[40.0], [40.125], [40.25], [40.375]]],
                     [37.5, [[40.0], [40.125], [40.25], [40.375]]]]
                    )

        # if anchorZeroRecurse is None, embedded stream that do not
        # start at zero are scaled proportionally
        procCompare(s1, 0.25, None,
                    [[10.0], [11.0], [11.25], [11.75],
                     [12.0, [[10.0], [10.125], [10.25], [10.375]]],
                     [24.75, [[10.0], [10.125], [10.25], [10.375]]],
                     [37.5, [[10.0], [10.125], [10.25], [10.375]]]]
                    )

    def testScaleDurationsBasic(self):
        '''
        Scale some durations, independent of offsets.
        '''

        def procCompare(s, scalar, match):
            sNew_inner = s.scaleDurations(scalar, inPlace=False)
            oListPost = [e.quarterLength for e in sNew_inner]
            self.assertEqual(oListPost[:len(match)], match)

        n1 = note.Note()
        n1.quarterLength = 0.5
        s1 = Stream()
        s1.repeatInsert(n1, list(range(6)))

        # test inPlace v/ not inPlace
        sNew = s1.scaleDurations(2, inPlace=False)
        self.assertEqual([e.duration.quarterLength for e in s1], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        self.assertEqual([e.duration.quarterLength for e in sNew], [1.0, 1.0, 1.0, 1.0, 1.0, 1.0])

        # basic test
        procCompare(s1, 0.5, [0.25, 0.25, 0.25])
        procCompare(s1, 3, [1.5, 1.5, 1.5])

        # a sequence of Durations of different values
        s1 = Stream()
        for ql in [0.5, 1.5, 2, 3, 0.25, 0.25, 0.5]:
            n = note.Note('g')
            n.quarterLength = ql
            s1.append(n)

        procCompare(s1, 0.5, [0.25, 0.75, 1.0, 1.5, 0.125, 0.125, 0.25])
        procCompare(s1, 0.25, [0.125, 0.375, 0.5, 0.75, 0.0625, 0.0625, 0.125])
        procCompare(s1, 4, [2.0, 6.0, 8, 12, 1.0, 1.0, 2.0])

    def testAugmentOrDiminishBasic(self):

        def procCompare(s, scalar, matchOffset, matchDuration):
            # oListSrc = [e.offset for e in s]
            # qListSrc = [e.quarterLength for e in s]

            sNew = s.augmentOrDiminish(scalar, inPlace=False)
            oListPost = [e.offset for e in sNew]
            qlListPost = [e.quarterLength for e in sNew]

            self.assertEqual(oListPost[:len(matchOffset)], matchOffset)
            self.assertEqual(qlListPost[:len(matchDuration)], matchDuration)

            # test that the last offset is the highest offset
            self.assertEqual(matchOffset[-1], sNew.highestOffset)
            self.assertEqual(matchOffset[-1] + matchDuration[-1],
                             sNew.highestTime)

            # test making measures on this
            unused_post = sNew.makeMeasures()
            # sNew.show()

        # a sequence of Durations of different values
        s1 = Stream()
        for ql in [0.5, 1.5, 2, 3, 0.25, 0.25, 0.5]:
            n = note.Note('g')
            n.quarterLength = ql
            s1.append(n)

        # provide offsets, then durations
        procCompare(s1, 0.5,
                    [0.0, 0.25, 1.0, 2.0, 3.5, 3.625, 3.75],
                    [0.25, 0.75, 1.0, 1.5, 0.125, 0.125, 0.25])

        procCompare(s1, 1.5,
                    [0.0, 0.75, 3.0, 6.0, 10.5, 10.875, 11.25],
                    [0.75, 2.25, 3.0, 4.5, 0.375, 0.375, 0.75])

        procCompare(s1, 3,
                    [0.0, 1.5, 6.0, 12.0, 21.0, 21.75, 22.5],
                    [1.5, 4.5, 6, 9, 0.75, 0.75, 1.5])

    def testAugmentOrDiminishHighestTimes(self):
        '''
        Need to make sure that highest offset and time are properly updated
        '''
        src = corpus.parse('bach/bwv324.xml')
        # get some measures of the soprano; just get the notes
        found = src.parts.first().flatten().notesAndRests[0:30]
        ex = Part(found)

        self.assertEqual(ex.highestOffset, 38.0)
        self.assertEqual(ex.highestTime, 42.0)

        # try first when doing this not in place
        newEx = ex.augmentOrDiminish(2, inPlace=False)
        self.assertEqual(newEx.notesAndRests[0].offset, 0.0)
        self.assertEqual(newEx.notesAndRests[1].offset, 4.0)

        self.assertEqual(newEx.highestOffset, 76.0)
        self.assertEqual(newEx.highestTime, 84.0)

        # try in place
        ex.augmentOrDiminish(2, inPlace=True)
        self.assertEqual(ex.notesAndRests[1].getOffsetBySite(ex), 4.0)
        self.assertEqual(ex.notesAndRests[1].offset, 4.0)

        self.assertEqual(ex.highestOffset, 76.0)
        self.assertEqual(ex.highestTime, 84.0)

    def testAugmentOrDiminishCorpus(self):
        '''
        Extract phrases from the corpus and use for testing
        '''
        # first method: iterating through notes
        src = corpus.parse('bach/bwv324.xml')
        # get some measures of the soprano; just get the notes
        # environLocal.printDebug(['testAugmentOrDiminishCorpus()', 'extracting notes:'])
        found = src.parts.first().flatten().notesAndRests[0:30]
        ex = Part(found)
        # attach a couple of transformations
        s = Score()
        for scalar in [0.5, 1.5, 2, 0.25]:
            # n= note.Note()
            part = Part()
            # environLocal.printDebug(['testAugmentOrDiminishCorpus()',
            #                          'pre augment or diminish', 'ex', ex, 'id(ex)', id(ex)])
            for n in ex.augmentOrDiminish(scalar, inPlace=False):
                part.append(n)
            s.insert(0, part)

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(s).decode('utf-8')

        # second method: getting flattened stream
        src = corpus.parse('bach/bwv323.xml')
        # get notes from one part
        ex = src.parts[0].flatten().notesAndRests.stream()
        s = Score()
        for scalar in [1, 2, 0.5, 1.5]:
            part = ex.augmentOrDiminish(scalar, inPlace=False)
            s.insert(0, part)

        unused_mx = GEX.parse(s).decode('utf-8')
        # s.show()

    def testMeasureBarDurationProportion(self):
        from fractions import Fraction
        m = Measure()
        m.timeSignature = meter.TimeSignature('3/4')
        n = note.Note('B--2')
        n.quarterLength = 1
        m.append(copy.deepcopy(n))

        self.assertEqual(m.notes[0].offset, 0)
        self.assertEqual(m.barDurationProportion(), Fraction(1, 3), 4)
        self.assertEqual(m.barDuration.quarterLength, 3, 4)

        # temporarily commented out
        # m.shiftElementsAsAnacrusis()
        # self.assertTrue(m in m.notesAndRests[0].sites)
        # self.assertEqual(m.notesAndRests[0].offset, 2.0)
        # # now the duration is full
        # self.assertAlmostEqual(m.barDurationProportion(), 1.0, 4)
        # self.assertAlmostEqual(m.highestOffset, 2.0, 4)

        m = Measure()
        m.timeSignature = meter.TimeSignature('5/4')
        n1 = note.Note()
        n1.quarterLength = 0.5
        n2 = note.Note()
        n2.quarterLength = 1.5
        m.append(n1)
        m.append(n2)

        self.assertEqual(m.barDurationProportion(), Fraction(2, 5), 4)
        self.assertEqual(m.barDuration.quarterLength, 5.0)

        # m.shiftElementsAsAnacrusis()
        # self.assertEqual(m.notesAndRests[0].offset, 3.0)
        # self.assertEqual(n1.offset, 3.0)
        # self.assertEqual(n2.offset, 3.5)
        # self.assertAlmostEqual(m.barDurationProportion(), 1.0, 4)

    def testInsertAndShiftBasic(self):
        offsets = [0, 2, 4, 6, 8, 10, 12]
        n = note.Note()
        n.quarterLength = 2
        s = Stream()
        s.repeatInsert(n, offsets)
        # qL, insertOffset, newHighOffset, newHighTime
        data = [
            (0.25, 0, 12.25, 14.25),
            (3, 0, 15, 17),
            (6.5, 0, 18.5, 20.5),
            # shifting at a positing where another element starts
            (0.25, 4, 12.25, 14.25),
            (3, 4, 15, 17),
            (6.5, 4, 18.5, 20.5),
            # shift the same duration at different insert points
            (1, 2, 13, 15),
            (2, 2, 14, 16),
            # this is overlapping element at 2 by 1, ending at 4
            # results in no change in new high values
            (1, 3, 12, 14),
            # since duration is here 2, extend new starts to 5
            (2, 3, 13, 15),
            (1, 4, 13, 15),
            (2, 4, 14, 16),
            # here, we do not shift the element at 4, only event at 6
            (2, 4.5, 12.5, 14.5),
            # here, we insert the start of an element and can shift it
            (2.5, 4, 14.5, 16.5),
        ]
        for qL, insertOffset, newHighOffset, newHighTime in data:
            sProc = copy.deepcopy(s)
            self.assertEqual(sProc.highestOffset, 12)
            self.assertEqual(sProc.highestTime, 14)
            nAlter = note.Note()
            nAlter.quarterLength = qL
            sProc.insertAndShift(insertOffset, nAlter)
            self.assertEqual(sProc.highestOffset, newHighOffset)
            self.assertEqual(sProc.highestTime, newHighTime)
            self.assertEqual(len(sProc), len(s) + 1)

            # try the same with scrambled elements
            sProc = copy.deepcopy(s)
            random.shuffle(sProc._elements)
            sProc.coreElementsChanged()

            self.assertEqual(sProc.highestOffset, 12)
            self.assertEqual(sProc.highestTime, 14)
            nAlter = note.Note()
            nAlter.quarterLength = qL
            sProc.insertAndShift(insertOffset, nAlter)
            self.assertEqual(sProc.highestOffset, newHighOffset)
            self.assertEqual(sProc.highestTime, newHighTime)
            self.assertEqual(len(sProc), len(s) + 1)

    def testInsertAndShiftNoDuration(self):
        offsets = [0, 2, 4, 6, 8, 10, 12]
        n = note.Note()
        n.quarterLength = 2
        s = Stream()
        s.repeatInsert(n, offsets)
        # qL, insertOffset, newHighOffset, newHighTime
        data = [
            (0, 12, 14),
            (0, 12, 14),
            (0, 12, 14),
            (4, 12, 14),
            (4, 12, 14),
            (4, 12, 14),
            (2, 12, 14),
            (2, 12, 14),
            (3, 12, 14),
        ]
        for insertOffset, newHighOffset, newHighTime in data:
            sProc = copy.deepcopy(s)
            self.assertEqual(sProc.highestOffset, 12)
            self.assertEqual(sProc.highestTime, 14)

            c = clef.Clef()
            sProc.insertAndShift(insertOffset, c)
            self.assertEqual(sProc.highestOffset, newHighOffset)
            self.assertEqual(sProc.highestTime, newHighTime)
            self.assertEqual(len(sProc), len(s) + 1)

    def testInsertAndShiftMultipleElements(self):
        offsets = [0, 2, 4, 6, 8, 10, 12]
        n = note.Note()
        n.quarterLength = 2
        s = Stream()
        s.repeatInsert(n, offsets)
        # qL, insertOffset, newHighOffset, newHighTime
        data = [
            (0.25, 0, 12.25, 14.25),
            (3, 0, 15, 17),
            (6.5, 0, 18.5, 20.5),
            # shifting at a positing where another element starts
            (0.25, 4, 12.25, 14.25),
            (3, 4, 15, 17),
            (6.5, 4, 18.5, 20.5),
            # shift the same duration at different insert points
            (1, 2, 13, 15),
            (2, 2, 14, 16),
            # this is overlapping element at 2 by 1, ending at 4
            # results in no change in new high values
            (1, 3, 12, 14),
            # since duration is here 2, extend new starts to 5
            (2, 3, 13, 15),
            (1, 4, 13, 15),
            (2, 4, 14, 16),
            # here, we do not shift the element at 4, only event at 6
            (2, 4.5, 12.5, 14.5),
            # here, we insert the start of an element and can shift it
            (2.5, 4, 14.5, 16.5),
        ]
        for qL, insertOffset, newHighOffset, newHighTime in data:
            sProc = copy.deepcopy(s)
            self.assertEqual(sProc.highestOffset, 12)
            self.assertEqual(sProc.highestTime, 14)

            # fill with sixteenth notes
            nAlter = note.Note()
            nAlter.quarterLength = 0.25
            itemList = []
            o = insertOffset
            while o < insertOffset + qL:
                itemList.append(o)
                itemList.append(copy.deepcopy(nAlter))
                o += 0.25
            # environLocal.printDebug(['itemList', itemList])

            sProc.insertAndShift(itemList)
            self.assertEqual(sProc.highestOffset, newHighOffset)
            self.assertEqual(sProc.highestTime, newHighTime)
            self.assertEqual(len(sProc), len(s) + len(itemList) / 2)

    def testMetadataOnStream(self):

        s = Stream()
        n1 = note.Note()
        s.append(n1)

        s.metadata = metadata.Metadata()
        s.metadata.composer = 'Frank the Composer'
        s.metadata.title = 'work title'  # will get as movement name if not set
        # s.metadata.movementName = 'movement name'
        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(s).decode('utf-8')
        # s.show()

    def testMeasureBarline(self):
        m1 = Measure()
        m1.timeSignature = meter.TimeSignature('3/4')
        self.assertEqual(len(m1), 1)

        b1 = bar.Barline('heavy')
        # this adds to elements list
        m1.leftBarline = b1
        self.assertEqual(len(m1), 2)
        self.assertEqual(m1[0], b1)  # this is on elements
        self.assertEqual(m1.rightBarline, None)  # this is on elements

        b2 = bar.Barline('heavy')
        self.assertEqual(m1.barDuration.quarterLength, 3.0)
        m1.rightBarline = b2

        # now have barline, ts, and barline
        self.assertEqual(len(m1), 3)
        b3 = bar.Barline('double')
        b4 = bar.Barline('heavy')

        m1.leftBarline = b3
        # length should be the same, as we replaced
        self.assertEqual(len(m1), 3)
        self.assertEqual(m1.leftBarline, b3)

        m1.rightBarline = b4
        self.assertEqual(len(m1), 3)
        self.assertEqual(m1.rightBarline, b4)

        p = Part()
        p.append(copy.deepcopy(m1))
        p.append(copy.deepcopy(m1))

        # p.show()

        # add right barline first, w/o a time signature
        m2 = Measure()
        self.assertEqual(len(m2), 0)
        m2.rightBarline = b4
        self.assertEqual(len(m2), 1)
        self.assertEqual(m2.leftBarline, None)  # this is on elements
        self.assertEqual(m2.rightBarline, b4)  # this is on elements

    def testMeasureLayout(self):
        '''
        test both system layout and measure width
        '''

        # Note: Measure.layoutWidth is not currently read by musicxml
        s = Stream()
        for i in range(1, 10):
            n = note.Note()
            m = Measure()
            m.append(n)
            m.layoutWidth = i * 100
            if i % 2 == 0:
                sl = layout.SystemLayout(isNew=True)
                m.insert(0, sl)
            s.append(m)

        # s.show()
        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(s).decode('utf-8')

    def testYieldContainers(self):
        n1 = note.Note()
        n1.id = 'n(1a)'
        n2 = note.Note()
        n2.id = 'n2(2b)'
        n3 = note.Note()
        n3.id = 'n3(3b)'
        n4 = note.Note()
        n4.id = 'n4(3b)'

        s1 = Stream()
        s1.id = '1a'
        s1.append(n1)

        s2 = Stream()
        s2.id = '2a'
        s3 = Stream()
        s3.id = '2b'
        s3.append(n2)
        s4 = Stream()
        s4.id = '2c'

        s5 = Stream()
        s5.id = '3a'
        s6 = Stream()
        s6.id = '3b'
        s6.append(n3)
        s6.append(n4)
        s7 = Stream()
        s7.id = '3c'
        s8 = Stream()
        s8.id = '3d'
        s9 = Stream()
        s9.id = '3e'
        s10 = Stream()
        s10.id = '3f'

        # environLocal.printDebug(['s1, s2, s3, s4', s1, s2, s3, s4])

        s2.append(s5)
        s2.append(s6)
        s2.append(s7)

        s3.append(s8)
        s3.append(s9)

        s4.append(s10)

        s1.append(s2)
        s1.append(s3)
        s1.append(s4)

        # environLocal.printDebug(['downward:'])

        match = []
        for x in s1.recurse(streamsOnly=True, includeSelf=True):
            match.append(x.id)
            # environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        self.assertEqual(match, ['1a', '2a', '3a', '3b', '3c', '2b', '3d', '3e', '2c', '3f'])

        # environLocal.printDebug(['downward with elements:'])
        match = []
        for x in s1.recurse(streamsOnly=False, includeSelf=True):
            match.append(x.id)
            # environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        self.assertEqual(match, ['1a', 'n(1a)', '2a', '3a', '3b', 'n3(3b)', 'n4(3b)', '3c',
                                 '2b', 'n2(2b)', '3d', '3e', '2c', '3f'])

        # environLocal.printDebug(['downward from non-topmost element:'])
        match = []
        for x in s2.recurse(streamsOnly=False, includeSelf=True):
            match.append(x.id)
            # environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        # test downward
        self.assertEqual(match, ['2a', '3a', '3b', 'n3(3b)', 'n4(3b)', '3c'])

        # environLocal.printDebug(['upward, with skipDuplicates:'])
        # match = []
        # # must provide empty list for memo
        # for x in s7._yieldReverseUpwardsSearch([], streamsOnly=True, skipDuplicates=True):
        #     match.append(x.id)
        #     # environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        # self.assertEqual(match, ['3c', '2a', '1a', '2b', '2c', '3a', '3b'] )

        # environLocal.printDebug(['upward from a single node, with skipDuplicates'])
        # match = []
        # for x in s10._yieldReverseUpwardsSearch([], streamsOnly=True):
        #     match.append(x.id)
        #     # environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        #
        # self.assertEqual(match, ['3f', '2c', '1a', '2a', '2b'] )

        # environLocal.printDebug(['upward with skipDuplicates=False:'])
        # match = []
        # for x in s10._yieldReverseUpwardsSearch([], streamsOnly=True, skipDuplicates=False):
        #     match.append(x.id)
        #     # environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        # self.assertEqual(match, ['3f', '2c', '1a', '2a', '1a', '2b', '1a'] )

        # environLocal.printDebug(['upward, with skipDuplicates, streamsOnly=False:'])
        # match = []
        # # must provide empty list for memo
        # for x in s8._yieldReverseUpwardsSearch([], streamsOnly=False,
        #     skipDuplicates=True):
        #     match.append(x.id)
        #     environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        # self.assertEqual(match, ['3d', 'n2(2b)', '2b', 'n(1a)', '1a', '2a', '2c', '3e'] )

        # environLocal.printDebug(['upward, with skipDuplicates, streamsOnly=False:'])
        # match = []
        # # must provide empty list for memo
        # for x in s4._yieldReverseUpwardsSearch([], streamsOnly=False,
        #     skipDuplicates=True):
        #     match.append(x.id)
        #     # environLocal.printDebug([x, x.id, 'activeSite', x.activeSite])
        # # notice that this does not get the nonContainers for 2b
        # self.assertEqual(match, ['2c', 'n(1a)', '1a', '2a', '2b'] )

    def testMidiEventsBuilt(self):
        from music21.midi import MetaEvents, ChannelVoiceMessages
        self.maxDiff = None

        def procCompare(mf_inner, match_inner):
            triples = []
            for i in range(0, len(mf_inner.tracks[1].events), 2):
                delta = mf_inner.tracks[1].events[i]  # delta
                e = mf_inner.tracks[1].events[i + 1]  # events
                triples.append((delta.time, e.type, e.pitch))

            self.assertEqual(triples, match_inner)

        s = Stream()
        n = note.Note('g#3')
        n.quarterLength = 0.5
        s.repeatAppend(n, 6)
        # post = s.midiTracks  # a list
        post = midiTranslate.streamHierarchyToMidiTracks(s)

        self.assertEqual(len(post[1].events), 30)
        # must be an even number
        self.assertEqual(len(post[1].events) % 2, 0)

        mf = midiTranslate.streamToMidiFile(s)
        match = [
            (0, MetaEvents.SEQUENCE_TRACK_NAME, None),
            (0, ChannelVoiceMessages.PITCH_BEND, None),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (5040, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (5040, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (5040, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (5040, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (5040, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (5040, ChannelVoiceMessages.NOTE_OFF, 56),
            (10080, MetaEvents.END_OF_TRACK, None),
        ]

        procCompare(mf, match)

        s = Stream()
        n = note.Note('g#3')
        n.quarterLength = 1.5
        s.repeatAppend(n, 3)

        mf = midiTranslate.streamToMidiFile(s)
        match = [
            (0, MetaEvents.SEQUENCE_TRACK_NAME, None),
            (0, ChannelVoiceMessages.PITCH_BEND, None),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (15120, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (15120, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (15120, ChannelVoiceMessages.NOTE_OFF, 56),
            (10080, MetaEvents.END_OF_TRACK, None),
        ]
        procCompare(mf, match)

        # combinations of different pitches and durs
        s = Stream()
        data = [
            ('c2', 0.25),
            ('c#3', 0.5),
            ('g#3', 1.5),
            ('a#2', 1),
            ('a4', 2),
        ]
        for p, d in data:
            n = note.Note(p)
            n.quarterLength = d
            s.append(n)

        mf = midiTranslate.streamToMidiFile(s)
        match = [
            (0, MetaEvents.SEQUENCE_TRACK_NAME, None),
            (0, ChannelVoiceMessages.PITCH_BEND, None),
            (0, ChannelVoiceMessages.NOTE_ON, 36),
            (2520, ChannelVoiceMessages.NOTE_OFF, 36),
            (0, ChannelVoiceMessages.NOTE_ON, 49),
            (5040, ChannelVoiceMessages.NOTE_OFF, 49),
            (0, ChannelVoiceMessages.NOTE_ON, 56),
            (15120, ChannelVoiceMessages.NOTE_OFF, 56),
            (0, ChannelVoiceMessages.NOTE_ON, 46),
            (10080, ChannelVoiceMessages.NOTE_OFF, 46),
            (0, ChannelVoiceMessages.NOTE_ON, 69),
            (20160, ChannelVoiceMessages.NOTE_OFF, 69),
            (10080, MetaEvents.END_OF_TRACK, None),
        ]
        procCompare(mf, match)

        # rests, basic
        # environLocal.printDebug(['rests'])
        s = Stream()
        data = [
            ('c2', 1),
            (None, 0.5),
            ('c#3', 1),
            (None, 0.5),
            ('a#2', 1),
            (None, 0.5),
            ('a4', 1),
        ]
        for p, d in data:
            if p is None:
                n = note.Rest()
            else:
                n = note.Note(p)
            n.quarterLength = d
            s.append(n)
        # s.show('midi')
        mf = midiTranslate.streamToMidiFile(s)
        match = [
            (0, MetaEvents.SEQUENCE_TRACK_NAME, None),
            (0, ChannelVoiceMessages.PITCH_BEND, None),
            (0, ChannelVoiceMessages.NOTE_ON, 36),
            (10080, ChannelVoiceMessages.NOTE_OFF, 36),
            (5040, ChannelVoiceMessages.NOTE_ON, 49),
            (10080, ChannelVoiceMessages.NOTE_OFF, 49),
            (5040, ChannelVoiceMessages.NOTE_ON, 46),
            (10080, ChannelVoiceMessages.NOTE_OFF, 46),
            (5040, ChannelVoiceMessages.NOTE_ON, 69),
            (10080, ChannelVoiceMessages.NOTE_OFF, 69),
            (10080, MetaEvents.END_OF_TRACK, None),
        ]
        procCompare(mf, match)

        # environLocal.printDebug(['rests, varied sizes'])
        s = Stream()
        data = [
            ('c2', 1),
            (None, 0.25),
            ('c#3', 1),
            (None, 1.5),
            ('a#2', 1),
            (None, 2),
            ('a4', 1),
        ]
        for p, d in data:
            if p is None:
                n = note.Rest()
            else:
                n = note.Note(p)
            n.quarterLength = d
            s.append(n)
        # s.show('midi')
        mf = midiTranslate.streamToMidiFile(s)
        match = [
            (0, MetaEvents.SEQUENCE_TRACK_NAME, None),
            (0, ChannelVoiceMessages.PITCH_BEND, None),
            (0, ChannelVoiceMessages.NOTE_ON, 36),
            (10080, ChannelVoiceMessages.NOTE_OFF, 36),
            (2520, ChannelVoiceMessages.NOTE_ON, 49),
            (10080, ChannelVoiceMessages.NOTE_OFF, 49),
            (15120, ChannelVoiceMessages.NOTE_ON, 46),
            (10080, ChannelVoiceMessages.NOTE_OFF, 46),
            (20160, ChannelVoiceMessages.NOTE_ON, 69),
            (10080, ChannelVoiceMessages.NOTE_OFF, 69),
            (10080, MetaEvents.END_OF_TRACK, None),
        ]
        procCompare(mf, match)

        # environLocal.printDebug(['rests, multiple in a row'])
        s = Stream()
        data = [
            ('c2', 1),
            (None, 1),
            (None, 1),
            ('c#3', 1),
            ('c#3', 1),
            (None, 0.5),
            (None, 0.5),
            (None, 0.5),
            (None, 0.5),
            ('a#2', 1),
            (None, 2),
            ('a4', 1),
        ]
        for p, d in data:
            if p is None:
                n = note.Rest()
            else:
                n = note.Note(p)
            n.quarterLength = d
            s.append(n)
        # s.show('midi')
        mf = midiTranslate.streamToMidiFile(s)
        match = [
            (0, MetaEvents.SEQUENCE_TRACK_NAME, None),
            (0, ChannelVoiceMessages.PITCH_BEND, None),
            (0, ChannelVoiceMessages.NOTE_ON, 36),
            (10080, ChannelVoiceMessages.NOTE_OFF, 36),
            (20160, ChannelVoiceMessages.NOTE_ON, 49),
            (10080, ChannelVoiceMessages.NOTE_OFF, 49),
            (0, ChannelVoiceMessages.NOTE_ON, 49),
            (10080, ChannelVoiceMessages.NOTE_OFF, 49),
            (20160, ChannelVoiceMessages.NOTE_ON, 46),
            (10080, ChannelVoiceMessages.NOTE_OFF, 46),
            (20160, ChannelVoiceMessages.NOTE_ON, 69),
            (10080, ChannelVoiceMessages.NOTE_OFF, 69),
            (10080, MetaEvents.END_OF_TRACK, None),
        ]
        procCompare(mf, match)

        # environLocal.printDebug(['w/ chords'])
        s = Stream()
        data = [
            ('c2', 1),
            (None, 1),
            (['f3', 'a-4', 'c5'], 1),
            (None, 0.5),
            ('a#2', 1),
            (None, 2),
            (['d2', 'a4'], 0.5),
            (['d-2', 'a#3', 'g#6'], 0.5),
            (None, 1),
            (['f#3', 'a4', 'c#5'], 4)
        ]
        for p, d in data:
            if p is None:
                n = note.Rest()
            elif isinstance(p, list):
                n = chord.Chord(p)
            else:
                n = note.Note(p)
            n.quarterLength = d
            s.append(n)
        # s.show('midi')
        mf = midiTranslate.streamToMidiFile(s)
        match = [
            (0, MetaEvents.SEQUENCE_TRACK_NAME, None),
            (0, ChannelVoiceMessages.PITCH_BEND, None),
            (0, ChannelVoiceMessages.NOTE_ON, 36),
            (10080, ChannelVoiceMessages.NOTE_OFF, 36),
            (10080, ChannelVoiceMessages.NOTE_ON, 53),
            (0, ChannelVoiceMessages.NOTE_ON, 68),
            (0, ChannelVoiceMessages.NOTE_ON, 72),
            (10080, ChannelVoiceMessages.NOTE_OFF, 53),
            (0, ChannelVoiceMessages.NOTE_OFF, 68),
            (0, ChannelVoiceMessages.NOTE_OFF, 72),
            (5040, ChannelVoiceMessages.NOTE_ON, 46),
            (10080, ChannelVoiceMessages.NOTE_OFF, 46),
            (20160, ChannelVoiceMessages.NOTE_ON, 38),
            (0, ChannelVoiceMessages.NOTE_ON, 69),
            (5040, ChannelVoiceMessages.NOTE_OFF, 38),
            (0, ChannelVoiceMessages.NOTE_OFF, 69),
            (0, ChannelVoiceMessages.NOTE_ON, 37),
            (0, ChannelVoiceMessages.NOTE_ON, 58),
            (0, ChannelVoiceMessages.NOTE_ON, 92),
            (5040, ChannelVoiceMessages.NOTE_OFF, 37),
            (0, ChannelVoiceMessages.NOTE_OFF, 58),
            (0, ChannelVoiceMessages.NOTE_OFF, 92),
            (10080, ChannelVoiceMessages.NOTE_ON, 54),
            (0, ChannelVoiceMessages.NOTE_ON, 69),
            (0, ChannelVoiceMessages.NOTE_ON, 73),
            (40320, ChannelVoiceMessages.NOTE_OFF, 54),
            (0, ChannelVoiceMessages.NOTE_OFF, 69),
            (0, ChannelVoiceMessages.NOTE_OFF, 73),
            (10080, MetaEvents.END_OF_TRACK, None),
        ]
        procCompare(mf, match)

    def testFindGaps(self):
        s = Stream()
        n = note.Note()
        s.repeatInsert(n, [0, 1.5, 2.5, 4, 8])
        post = s.findGaps()
        test = [(e.offset, e.offset + e.duration.quarterLength) for e in post]
        match = [(1.0, 1.5), (3.5, 4.0), (5.0, 8.0)]
        self.assertEqual(test, match)

        self.assertEqual(len(s), 5)
        s.makeRests(inPlace=True, fillGaps=True)
        self.assertEqual(len(s), 8)
        self.assertEqual(len(s.getElementsByClass(note.Rest)), 3)

    def testQuantize(self):

        def procCompare(srcOffset, srcDur, dstOffset, dstDur, divList):
            s = Stream()
            for nOffset, nDuration in zip(srcOffset, srcDur):
                n = note.Note()
                n.quarterLength = nDuration
                s.insert(nOffset, n)
            # Must be sorted for quantizing to work optimally.
            s.sort()

            s.quantize(divList, processOffsets=True, processDurations=True, inPlace=True)

            targetOffset = [e.offset for e in s]
            targetDur = [e.duration.quarterLength for e in s]

            self.assertEqual(targetOffset, dstOffset)
            self.assertEqual(targetDur, dstDur)

            # environLocal.printDebug(['quantization results:', targetOffset, targetDur])
        from fractions import Fraction as F

        procCompare([0.01, 0.24, 0.57, 0.78], [0.25, 0.25, 0.25, 0.25],
                    [0.0, 0.25, 0.5, 0.75], [0.25, 0.25, 0.25, 0.25],
                    [4])  # snap to 0.25

        procCompare([0.01, 0.24, 0.52, 0.78], [0.25, 0.25, 0.25, 0.25],
                    [0.0, 0.25, 0.5, 0.75], [0.25, 0.25, 0.25, 0.25],
                    [8])  # snap to 0.125

        procCompare([0.01, 0.345, 0.597, 1.02, 1.22],
                    [0.31, 0.32, 0.33, 0.25, 0.25],

                    [0.0, F('1/3'), F('2/3'), 1.0, 1.25],
                    [F('1/3'), F('1/3'), F('1/3'), 0.25, 0.25],

                    [4, 3])  # snap to 0.125 and 0.3333

        procCompare([0.01, 0.345, 0.687, 0.99, 1.28],
                    [0.31, 0.32, 0.33, 0.22, 0.21],

                    [0.0, F('1/3'), F('2/3'), 1.0, 1.25],
                    [F('1/3'), F('1/3'), F('1/3'), 0.25, 0.25],

                    [8, 3])  # snap to 0.125 and 0.3333

        procCompare([0.03, 0.335, 0.677, 1.02, 1.28],
                    [0.32, 0.35, 0.33, 0.22, 0.21],

                    [0.0, F('1/3'), F('2/3'), 1.0, 1.25],
                    [F('1/3'), F('1/3'), F('1/3'), 0.25, 0.25],

                    [8, 6])  # snap to 0.125 and 0.1666666

        # User-reported example: contains overlap and tiny gaps
        # Parsing with fewer gaps in v.9, as long as stream is sorted
        # https://github.com/cuthbertLab/music21/issues/1536
        procCompare([2.016, 2.026, 2.333, 2.646, 3.0, 3.323, 3.651],
                    [0.123, 0.656, 0.104, 0.094, 0.146, 0.099, 0.141],

                    [2, 2, F('7/3'), F('8/3'), 3.0, F('10/3'), F('11/3')],
                    [F('1/3'), F('2/3'), F('1/3'), F('1/3'),
                     F('1/3'), F('1/3'), 0.25],

                    [4, 3])

    def testQuantizeMinimumDuration(self):
        '''
        Notes (not rests!) of nonzero duration should retain a nonzero
        duration after quantizing. Zero duration rests should be removed.
        '''
        dirLib = common.getSourceFilePath() / 'midi' / 'testPrimitive'
        fp = dirLib / 'test15.mid'  # 3 16ths, 2 32nds
        s = converter.parse(fp, quarterLengthDivisors=[2])
        last_note = s.flatten().notes[-1]
        self.assertEqual(last_note.duration.quarterLength, 0.5)
        self.assertEqual(last_note.editorial.quarterLengthQuantizationError, .125 - .5)

        # build up the same score from scratch and show
        # minimum duration constraint does not apply to rests
        s2 = Stream()
        s2.repeatAppend(note.Note(type='16th'), 3)
        s2.repeatAppend(note.Rest(type='32nd'), 2)
        s2.quantize(inPlace=True, quarterLengthDivisors=[2])
        self.assertEqual(len(s2.notesAndRests), 3)

    def testAnalyze(self):

        s = corpus.parse('bach/bwv66.6')

        sub = [s.parts[0], s.parts[1], s.measures(4, 5),
                s.parts[2].measures(4, 5)]

        matchAmbitus = [interval.Interval(12),
                        interval.Interval(15),
                        interval.Interval(26),
                        interval.Interval(10)]

        # match values for different analysis strings
        for idStr in ['range', 'ambitus', 'span']:
            for sTest, matchAmbitusTest in zip(sub, matchAmbitus):
                post = sTest.analyze(idStr)
                self.assertEqual(str(post), str(matchAmbitusTest))

        # only match first two values
        matchKrumhansl = [(pitch.Pitch('F#'), 'minor'),
                          (pitch.Pitch('C#'), 'minor'),
                          (pitch.Pitch('E'), 'major'),
                          (pitch.Pitch('E'), 'major')]

        # match values under different strings provided to analyze
        for idStr in ['KrumhanslSchmuckler', 'krumhansl']:
            for sTest, sMatch in zip(sub, matchKrumhansl):
                post = sTest.analyze(idStr)
                # returns three values; match 2
                self.assertEqual(post.tonic.name, sMatch[0].name)
                self.assertEqual(post.mode, sMatch[1])

        matchArden = [(pitch.Pitch('F#'), 'minor'),
                      (pitch.Pitch('C#'), 'minor'),
                      (pitch.Pitch('F#'), 'minor'),
                      (pitch.Pitch('E'), 'major')]
        for idStr in ['arden']:
            for sTest, sMatch in zip(sub, matchArden):
                post = sTest.analyze(idStr)
                # returns three values; match 2
                self.assertEqual(post.tonic.name, sMatch[0].name)
                self.assertEqual(post.mode, sMatch[1])

    def testMakeTupletBracketsA(self):
        '''
        Creating brackets
        '''
        from music21.stream import makeNotation

        def collectType(ss):
            post = []
            for e in ss:
                if e.duration.tuplets:
                    post.append(e.duration.tuplets[0].type)
                else:
                    post.append(None)
            return post

        def collectBracket(ss):
            post = []
            for e in ss:
                if e.duration.tuplets:
                    post.append(e.duration.tuplets[0].bracket)
                else:
                    post.append(None)
            return post

        # case of incomplete, single tuplet ending the Stream
        # remove bracket
        s = Stream()
        qlList = [1, 2, 0.5, 1 / 6]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        self.assertEqual(collectType(s), [None, None, None, 'startStop'])
        self.assertEqual(collectBracket(s), [None, None, None, False])
        # s.show()

    def testMakeTupletBracketsB(self):
        '''
        Creating brackets
        '''
        from music21.stream import makeNotation

        def collectType(ss):
            post = []
            for e in ss:
                if e.duration.tuplets:
                    post.append(e.duration.tuplets[0].type)
                else:
                    post.append(None)
            return post

        def collectBracket(ss):
            post = []
            for e in ss:
                if e.duration.tuplets:
                    post.append(e.duration.tuplets[0].bracket)
                else:
                    post.append(None)
            return post

        s = Stream()
        qlList = [1, 1 / 3, 1 / 3, 1 / 3, 1, 1]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        self.assertEqual(collectType(s), [None, 'start', None, 'stop', None, None])
        # s.show()

        s = Stream()
        qlList = [1, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1, 1]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        # this is the correct type settings but this displays by dividing
        # into two brackets
        self.assertEqual(collectType(s),
                         [None, 'start', None, 'stop', 'start', None, 'stop', None, None])
        # s.show()

        # case of tuplet ending the Stream
        s = Stream()
        qlList = [1, 2, 0.5, 1 / 6, 1 / 6, 1 / 6, ]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        self.assertEqual(collectType(s), [None, None, None, 'start', None, 'stop'])
        # s.show()

        # case of incomplete, single tuplets in the middle of a Stream
        s = Stream()
        qlList = [1, 1 / 3, 1, 1 / 3, 1, 1 / 3]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        self.assertEqual(collectType(s),
                         [None, 'startStop', None, 'startStop', None, 'startStop'])
        self.assertEqual(collectBracket(s), [None, False, None, False, None, False])
        # s.show()

        # diverse groups that sum to a whole
        s = Stream()
        qlList = [1, 1 / 3, 2 / 3, 2 / 3, 1 / 6, 1 / 6, 1]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        self.assertEqual(collectType(s), [None, 'start', 'stop', 'start', None, 'stop', None])
        # s.show()

        # diverse groups that sum to a whole
        s = Stream()
        qlList = [1, 1 / 3, 2 / 3, 1, 1 / 6, 1 / 3, 1 / 3, 1 / 6]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        self.assertEqual(collectType(s),
                         [None, 'start', 'stop', None, 'start', 'stop', 'start', 'stop'])
        self.assertEqual(collectBracket(s),
                         [None, True, True, None, True, True, True, True])
        # s.show()

        # quintuplets
        s = Stream()
        qlList = [1, 1 / 5, 1 / 5, 1 / 10, 1 / 10, 1 / 5, 1 / 5, 2.]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        makeNotation.makeTupletBrackets(s, inPlace=True)
        self.assertEqual(collectType(s), [None, 'start', None, None, None, None, 'stop', None])
        self.assertEqual(collectBracket(s), [None, True, True, True, True, True, True, None])
        # s.show()

    def testMakeNotationA(self):
        '''
        This is a test of many make procedures
        '''
        def collectTupletType(s_inner):
            post = []
            for e in s_inner:
                if e.duration.tuplets:
                    post.append(e.duration.tuplets[0].type)
                else:
                    post.append(None)
            return post

        def collectTupletBracket(s_inner):
            post = []
            for e in s_inner:
                if e.duration.tuplets:
                    post.append(e.duration.tuplets[0].bracket)
                else:
                    post.append(None)
            return post

        # s = Stream()
        # qlList = [1, 1/3, 1/3, 1/3, 1, 1, 1/3, 1/3, 1/3, 1, 1]
        # for ql in qlList:
        #     n = note.Note()
        #     n.quarterLength = ql
        #     s.append(n)
        # postMake = s.makeNotation()
        # self.assertEqual(collectTupletType(postMake.flatten().notesAndRests),
        #                    [None, 'start', None, 'stop', None, None, 'start',
        #                     None, 'stop', None, None])
        # # s.show()

        s = Stream()
        qlList = [1 / 3, ]
        for ql in qlList:
            n = note.Note()
            n.quarterLength = ql
            s.append(n)
        postMake = s.makeNotation()
        self.assertEqual(collectTupletType(postMake.flatten().notes), ['startStop'])
        self.assertEqual(collectTupletBracket(postMake.flatten().notes), [False])

        # s.show()

    def testMakeNotationB(self):
        '''
        Testing voices making routines within make notation
        '''
        from music21.instrument import Xylophone
        s = Stream()
        s.insert(0, Xylophone())
        s.insert(0, note.Note('C4', quarterLength=8))
        s.repeatInsert(note.Note('b-4', quarterLength=0.5), [x * 0.5 for x in range(16)])
        s.repeatInsert(note.Note('f#5', quarterLength=2), [0, 2, 4, 6])

        sPost = s.makeNotation()
        # sPost.show()
        # make sure original is not changed
        self.assertEqual(len(s.voices), 0)
        self.assertEqual(len(s.notes), 21)
        # we have generated measures, beams, and voices
        self.assertEqual(len(sPost.getElementsByClass(Measure)), 2)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[0].voices), 3)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[1].voices), 3)
        # check beaming
        for m in sPost.getElementsByClass(Measure):
            for n in m.voices[1].notes:  # middle voice has beams
                self.assertGreater(len(n.beams), 0)

        # check instruments
        self.assertIsInstance(sPost.getInstruments(recurse=True)[0], Xylophone)

    def testMakeNotationC(self):
        '''
        Test creating diverse, overlapping durations and notes
        '''
        s = Stream()
        for dur in [0.5, 1.5, 3]:
            for offset in [0, 1.5, 4, 6]:
                # create a midi pitch value from duration
                s.insert(offset, note.Note(50 + (dur * 2) + (offset * 2),
                                           quarterLength=dur))
        # s.show()
        sPost = s.makeNotation()
        self.assertEqual(len(sPost.getElementsByClass(Measure)), 3)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[0].voices), 4)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[1].voices), 4)

        self.assertIsNotNone(sPost.flatten().notes[-1].tie)

    def testMakeNotationScoreA(self):
        '''
        Test makeNotation on Score objects
        '''
        s = Score()
        p1 = Stream()
        p2 = Stream()
        for p in [p1, p2]:
            p.repeatAppend(note.Note(), 12)
            s.insert(0, p)
        # this is true as the sub-stream contain notes
        self.assertTrue(s.hasPartLikeStreams())

        self.assertFalse(s.getElementsByClass(Stream)[0].hasMeasures())
        self.assertFalse(s.getElementsByClass(Stream)[1].hasMeasures())

        post = s.makeNotation(inPlace=False)
        self.assertTrue(post.hasPartLikeStreams())

        # three measures are made by default
        self.assertEqual(len(post.getElementsByClass(Stream).first().getElementsByClass(Measure)),
                         3)
        self.assertEqual(len(post.getElementsByClass(Stream)[1].getElementsByClass(Measure)),
                         3)
        self.assertEqual(len(post.flatten().getElementsByClass(meter.TimeSignature)), 2)
        self.assertEqual(len(post.flatten().getElementsByClass(clef.Clef)), 2)

    def testMakeNotationScoreB(self):
        '''
        Test makeNotation on Score objects
        '''
        s = Score()
        p1 = Stream()
        p2 = Stream()
        for p in [p1, p2]:
            p.repeatAppend(note.Note(), 12)
            s.insert(0, p)
        # this is true as the sub-stream contain notes
        self.assertTrue(s.hasPartLikeStreams())

        self.assertFalse(s.getElementsByClass(Stream)[0].hasMeasures())
        self.assertFalse(s.getElementsByClass(Stream)[1].hasMeasures())

        # supply a meter stream
        post = s.makeNotation(inPlace=False, meterStream=Stream(
            [meter.TimeSignature('3/4')]))

        self.assertTrue(post.hasPartLikeStreams())

        # four measures are made due to passed-in time signature
        self.assertEqual(len(post.getElementsByClass(Stream)[0].getElementsByClass(Measure)), 4)
        self.assertEqual(len(post.getElementsByClass(Stream)[1].getElementsByClass(Measure)), 4)

        self.assertEqual(len(post.flatten().getElementsByClass(meter.TimeSignature)), 2)
        self.assertEqual(len(post.flatten().getElementsByClass(clef.Clef)), 2)

    def testMakeNotationScoreC(self):
        '''
        Test makeNotation on Score objects
        '''
        s = Score()
        p1 = Stream()
        p2 = Stream()
        for p in [p1, p2]:
            p.repeatAppend(note.Note(), 12)
            s.insert(0, p)

        # create measures in the first part
        s.getElementsByClass(Stream).first().makeNotation(
            inPlace=True,
            meterStream=Stream([meter.TimeSignature('3/4')]))

        self.assertTrue(s.getElementsByClass(Stream)[0].hasMeasures())
        self.assertFalse(s.getElementsByClass(Stream)[1].hasMeasures())

        post = s.makeNotation(inPlace=False)

        self.assertEqual(len(post.getElementsByClass(
            Stream)[0].getElementsByClass(Measure)), 4)
        self.assertEqual(len(post.getElementsByClass(
            Stream)[1].getElementsByClass(Measure)), 3)

        self.assertEqual(len(post.flatten().getElementsByClass(meter.TimeSignature)), 2)
        self.assertEqual(len(post.flatten().getElementsByClass(clef.Clef)), 2)

    def testMakeNotationKeySignatureOneVoice(self):
        '''
        The base-case: Stream should keep it's key.KeySignature element when a
        single-voice score is prepared for notation.
        '''
        sharpsInKey = 2
        c = clef.TrebleClef()
        ts = meter.TimeSignature('4/4')
        ks = key.KeySignature(sharpsInKey)
        s = Stream()
        s.insert(0.0, c)
        s.insert(0.0, ts)
        s.insert(0.0, ks)
        s.insert(0.0, note.Note('C'))
        s.insert(2.0, note.Note('G'))

        sPost = s.makeNotation()

        self.assertEqual(len(sPost.getElementsByClass(Measure)), 1)
        m1 = sPost.getElementsByClass(Measure).first()
        self.assertEqual(m1.keySignature.sharps, sharpsInKey)

    def testMakeNotationKeySignatureMultiVoice(self):
        '''
        Stream should keep its key.KeySignature element
        when a multi-voice score is prepared for notation.
        '''

        sharpsInKey = 2
        c = clef.TrebleClef()
        ts = meter.TimeSignature('4/4')
        ks = key.KeySignature(2)
        s = Stream()
        s.insert(0.0, c)
        s.insert(0.0, ts)
        s.insert(0.0, ks)

        # two notes at the same time create multi-voice
        s.insert(2.0, note.Note('C'))
        s.insert(2.0, note.Note('G'))

        sPost = s.makeNotation()

        self.assertEqual(len(sPost.getElementsByClass(Measure)), 1)
        m1 = sPost.getElementsByClass(Measure).first()
        assert m1.keySignature is not None
        self.assertEqual(m1.keySignature.sharps, sharpsInKey)

    def testMakeTies(self):
        def collectAccidentalDisplayStatus(s_inner):
            post = []
            for e in s_inner.flatten().notesAndRests:
                if e.pitch.accidental is not None:
                    post.append((e.pitch.name, e.pitch.accidental.displayStatus))
                else:  # mark as not having an accidental
                    post.append('x')
            return post

        s = corpus.parse('bach/bwv66.6')
        # this has accidentals in measures 2 and 6
        sSub = s.parts[3].measures(2, 6)
        # sSub.show()
        # only notes that deviate from key signature are True
        self.assertEqual(collectAccidentalDisplayStatus(sSub),
                         ['x', ('C#', False), 'x', 'x', ('E#', True), ('F#', False), 'x',
                          ('C#', False), ('F#', False), ('F#', False), ('G#', False),
                          ('F#', False), ('G#', False), 'x', 'x', 'x', ('C#', False),
                          ('F#', False), ('G#', False), 'x', 'x', 'x', 'x',
                          ('E#', True), ('F#', False)])

        # this removes key signature
        sSub = sSub.flatten().notesAndRests.stream()
        self.assertEqual(len(sSub), 25)

        sSub.insert(0, meter.TimeSignature('3/8'))
        sSub.augmentOrDiminish(2, inPlace=True)

        # explicitly call make measures and make ties
        mStream = sSub.makeMeasures(finalBarline=None)
        mStream.makeTies(inPlace=True)

        self.assertEqual(len(mStream.flatten()), 45)

        # mStream.show()

        # this as expected: the only True accidental display status is those
        # that were in the original. in Finale display, however, sharps are
        # displayed when they should not be.
        self.assertEqual(collectAccidentalDisplayStatus(mStream),
                         ['x', ('C#', False), ('C#', False), 'x', 'x', 'x', 'x',
                          ('E#', True), ('E#', False), ('F#', False), 'x',
                          ('C#', False), ('C#', False), ('F#', False), ('F#', False),
                          ('F#', False), ('F#', False), ('G#', False), ('G#', False),
                          ('F#', False), ('G#', False), 'x', 'x', 'x', 'x', ('C#', False),
                          ('C#', False), ('F#', False), ('F#', False), ('G#', False),
                          ('G#', False), 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x',
                          ('E#', True), ('E#', False), ('F#', False), ('F#', False)]
                         )

        mStream.flatten().transpose('p5', inPlace=True)

        # mStream.show()

        self.maxDiff = None
        self.assertEqual(collectAccidentalDisplayStatus(mStream),
                         ['x', ('G#', None), ('G#', None), 'x', 'x', 'x', 'x',
                          ('B#', None), ('B#', None), ('C#', None), ('F#', None), ('G#', None),
                          ('G#', None), ('C#', None), ('C#', None), ('C#', None), ('C#', None),
                          ('D#', None), ('D#', None), ('C#', None), ('D#', None), 'x', 'x',
                          ('F#', None), ('F#', None), ('G#', None), ('G#', None), ('C#', None),
                          ('C#', None), ('D#', None), ('D#', None), 'x', 'x', 'x', 'x', 'x', 'x',
                          ('F#', None), ('F#', None), ('B#', None), ('B#', None),
                          ('C#', None), ('C#', None)]
                         )

    def testMakeTiesAddNewMeasure(self):
        '''
        Test that makeTies adds a new measure when the last note is too long,
        both when called directly and when called from makeNotation
        '''
        p = Part()
        m = Measure(number=1)
        m.append(meter.TimeSignature('4/4'))
        m.append(note.Note(type='breve'))
        p.append(m)
        p_makeTies = p.makeTies()
        self.assertEqual(len(p_makeTies[Measure]), 2)
        n1 = p_makeTies[Measure].first().notes.first()
        n2 = p_makeTies[Measure].last().notes.first()
        self.assertEqual(n1.duration.quarterLength, 4.0)
        self.assertEqual(n1.duration.quarterLength, 4.0)
        self.assertIsNotNone(n1.tie)
        self.assertIsNotNone(n2.tie)
        self.assertEqual(n1.tie.type, 'start')
        self.assertEqual(n2.tie.type, 'stop')

        p_makeNotation = p.makeNotation()
        self.assertEqual(len(p_makeNotation[Measure]), 2)

    def testMeasuresAndMakeMeasures(self):
        s = converter.parse('tinynotation: 2/8 g8 e f g e f g a')
        sSub = s.measures(3, 3)
        self.assertEqual(str(sSub.pitches), '[<music21.pitch.Pitch E4>, <music21.pitch.Pitch F4>]')
        # sSub.show()

    def testSortAndAutoSort(self):
        s = Stream()
        s.autoSort = False

        n1 = note.Note('A')
        n2 = note.Note('B')

        s.insert(100, n2)  # add  'b' first
        s.insert(0, n1)  # now n1 has a higher index than n2

        self.assertEqual([x.name for x in s], ['B', 'A'])
        # try getting sorted
        sSorted = s.sorted()
        # original unchanged
        self.assertEqual([x.name for x in s], ['B', 'A'])
        # new is changed
        self.assertEqual([x.name for x in sSorted], ['A', 'B'])
        # sort in place
        s.sort()
        self.assertEqual([x.name for x in s], ['A', 'B'])

        # test getElements sorting through .notesAndRests w/ autoSort
        s = Stream()
        s.autoSort = True
        n1 = note.Note('A')
        n2 = note.Note('B')
        s.insert(100, n2)  # add  'b' first
        s.insert(0, n1)  # now n1 (A) has a higher index than n2 (B)
        # if we get .notesAndRests, we are getting elements by class, and thus getting
        # sorted version
        self.assertEqual([x.name for x in s.notesAndRests], ['A', 'B'])

        # test getElements sorting through .notesAndRests w/o autoSort
        s = Stream()
        s.autoSort = False
        n1 = note.Note('a')
        n2 = note.Note('b')
        s.insert(100, n2)  # add  'b' first
        s.insert(0, n1)  # now n1 (A) has a higher index than n2 (B)
        self.assertEqual([x.name for x in s.notesAndRests], ['B', 'A'])

        # test __getitem__ calls w/ autoSort
        s = Stream()
        s.autoSort = False
        n1 = note.Note('A')
        n2 = note.Note('B')
        s.insert(100, n2)  # add  'b' first
        s.insert(0, n1)  # now n1 (A) has a higher index than n2 (B)
        self.assertEqual(s[0].name, 'B')
        self.assertEqual(s[1].name, 'A')

        # test __getitem__ calls w autoSort
        s = Stream()
        s.autoSort = True
        n1 = note.Note('a')
        n2 = note.Note('b')
        s.insert(100, n2)  # add  'b' first
        s.insert(0, n1)  # now n1 (A) has a higher index than n2 (B)
        self.assertEqual(s[0].name, 'A')
        self.assertEqual(s[1].name, 'B')

        # test .elements calls w/ autoSort
        s = Stream()
        s.autoSort = False
        n1 = note.Note('a')
        n2 = note.Note('b')
        s.insert(100, n2)  # add  'b' first
        s.insert(0, n1)  # now n1 (A) has a higher index than n2 (B)
        self.assertEqual(s.elements[0].name, 'B')
        self.assertEqual(s.elements[1].name, 'A')

        # test .elements calls w autoSort
        s = Stream()
        s.autoSort = True
        n1 = note.Note('a')
        n2 = note.Note('b')
        s.insert(100, n2)  # add  'b' first
        s.insert(0, n1)  # now n1 (A) has a higher index than n2 (B)
        self.assertEqual(s.elements[0].name, 'A')
        self.assertEqual(s.elements[1].name, 'B')

        # test possible problematic cases of overlapping parts
        # store start time, dur
        pairs = [(20, 2), (15, 10), (22, 1), (10, 2), (5, 25), (8, 10), (0, 2), (0, 30)]

        # with autoSort false
        s = Stream()
        s.autoSort = False
        for o, d in pairs:
            n = note.Note()
            n.quarterLength = d
            s.insert(o, n)
        match = []
        for n in s.notesAndRests:
            match.append((n.offset, n.quarterLength))
        self.assertEqual(pairs, match)

        # with autoSort True
        s = Stream()
        s.autoSort = True
        for o, d in pairs:
            n = note.Note()
            n.quarterLength = d
            s.insert(o, n)
        match = []
        for n in s.notesAndRests:
            match.append((n.offset, n.quarterLength))
        self.assertEqual([(0.0, 2), (0.0, 30), (5.0, 25), (8.0, 10), (10.0, 2),
                          (15.0, 10), (20.0, 2), (22.0, 1.0)], match)

    def testMakeChordsBuiltA(self):
        # test with equal durations
        pitchCol = [('C2', 'A2'),
                    ('A#1', 'C-3', 'G5'),
                    ('B-1', 'D#2', 'D3', 'C4')]
        # try with different duration assignments; should always get
        # the same results
        for durCol in [[1, 1, 1], [0.5, 2, 3], [0.25, 0.25, 0.5], [6, 6, 8]]:
            s = Stream()
            o = 0
            for ql, pitches in zip(durCol, pitchCol):
                for pStr in pitches:
                    n = note.Note(pStr)
                    n.quarterLength = ql
                    s.insert(o, n)
                o += ql
            self.assertEqual(len(s), 9)
            self.assertEqual(len(s.getElementsByClass(chord.Chord)), 0)

            # do both in place and not in place, compare results
            sMod = s.chordify()
            s = s.chordify()
            for sEval in [s, sMod]:
                self.assertEqual(len(sEval.getElementsByClass(chord.Chord)), 3)
                # make sure we have all the original pitches
                for i, pitchEl in enumerate(pitchCol):
                    match = [p.nameWithOctave for p in
                             sEval.getElementsByClass(chord.Chord)[i].pitches]
                    self.assertEqual(match, list(pitchEl))
        # print('post chordify')
        # s.show('t')
        # sMod.show('t')
        # s.show()

    def testMakeChordsBuiltB(self):
        n1 = note.Note('c2')
        n1.quarterLength = 2
        n2 = note.Note('d3')
        n2.quarterLength = 0.5

        n3 = note.Note('e4')
        n3.quarterLength = 2
        n4 = note.Note('f5')
        n4.quarterLength = 0.5

        s = Stream()
        s.insert(0, n1)
        s.insert(1, n2)  # overlapping, starting after n1 but finishing before
        s.insert(2, n3)
        s.insert(3, n4)  # overlapping, starting after n3 but finishing before

        self.assertEqual([e.offset for e in s], [0.0, 1.0, 2.0, 3.0])
        # this results in two chords; n2 and n4 are effectively shifted
        # to the start of n1 and n3
        sMod = s.chordify()
        s = s.chordify()
        for sEval in [s, sMod]:
            # of these 6 chords, only 2 have more than one note
            self.assertEqual(len(sEval.getElementsByClass(chord.Chord)), 6)
            self.assertEqual([c.offset for c in sEval], [0.0, 1.0, 1.5, 2.0, 3.0, 3.5])

        # do the same, but reverse the short/long duration relation
        # because the default min window is 0.25, the first  and last
        # notes are not gathered into chords
        # into a chord
        n1 = note.Note('c2')
        n1.quarterLength = 0.5
        n2 = note.Note('d3')
        n2.quarterLength = 1.5
        n3 = note.Note('e4')
        n3.quarterLength = 0.5
        n4 = note.Note('f5')
        n4.quarterLength = 1.5

        s = Stream()
        s.insert(0, n1)
        s.insert(1, n2)  # overlapping, starting after n1 but finishing before
        s.insert(2, n3)
        s.insert(3, n4)  # overlapping, starting after n3 but finishing before
        # s.makeRests(inPlace=True, fillGaps=True)
        # this results in two chords; n2 and n4 are effectively shifted
        # to the start of n1 and n3
        sMod = s.chordify()

    def testMakeChordsBuiltC(self):
        # test removal of redundant pitches
        n1 = note.Note('c2')
        n1.quarterLength = 0.5
        n2 = note.Note('c2')
        n2.quarterLength = 0.5
        n3 = note.Note('g2')
        n3.quarterLength = 0.5

        n4 = note.Note('e4')
        n4.quarterLength = 0.5
        n5 = note.Note('e4')
        n5.quarterLength = 0.5
        n6 = note.Note('f#4')
        n6.quarterLength = 0.5

        s1 = Stream()
        s1.insert(0, n1)
        s1.insert(0, n2)
        s1.insert(0, n3)
        s1.insert(0.5, n4)
        s1.insert(0.5, n5)
        s1.insert(0.5, n6)

        sMod = s1.chordify(removeRedundantPitches=True)
        self.assertEqual([p.nameWithOctave
                          for p in sMod.getElementsByClass(chord.Chord)[0].pitches],
                          ['C2', 'G2'])

        self.assertEqual([p.nameWithOctave
                          for p in sMod.getElementsByClass(chord.Chord)[1].pitches],
                          ['E4', 'F#4'])

        # without redundant pitch gathering
        sMod = s1.chordify(removeRedundantPitches=False)
        self.assertEqual(
            [p.nameWithOctave for p in sMod.getElementsByClass(chord.Chord)[0].pitches],
            ['C2', 'C2', 'G2']
        )

        self.assertEqual(
            [p.nameWithOctave for p in sMod.getElementsByClass(chord.Chord)[1].pitches],
            ['E4', 'E4', 'F#4']
        )

    def testMakeChordsBuiltD(self):
        # attempt to isolate case
        p1 = Part()
        p1.append([note.Note('G4', quarterLength=2),
                   note.Note('B4', quarterLength=2),
                   note.Note('C4', quarterLength=4),
                   note.Rest(quarterLength=1),
                   note.Note('C4', quarterLength=1),
                   note.Note('B4', quarterLength=1),
                   note.Note('A4', quarterLength=1),

                   ])

        p2 = Part()
        p2.append([note.Note('A3', quarterLength=4),
                   note.Note('F3', quarterLength=4), ])

        p3 = Part()
        p3.append([note.Rest(quarterLength=8),
                   note.Rest(quarterLength=4),
                   ])

        s = Score()
        s.insert([0, p1])
        s.insert([0, p2])
        s.insert([0, p3])

        post = s.flatten().chordify()
        # post.show('t')
        self.assertEqual(len(post.getElementsByClass(note.Rest)), 1)
        self.assertEqual(len(post.getElementsByClass(chord.Chord)), 6)
        # post.show()

    def testGetElementAtOrBeforeBarline(self):
        '''
        problems with getting elements at or before when triplets were involved.
        '''
        bugtestFile = common.getSourceFilePath() / 'stream' / 'tripletOffsetBugtest.xml'
        s = converter.parse(bugtestFile)
        p = s.parts[0]
        m = p.getElementAtOrBefore(2)
        self.assertEqual(m.number, 2)

    def testElementsHighestTimeA(self):
        '''
        Test adding elements at the highest time position
        '''
        n1 = note.Note()
        n1.quarterLength = 30
        n2 = note.Note()
        n2.quarterLength = 20
        b1 = bar.Barline()
        s = Stream()
        s.append(n1)
        self.assertEqual(s.highestTime, 30)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0], n1)
        self.assertEqual(s.index(n1), 0)
        self.assertEqual(s[0].activeSite, s)

        # insert bar in the highest time position
        s.storeAtEnd(b1)
        self.assertEqual(len(s), 2)
        self.assertEqual(s[1], b1)
        self.assertEqual(s.index(b1), 1)
        self.assertEqual(s[1].activeSite, s)
        # offset of b1 is at the highest time
        self.assertEqual([e.offset for e in s], [0.0, 30.0])

        s.append(n2)
        self.assertEqual(len(s), 3)
        self.assertEqual(s[1], n2)
        self.assertEqual(s.index(n2), 1)
        self.assertEqual(s[2], b1)
        self.assertEqual(s.index(b1), 2)
        self.assertEqual(s.highestTime, 50)
        # there are now three elements, and the third is the bar
        self.assertEqual([e.offset for e in s], [0.0, 30, 50.0])

        # get offset by elements
        self.assertEqual(s.elementOffset(n1), 0.0)
        self.assertEqual(s.elementOffset(b1), 50)

        # get elements by offset

        found1 = s.getElementsByOffset(0, 40).stream()
        self.assertEqual(len(found1.notesAndRests), 2)
        # check within the maximum range
        found2 = s.getElementsByOffset(40, 60).stream()
        self.assertEqual(len(found2.notesAndRests), 0)
        # found the barline
        self.assertEqual(found2[0], b1)

        # should get the barline
        self.assertEqual(s.getElementAtOrBefore(50), b1)
        self.assertEqual(s.getElementAtOrBefore(49), n2)

        # can get element after element
        self.assertEqual(s.getElementAfterElement(n1), n2)
        self.assertEqual(s.getElementAfterElement(n2), b1)

        # try to get elements by class
        sub1 = s.getElementsByClass(bar.Barline).stream()
        self.assertEqual(len(sub1), 1)
        # only found item is barline
        self.assertEqual(sub1[0], b1)
        self.assertEqual([e.offset for e in sub1], [0.0])
        # if we append a new element, the old barline should report
        # an offset at the last element
        n3 = note.Note()
        n3.quarterLength = 10
        sub1.append(n3)  # places this before barline
        self.assertEqual(sub1[sub1.index(b1)].offset, 10.0)
        self.assertEqual([e.offset for e in sub1], [0.0, 10.0])

        # try to get elements not of class; only have notes
        sub2 = s.getElementsNotOfClass(bar.Barline)
        self.assertEqual(len(sub2), 2)
        self.assertEqual(len(sub2.notesAndRests), 2)

        sub3 = s.getElementsNotOfClass(note.Note)
        self.assertEqual(len(sub3), 1)
        self.assertEqual(len(sub3.notesAndRests), 0)

        # make a copy:
        sCopy = copy.deepcopy(s)
        self.assertEqual([e.offset for e in sCopy], [0.0, 30, 50.0])
        # not equal b/c a deepcopy was made
        self.assertNotEqual(id(sCopy[2]), id(b1))
        # can still match class
        self.assertIsInstance(sCopy[2], bar.Barline)

        # create another barline and try to replace
        b2 = bar.Barline()
        s.replace(b1, b2)
        self.assertEqual(id(s[2]), id(b2))

        # try to remove elements; the second index is the barline
        self.assertEqual(s.pop(2), b2)
        self.assertEqual(len(s), 2)
        self.assertEqual([e.offset for e in s], [0.0, 30])

        # add back again.
        s.storeAtEnd(b1)
        self.assertEqual([e.offset for e in s], [0.0, 30, 50.0])

        # try to remove intermediary elements
        self.assertEqual(s.pop(1), n2)
        # offset of the highest time element has shifted
        self.assertEqual([e.offset for e in s], [0.0, 30.0])
        # index is now 1
        self.assertEqual(s.index(b1), 1)

    def testStoreAtEndFailures(self):
        s = Stream()
        with self.assertRaises(StreamException):
            s.storeAtEnd(6)

        n = note.Note()
        n.duration.quarterLength = 2.0
        with self.assertRaises(StreamException):
            s.storeAtEnd(n)

        # also test that lists work
        b = bar.Barline()
        s.storeAtEnd([b])

        # also test that element may not be in stream twice.
        with self.assertRaises(StreamException):
            s.storeAtEnd([b])

        # test that element may not be in stream elements and at end.
        b2 = bar.Barline()
        s.insert(0, b2)
        self.assertEqual(b2.offset, 0)
        self.assertEqual(s.elementOffset(b2, returnSpecial=True), 0)
        with self.assertRaises(StreamException):
            s.storeAtEnd(b2)

    def testElementsHighestTimeB(self):
        '''
        Test adding elements at the highest time position
        '''
        n1 = note.Note()
        n1.quarterLength = 30

        n2 = note.Note()
        n2.quarterLength = 20

        b1 = bar.Barline()

        s = Stream()
        s.append(n1)
        s.append(n2)
        s.storeAtEnd(b1)
        self.assertEqual([e.offset for e in s], [0.0, 30.0, 50.0])

        # can shift elements, altering all, but only really shifting
        # standard elements
        s.shiftElements(5)
        self.assertEqual([e.offset for e in s], [5.0, 35.0, 55.0])

        # got all
        found1 = s.extractContext(n2, 30)
        self.assertEqual([e.offset for e in found1], [5.0, 35.0, 55.0])
        # just after, none before
        found1 = s.extractContext(n2, 0, 30)
        self.assertEqual([e.offset for e in found1], [35.0, 55.0])

    def testElementsHighestTimeC(self):

        n1 = note.Note()
        n1.quarterLength = 30

        n2 = note.Note()
        n2.quarterLength = 20

        ts1 = meter.TimeSignature('6/8')
        b1 = bar.Barline()
        c1 = clef.Treble8vaClef()

        s = Stream()
        s.append(n1)
        self.assertEqual([e.offset for e in s], [0.0])

        s.storeAtEnd(b1)
        s.storeAtEnd(c1)
        s.storeAtEnd(ts1)
        self.assertEqual([e.offset for e in s], [0.0, 30.0, 30.0, 30.0])

        s.append(n2)
        self.assertEqual([e.offset for e in s], [0.0, 30.0, 50.0, 50.0, 50.0])
        # sorting of objects is by class
        self.assertEqual([e.classes[0] for e in s],
                         ['Note', 'Note', 'Barline', 'Treble8vaClef', 'TimeSignature'])

        b2 = bar.Barline()
        s.storeAtEnd(b2)
        self.assertEqual([e.classes[0] for e in s],
                         ['Note', 'Note', 'Barline', 'Barline', 'Treble8vaClef', 'TimeSignature'])

    def testSliceByQuarterLengthsBuilt(self):
        s = Stream()
        n1 = note.Note()
        n1.quarterLength = 1

        n2 = note.Note()
        n2.quarterLength = 2

        n3 = note.Note()
        n3.quarterLength = 0.5

        n4 = note.Note()
        n4.quarterLength = 1.5

        for n in [n1, n2, n3, n4]:
            s.append(n)

        post = s.sliceByQuarterLengths(0.125, inPlace=False)
        self.assertEqual([n.tie.type for n in post.notesAndRests],
                         ['start', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'continue', 'stop', 'start', 'continue', 'continue',
                          'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
                          'stop', 'start', 'continue', 'continue', 'stop', 'start', 'continue',
                          'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'continue', 'continue', 'stop'])

        post = s.sliceByQuarterLengths(0.25, inPlace=False)
        self.assertEqual([n.tie.type for n in post.notesAndRests],
                         ['start', 'continue', 'continue', 'stop', 'start', 'continue',
                          'continue', 'continue', 'continue', 'continue', 'continue',
                          'stop', 'start', 'stop', 'start', 'continue', 'continue',
                          'continue', 'continue', 'stop'])

        post = s.sliceByQuarterLengths(0.5, inPlace=False)
        self.assertEqual([n.tie is None for n in post.notesAndRests],
                         [False, False, False, False, False, False, True, False, False, False])

        # cannot map 0.3333 into 0.5, so this raises an exception
        self.assertRaises(StreamException,
                          lambda: s.sliceByQuarterLengths(1 / 3, inPlace=False))

        post = s.sliceByQuarterLengths(1 / 6, inPlace=False)
        self.assertEqual([n.tie.type for n in post.notesAndRests],
                         ['start', 'continue', 'continue', 'continue', 'continue', 'stop',
                          'start', 'continue', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'continue', 'continue', 'continue', 'continue', 'stop',
                          'start', 'continue', 'stop', 'start', 'continue', 'continue',
                          'continue', 'continue', 'continue', 'continue', 'continue', 'stop'])
        # post.show()

        # try to slice just a target
        post = s.sliceByQuarterLengths(0.125, target=n2, inPlace=False)
        self.assertEqual([n.tie is None for n in post.notesAndRests],
                         [True,
                          False, False, False, False, False, False, False,
                          False, False, False, False, False, False, False, False, False,
                          True, True])

        # post.show()

        # test case where we have an existing tied note in a multi Measure structure
        # that we do not want to break
        s = Stream()
        n1 = note.Note()
        n1.quarterLength = 8

        n2 = note.Note()
        n2.quarterLength = 8

        n3 = note.Note()
        n3.quarterLength = 8

        s.append(n1)
        s.append(n2)
        s.append(n3)

        self.assertEqual(s.highestTime, 24)
        sMeasures = s.makeMeasures()
        sMeasures.makeTies(inPlace=True)

        self.assertEqual([n.tie.type for n in sMeasures.flatten().notesAndRests],
                         ['start', 'stop', 'start', 'stop', 'start', 'stop'])

        # this shows that the previous ties across the bar line are maintained
        # even after slicing
        sMeasures.sliceByQuarterLengths([0.5], inPlace=True)
        self.assertEqual(
            [n.tie.type for n in sMeasures.flatten().notesAndRests],
            ['start', 'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
             'continue', 'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
             'continue', 'stop', 'start', 'continue', 'continue', 'continue', 'continue',
             'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
             'continue', 'continue', 'continue', 'continue', 'stop', 'start', 'continue',
             'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
             'continue', 'continue', 'continue', 'continue', 'continue', 'continue',
             'continue', 'stop'])

        # sMeasures.show()

        s = Stream()
        n1 = note.Note('c#')
        n1.quarterLength = 1

        n2 = note.Note('d-')
        n2.quarterLength = 2

        n3 = note.Note('f#')
        n3.quarterLength = 0.5

        n4 = note.Note('g#')
        n4.quarterLength = 1.5

        for n in [n1, n2, n3, n4]:
            s.append(n)

        post = s.sliceByQuarterLengths(0.125, inPlace=False)
        # post.show()

        self.assertTrue(all(n.tie is not None for n in post.notesAndRests))

        s = Stream()
        n1 = note.Note()
        n1.quarterLength = 0.25

        n2 = note.Note()
        n2.quarterLength = 0.5

        n3 = note.Note()
        n3.quarterLength = 1

        n4 = note.Note()
        n4.quarterLength = 1.5

        for n in [n1, n2, n3, n4]:
            s.append(n)

        post = s.sliceByQuarterLengths(0.5, inPlace=False)
        self.assertEqual([n.tie is None for n in post.notesAndRests],
                         [True, True, False, False, False, False, False])

    def testSliceByQuarterLengthsImported(self):

        sSrc = corpus.parse('bwv66.6')
        s = copy.deepcopy(sSrc)
        for p in s.parts:
            p.sliceByQuarterLengths(0.5, inPlace=True, addTies=False)
            p.makeBeams(inPlace=True)
        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 72)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 72)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 72)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 72)

        s = copy.deepcopy(sSrc)
        for p in s.parts:
            p.sliceByQuarterLengths(0.25, inPlace=True, addTies=False)
            p.makeBeams(inPlace=True)
        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 144)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 144)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 144)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 144)

        # test applying to a complete score; works fine
        s = copy.deepcopy(sSrc)
        s.sliceByQuarterLengths(0.5, inPlace=True, addTies=False)
        # s.show()
        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 72)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 72)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 72)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 72)

    def testSliceByGreatestDivisorBuilt(self):

        s = Stream()
        n1 = note.Note()
        n1.quarterLength = 1.75
        n2 = note.Note()
        n2.quarterLength = 2
        n3 = note.Note()
        n3.quarterLength = 0.5
        n4 = note.Note()
        n4.quarterLength = 1.5
        for n in [n1, n2, n3, n4]:
            s.append(n)
        post = s.sliceByGreatestDivisor(inPlace=False)

        self.assertEqual(len(post.flatten().notesAndRests), 23)
        self.assertEqual([n.tie.type for n in post.notesAndRests],
                         ['start', 'continue', 'continue', 'continue', 'continue', 'continue',
                          'stop', 'start', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'continue', 'stop', 'start', 'stop', 'start',
                          'continue', 'continue', 'continue', 'continue', 'stop'])

        s = Stream()
        n1 = note.Note()
        n1.quarterLength = 2
        n2 = note.Note()
        n2.quarterLength = 1 / 3
        n3 = note.Note()
        n3.quarterLength = 0.5
        n4 = note.Note()
        n4.quarterLength = 1.5
        for n in [n1, n2, n3, n4]:
            s.append(n)
        post = s.sliceByGreatestDivisor(inPlace=False)

        self.assertEqual(len(post.flatten().notesAndRests), 26)
        self.assertEqual([n.tie.type for n in post.notesAndRests],
                         ['start', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'stop', 'start', 'stop', 'start', 'continue',
                          'stop', 'start', 'continue', 'continue', 'continue', 'continue',
                          'continue', 'continue', 'continue', 'stop'])

    def testSliceByGreatestDivisorImported(self):

        s = corpus.parse('bwv66.6')
        for p in s.parts:
            p.sliceByGreatestDivisor(inPlace=True, addTies=True)
            # p.makeBeams(inPlace=True)
            # uncomment when debugging, otherwise just slows down the test
        # s.show()
        # parts have different numbers of notes, as splitting is done on
        # a note per note basis
        self.assertEqual(len(s.parts[0].flatten().notesAndRests), 44)
        self.assertEqual(len(s.parts[1].flatten().notesAndRests), 59)
        self.assertEqual(len(s.parts[2].flatten().notesAndRests), 61)
        self.assertEqual(len(s.parts[3].flatten().notesAndRests), 53)

        # s = corpus.parse('bwv66.6')
        # s.sliceByGreatestDivisor(inPlace=True, addTies=True)
        # s.flatten().chordify().show()
        # s.show()

    def testSliceAtOffsetsSimple(self):
        s = Stream()
        n = note.Note()
        n.quarterLength = 4
        s.append(n)
        s.sliceAtOffsets([1, 2, 3], inPlace=True)
        a = [(e.offset, e.quarterLength) for e in s]
        b = [(0.0, 1.0), (1.0, 1.0), (2.0, 1.0), (3.0, 1.0)]
        self.assertEqual(a, b)

    def testSliceAtOffsetsBuilt(self):
        s = Stream()
        for p, ql in [('d2', 4)]:
            n = note.Note(p)
            n.quarterLength = ql
            s.append(n)
        self.assertEqual([e.offset for e in s], [0.0])

        s1 = s.sliceAtOffsets([0.5, 1, 1.5, 2, 2.5, 3, 3.5], inPlace=False)
        self.assertEqual([(e.offset, e.quarterLength) for e in s1],
                         [(0.0, 0.5), (0.5, 0.5), (1.0, 0.5), (1.5, 0.5), (2.0, 0.5),
                          (2.5, 0.5), (3.0, 0.5), (3.5, 0.5)])

        s1 = s.sliceAtOffsets([0.5], inPlace=False)
        self.assertEqual([(e.offset, e.quarterLength) for e in s1], [(0.0, 0.5), (0.5, 3.5)])

        s = Stream()
        for p, ql in [('a2', 1.5), ('a2', 1.5), ('a2', 1.5)]:
            n = note.Note(p)
            n.quarterLength = ql
            s.append(n)
        self.assertEqual([e.offset for e in s], [0.0, 1.5, 3.0])

        s1 = s.sliceAtOffsets([0.5], inPlace=False)
        self.assertEqual([e.offset for e in s1], [0.0, 0.5, 1.5, 3.0])
        s1.sliceAtOffsets([1.0, 2.5], inPlace=True)
        self.assertEqual([e.offset for e in s1], [0.0, 0.5, 1.0, 1.5, 2.5, 3.0])
        s1.sliceAtOffsets([3.0, 2.0, 3.5, 4.0], inPlace=True)
        self.assertEqual([e.offset for e in s1], [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])

        self.assertEqual([e.quarterLength for e in s1],
                         [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

    def testSliceAtOffsetsImported(self):
        sSrc = corpus.parse('bwv66.6')

        post = sSrc.parts[0].flatten().sliceAtOffsets([0.25, 1.25, 3.25])
        self.assertEqual([e.offset for e in post],
                         [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.5, 1.0, 1.25, 2.0, 3.0, 3.25, 4.0,
                          5.0, 6.0, 7.0, 8.0, 9.0, 9.0, 9.5, 10.0, 11.0, 12.0, 13.0, 14.0,
                          15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 21.0, 22.0, 23.0, 24.0,
                          25.0, 26.0, 27.0, 29.0, 31.0, 32.0, 33.0, 34.0, 34.5, 35.0, 36.0])

        # will also work on measured part
        post = sSrc.parts[0].sliceAtOffsets([0.25, 1.25, 3.25, 35.125])
        self.assertEqual([e.offset for e in
                          post.getElementsByClass(Measure)[0].notesAndRests],
                         [0.0, 0.25, 0.5])
        self.assertEqual([e.offset for e in
                          post.getElementsByClass(Measure)[1].notesAndRests],
                         [0.0, 0.25, 1.0, 2.0, 2.25, 3.0])
        # check for alteration in last measure
        self.assertEqual([e.offset for e in
                          post.getElementsByClass(Measure)[-1].notesAndRests],
                         [0.0, 1.0, 1.5, 2.0, 2.125])

    def testSliceByBeatBuilt(self):
        s = Stream()
        ts1 = meter.TimeSignature('3/4')
        s.insert(0, ts1)
        for p, ql in [('d2', 3)]:
            n = note.Note(p)
            n.quarterLength = ql
            s.append(n)
        # have time signature and one note
        self.assertEqual([e.offset for e in s], [0.0, 0.0])

        s1 = s.sliceByBeat()
        self.assertEqual([(e.offset, e.quarterLength) for e in s1.notesAndRests],
                         [(0.0, 1.0), (1.0, 1.0), (2.0, 1.0)])

        # replace old ts with a new
        s.remove(ts1)
        ts2 = meter.TimeSignature('6/8')
        s.insert(0, ts2)
        s1 = s.sliceByBeat()
        self.assertEqual([(e.offset, e.quarterLength) for e in s1.notesAndRests],
                         [(0.0, 1.5), (1.5, 1.5)])

    def testSliceByBeatImported(self):
        sSrc = corpus.parse('bwv66.6')
        post = sSrc.parts[0].sliceByBeat()
        self.assertEqual([e.offset for e in post.flatten().notesAndRests],
                         [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 9.5,
                          10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0,
                          20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0,
                          30.0, 31.0, 32.0, 33.0, 34.0, 34.5, 35.0])

        # post.show()

    def testChordifyImported(self):
        s = corpus.parse('luca/gloria')
        # s.show()
        post = s.measures(0, 20, gatherSpanners=False)
        # somehow, this is doubling measures
        # post.show()

        self.assertEqual([e.offset for e in post.parts[0].flatten().notesAndRests],
                         [0.0, 3.0, 3.5, 4.5, 5.0, 6.0, 6.5, 7.5, 8.5, 9.0, 10.5,
                          12.0, 15.0, 16.5, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5,
                          21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 30.0, 33.0, 34.5,
                          35.5, 36.0, 37.5, 38.0, 39.0, 40.0, 41.0, 42.0, 43.5, 45.0,
                          45.5, 46.5, 47.0, 48.0, 49.5, 51.0, 51.5, 52.0, 52.5, 53.0,
                          53.5, 54.0, 55.5, 57.0, 58.5])

        post = post.chordify()
        # post.show('t')
        # post.show()
        self.assertEqual([e.offset for e in post.flatten().notes],
                         [0.0, 3.0, 3.5, 4.5, 5.0, 5.5, 6.0, 6.5, 7.5, 8.5, 9.0, 10.5,
                          12.0, 15.0, 16.5, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5,
                          21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5, 25.0, 25.5,
                          26.0, 26.5, 27.0, 30.0, 33.0, 34.5, 35.5, 36.0, 37.5, 38.0,
                          39.0, 40.0, 40.5, 41.0, 42.0, 43.5, 45.0, 45.5, 46.0, 46.5,
                           47.0, 47.5, 48.0, 49.5, 51.0, 51.5, 52.0, 52.5, 53.0, 53.5,
                           54.0, 54.5, 55.0, 55.5, 56.0, 56.5, 57.0, 58.5, 59.5])
        self.assertEqual(len(post[chord.Chord]), 71)
        # Careful! one version of the caching is screwing up m. 20 which definitely should
        # not have rests in it -- was creating 69 notes, not 71.

    def testChordifyRests(self):
        # test that chordify does not choke on rests
        p1 = Part()
        for p, ql in [(None, 2), ('d2', 2), (None, 2), ('e3', 2), ('f3', 2)]:
            if p is None:
                n = note.Rest()
            else:
                n = note.Note(p)
            n.quarterLength = ql
            p1.append(n)

        p2 = Part()
        for p, ql in [(None, 2), ('c#3', 1), ('d#3', 1), (None, 2), ('e-5', 2), (None, 2)]:
            if p is None:
                n = note.Rest()
            else:
                n = note.Note(p)
            n.quarterLength = ql
            p2.append(n)

        self.assertEqual([e.offset for e in p1], [0.0, 2.0, 4.0, 6.0, 8.0])
        self.assertEqual([e.offset for e in p2], [0.0, 2.0, 3.0, 4.0, 6.0, 8.0])

        score = Score()
        score.insert(0, p1)
        score.insert(0, p2)
        # parts retain their characteristics
        # rests are recast
        p1Chords = score.parts[0].chordify()
        p2Chords = score.parts[1].chordify()

        self.assertEqual(len(p1Chords.flatten()), 5)
        self.assertEqual(len(p1Chords.flatten().getElementsByClass(chord.Chord)), 3)
        self.assertEqual(len(p1Chords.flatten().getElementsByClass(note.Rest)), 2)

        self.assertEqual(len(p2Chords.flatten()), 6)
        self.assertEqual(len(p2Chords.flatten().getElementsByClass(chord.Chord)), 3)
        self.assertEqual(len(p2Chords.flatten().getElementsByClass(note.Rest)), 3)

        # calling this on a flattened version
        scoreFlat = score.flatten()
        scoreChords = scoreFlat.chordify()
        # fourth chord actually comprises only one note!
        self.assertEqual(len(scoreChords.flatten().getElementsByClass(chord.Chord)), 4)
        self.assertEqual(len(scoreChords.flatten().getElementsByClass(note.Rest)), 2)

        scoreChordify = score.chordify()
        self.assertEqual(len(scoreChordify.flatten().getElementsByClass(chord.Chord)), 4)
        self.assertEqual(len(scoreChordify.flatten().getElementsByClass(note.Rest)), 2)

        self.assertEqual(str(scoreChordify.getElementsByClass(chord.Chord).first().pitches),
                         '(<music21.pitch.Pitch D2>, <music21.pitch.Pitch C#3>)')
        self.assertEqual(str(scoreChordify.getElementsByClass(chord.Chord)[1].pitches),
                         '(<music21.pitch.Pitch D2>, <music21.pitch.Pitch D#3>)')

    def testChordifyA(self):
        p1 = Part()
        p1.insert(0, note.Note(quarterLength=12.0))
        p1.insert(0.25, expressions.TextExpression('test'))
        self.assertEqual(p1.highestTime, 12.0)
        p2 = Part()
        p2.repeatAppend(note.Note('g4'), 12)

        s = Score()
        s.insert(0, p1)
        s.insert(0, p2)
        post = s.chordify()
        self.assertEqual(len(post.getElementsByClass(chord.Chord)), 12)
        self.assertEqual(str(post.getElementsByClass(chord.Chord).first().pitches),
                         '(<music21.pitch.Pitch C4>, <music21.pitch.Pitch G4>)')

        p1 = Part()
        p1.insert(0, note.Note(quarterLength=12.0))
        p1.insert(0.25, expressions.TextExpression('test'))
        self.assertEqual(p1.highestTime, 12.0)
        p2 = Part()
        p2.repeatAppend(note.Note('g4', quarterLength=6.0), 2)
        # p.repeatAppend(note.Note('g4'), 12)

        s = Score()
        s.insert(0, p1)
        s.insert(0, p2)
        post = s.chordify()
        self.assertEqual(len(post.getElementsByClass(chord.Chord)), 2)
        self.assertEqual(str(post.getElementsByClass(chord.Chord).first().pitches),
                         '(<music21.pitch.Pitch C4>, <music21.pitch.Pitch G4>)')
        # post.show()

        # s.show()

    def testChordifyB(self):
        p1 = Part()
        m1a = Measure()
        m1a.timeSignature = meter.TimeSignature('4/4')
        m1a.insert(0, note.Note())
        m1a.padAsAnacrusis()
        self.assertEqual(m1a.paddingLeft, 3.0)
        # m1a.paddingLeft = 3.0  # a quarter pickup
        m2a = Measure()
        m2a.repeatAppend(note.Note(), 4)
        p1.append([m1a, m2a])

        p2 = Part()
        m1b = Measure()
        m1b.timeSignature = meter.TimeSignature('4/4')
        m1b.repeatAppend(note.Rest(), 1)
        m1b.padAsAnacrusis()
        self.assertEqual(m1b.paddingLeft, 3.0)
        m2b = Measure()
        m2b.repeatAppend(note.Note('g4'), 4)
        p2.append([m1b, m2b])

        s = Score()
        s.insert(0, p1)
        s.insert(0, p2)
        # s.show()
        post = s.chordify()
        self.assertEqual(len(post.getElementsByClass(Measure)), 2)
        m1 = post.getElementsByClass(Measure).first()
        # test that padding has been maintained
        self.assertEqual(m1.paddingLeft, 3.0)
        # post.show()

    def testChordifyC(self):
        '''
        Chordifies with triplets (floating point errors)
        '''
        s = corpus.parse('schoenberg/opus19/movement6')
        # s.show('text')
        m1 = s.parts.first().getElementsByClass(Measure).first()
        # m1.show('text')

        self.assertEqual(m1.highestTime, 1.0)
        self.assertEqual(m1.paddingLeft, 3.0)
        self.assertEqual(m1.duration.quarterLength, 1.0)
        self.assertEqual([e.offset for e in m1.notes], [0.0])
        # s.parts[0].show()
        post = s.chordify()
        # pst.show('text', addEndTimes=True)
        self.assertEqual(post.getElementsByClass(Measure).first().paddingLeft, 3.0)
        # self.assertEqual(len(post.flatten()), 3)
        # post.show()

        # make sure we do not have any voices after chordifying
        match = []
        for m in post.getElementsByClass(Measure):
            self.assertFalse(m.hasVoices())
            match.append(len(m.pitches))
        self.assertEqual(match, [3, 9, 9, 25, 25, 21, 12, 6, 21, 29])
        self.assertEqual(len(post.flatten().getElementsByClass(note.Rest)), 4)

    def testChordifyD(self):
        # test on a Stream of Streams.
        s1 = Stream()
        s1.repeatAppend(note.Note(quarterLength=3), 4)
        s2 = Stream()
        s2.repeatAppend(note.Note('g4', quarterLength=2), 6)
        s3 = Stream()
        s3.insert(0, s1)
        s3.insert(0, s2)

        post = s3.chordify()
        self.assertEqual(len(post.getElementsByClass(chord.Chord)), 8)

    def testChordifyE(self):
        s1 = Stream()
        m1 = Measure()
        v1 = Voice()
        v1.repeatAppend(note.Note('g4', quarterLength=1.5), 3)
        v2 = Voice()
        v2.repeatAppend(note.Note(quarterLength=1), 6)
        m1.insert(0, v1)
        m1.insert(0, v2)
        # m.timeSignature = m1.flatten().bestTimeSignature()
        # self.assertEqual(str(m1.timeSignature), '')
        s1.append(m1)
        # s1.show()
        post = s1.chordify()
        # post.show()
        self.assertEqual(len(post[chord.Chord]), 8)

    # noinspection SpellCheckingInspection
    def testOpusSearch(self):
        import re
        o = corpus.parse('essenFolksong/erk5')
        s = o.getScoreByTitle('blauen')
        self.assertEqual(s.metadata.title, 'Ich sach mir einen blauen Storchen')

        s = o.getScoreByTitle('pfal.gr.f')
        self.assertEqual(s.metadata.title, 'Es fuhr sich ein Pfalzgraf')

        s = o.getScoreByTitle(re.compile('Pfal(.*)'))
        self.assertEqual(s.metadata.title, 'Es fuhr sich ein Pfalzgraf')

    def testOpusSequence(self):
        '''
        Providing a sequence of Scores to an Opus container should append
        rather than insert each at 0.0.
        '''
        s1 = Score(Part(Measure(note.Note())))
        s2 = Score(Part(Measure(note.Note())))
        o = Opus([s1, s2])
        self.assertEqual(o.elementOffset(s2), 1.0)

    def testActiveSiteMangling(self):
        outer = Stream()
        inner = Stream()
        outer.append(inner)

        self.assertEqual(inner.activeSite, outer)
        junk = inner.flatten(retainContainers=True)
        self.assertEqual(inner.activeSite, outer)
        junk = inner.flatten()
        # the order of these two calls ensures that flatten() is called without cache
        self.assertEqual(inner.activeSite, outer)

        # this works fine
        junk = outer.flatten()
        self.assertEqual(inner.activeSite, outer)

        # this was the key problem: getting the semiFlat of the activeSite
        # looses the activeSite of the sub-stream; this is fixed by the inserting
        # of the sub-Stream with setActiveSite False
        junk = outer.flatten(retainContainers=True)
        self.assertEqual(inner.activeSite, outer)

        # these test prove that getting a semiFlat stream does not change the
        # activeSite
        junk = inner.sites.getObjByClass(meter.TimeSignature)
        self.assertEqual(inner.activeSite, outer)

        junk = inner.sites.getObjByClass(clef.Clef)
        self.assertEqual(inner.activeSite, outer)

        junk = inner.getContextByClass(clef.Clef)
        self.assertEqual(inner.activeSite, outer)

    def testGetElementsByContextStream(self):

        s = corpus.parse('bwv66.6')
        for p in s.parts:
            for m in p.getElementsByClass(Measure):
                n = m.notes[0]
                post = n.getContextByClass(clef.Clef)
                self.assertTrue(isinstance(post, clef.Clef), post)
                post = n.getContextByClass(meter.TimeSignature)
                self.assertTrue(isinstance(post, meter.TimeSignature), post)
                post = n.getContextByClass(key.KeySignature)
                self.assertTrue(isinstance(post, key.KeySignature), post)

    def testVoicesA(self):

        v1 = Voice()
        n1 = note.Note('d5')
        n1.quarterLength = 0.5
        v1.repeatAppend(n1, 4)

        v2 = Voice()
        n2 = note.Note('c4')
        n2.quarterLength = 1
        v2.repeatAppend(n2, 2)

        s = Measure()
        s.insert(0, v1)
        s.insert(0, v2)

        # test allocating streams and assigning indices
        oMap = s.offsetMap()

        self.assertTrue(common.whitespaceEqual(
            repr(oMap),
            '''[OffsetMap(element=<music21.note.Note D>, offset=0.0, endTime=0.5, voiceIndex=0),
            OffsetMap(element=<music21.note.Note D>, offset=0.5, endTime=1.0, voiceIndex=0),
            OffsetMap(element=<music21.note.Note D>, offset=1.0, endTime=1.5, voiceIndex=0),
            OffsetMap(element=<music21.note.Note D>, offset=1.5, endTime=2.0, voiceIndex=0),
            OffsetMap(element=<music21.note.Note C>, offset=0.0, endTime=1.0, voiceIndex=1),
            OffsetMap(element=<music21.note.Note C>, offset=1.0, endTime=2.0, voiceIndex=1)]'''))

        oMeasures = Part()
        oMeasures.insert(0, s)
        self.assertEqual(len(oMeasures[0].voices), 2)
        self.assertEqual([e.offset for e in oMeasures[0].voices[0]],
                         [0.0, 0.5, 1.0, 1.5])
        self.assertEqual([e.offset for e in oMeasures[0].voices[1]],
                         [0.0, 1.0])

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(s).decode('utf-8')

    def testVoicesALonger(self):

        # try version longer than 1 measure, more than 2 voices
        v1 = Voice()
        n1 = note.Note('c5')
        n1.quarterLength = 0.5
        v1.repeatAppend(n1, 32)

        v2 = Voice()
        n2 = note.Note('c4')
        n2.quarterLength = 1
        v2.repeatAppend(n2, 16)

        v3 = Voice()
        n3 = note.Note('c3')
        n3.quarterLength = 0.25
        v3.repeatAppend(n3, 64)

        v4 = Voice()
        n4 = note.Note('c2')
        n4.quarterLength = 4
        v4.repeatAppend(n4, 4)

        s = Part()
        s.insert(0, v1)
        s.insert(0, v2)
        s.insert(0, v3)
        s.insert(0, v4)

        oMeasures = s.makeMeasures()

        # each measure has the same number of voices
        for i in range(3):
            self.assertEqual(len(oMeasures[i].voices), 4)
        # each measure has the same total number of voices
        for i in range(3):
            self.assertEqual(len(oMeasures[i].flatten().notesAndRests), 29)
        # each measure has the same number of notes for each voices
        for i in range(3):
            self.assertEqual(len(oMeasures[i].voices[0].notesAndRests), 8)
            self.assertEqual(len(oMeasures[i].voices[1].notesAndRests), 4)
            self.assertEqual(len(oMeasures[i].voices[2].notesAndRests), 16)
            self.assertEqual(len(oMeasures[i].voices[3].notesAndRests), 1)

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(oMeasures).decode('utf-8')
        # s.show()

    def testVoicesB(self):

        # make sure strip ties works
        v1 = Voice()
        n1 = note.Note('c5')
        n1.quarterLength = 0.5
        v1.repeatAppend(n1, 27)

        v2 = Voice()
        n2 = note.Note('c4')
        n2.quarterLength = 3
        v2.repeatAppend(n2, 6)

        v3 = Voice()
        n3 = note.Note('c3')
        n3.quarterLength = 8
        v3.repeatAppend(n3, 4)

        s = Stream()
        s.insert(0, v1)
        s.insert(0, v2)
        s.insert(0, v3)

        sPost = s.makeNotation()
        # voices are retained for all measures after makeNotation, unless unnecessary
        self.assertEqual(len(sPost.getElementsByClass(Measure)), 8)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[0].voices), 3)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[1].voices), 3)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[4].voices), 2)
        self.assertEqual(len(sPost.getElementsByClass(Measure)[5].voices), 0)

        # s.show()

    def testVoicesC(self):
        v1 = Voice()
        n1 = note.Note('c5')
        n1.quarterLength = 0.25
        v1.repeatInsert(n1, [2, 4.5, 7.25, 11.75])

        v2 = Voice()
        n2 = note.Note('c4')
        n2.quarterLength = 0.25
        v2.repeatInsert(n2, [0.25, 3.75, 5.5, 13.75])

        s = Stream()
        s.insert(0, v1)
        s.insert(0, v2)

        sPost = s.makeRests(fillGaps=True, inPlace=False)
        self.assertEqual(str(list(sPost.voices[0].notesAndRests)),
                         '[<music21.note.Rest half>, <music21.note.Note C>, '
                         + '<music21.note.Rest 2.25ql>, '
                         + '<music21.note.Note C>, '
                         + '<music21.note.Rest 2.5ql>, '
                         + '<music21.note.Note C>, '
                         + '<music21.note.Rest 4.25ql>, '
                         + '<music21.note.Note C>, '
                         + '<music21.note.Rest half>]')
        self.assertEqual(str(list(sPost.voices[1].notesAndRests)),
                         '[<music21.note.Rest 16th>, <music21.note.Note C>, '
                         + '<music21.note.Rest 3.25ql>, '
                         + '<music21.note.Note C>, '
                         + '<music21.note.Rest dotted-quarter>, <music21.note.Note C>, '
                         + '<music21.note.Rest breve>, <music21.note.Note C>]')

        # sPost.show()

    def testPartsToVoicesA(self):
        s0 = corpus.parse('bwv66.6')
        # s.show()
        s1 = s0.partsToVoices(2)
        # s1.show()
        # s1.show('t')
        self.assertEqual(len(s1.parts), 2)

        p1 = s1.parts[0]
        self.assertEqual(len(p1.flatten().getElementsByClass(clef.Clef)), 1)
        # p1.show('t')

        # look at individual measure; check counts; these should not
        # change after measure extraction
        m1Raw = p1.getElementsByClass(Measure)[1]
        # environLocal.printDebug(['m1Raw', m1Raw])
        self.assertEqual(len(m1Raw.flatten()), 8)

        # m1Raw.show('t')
        m2Raw = p1.getElementsByClass(Measure)[2]
        # environLocal.printDebug(['m2Raw', m2Raw])
        self.assertEqual(len(m2Raw.flatten()), 9)

        # get a measure from this part
        # NOTE: we no longer get Clef here, as we return clefs in the
        # Part outside a Measure when using measures()
        # m = p1.measure(2)
        # self.assertEqual(len(m1.flatten().getElementsByClass(clef.Clef)), 1)

        # look at individual measure; check counts; these should not
        # change after measure extraction
        m1Raw = p1.getElementsByClass(Measure)[1]
        # environLocal.printDebug(['m1Raw', m1Raw])
        self.assertEqual(len(m1Raw.flatten()), 8)

        # m1Raw.show('t')
        m2Raw = p1.getElementsByClass(Measure)[2]
        # environLocal.printDebug(['m2Raw', m2Raw])
        self.assertEqual(len(m2Raw.flatten()), 9)

        # m2Raw.show('t')

        # self.assertEqual(len(m1.flatten().getElementsByClass(clef.Clef)), 1)
        ex1 = p1.measures(1, 3)
        self.assertEqual(len(ex1.flatten().getElementsByClass(clef.Clef)), 1)

        # ex1.show()

        for p in s1.parts:
            # need to look in measures to get at voices
            self.assertEqual(len(p.getElementsByClass(Measure).first().voices), 2)
            self.assertEqual(len(p.measure(2).voices), 2)
            self.assertEqual(len(p.measures(
                1, 3).getElementsByClass(Measure)[2].voices), 2)

        # s1.show()
        # p1.show()

    def testPartsToVoicesB(self):
        # this work has five parts: results in e parts
        s0 = corpus.parse('corelli/opus3no1/1grave')
        self.assertEqual(len(s0.parts), 3)
        s1 = s0.partsToVoices(2, permitOneVoicePerPart=True)
        self.assertEqual(len(s1.parts), 2)
        self.assertEqual(len(s1.parts[0].getElementsByClass(Measure).first().voices), 2)
        self.assertEqual(len(s1.parts[1].getElementsByClass(Measure).first().voices), 1)

        # s1.show()

        # s0 = corpus.parse('hwv56', '1-05')
        # # can use index values
        # s2 = s0.partsToVoices(([0, 1], [2, 4], 3), permitOneVoicePerPart=True)
        # self.assertEqual(len(s2.parts), 3)
        # self.assertEqual(len(s2.parts[0].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(len(s2.parts[1].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(len(s2.parts[2].getElementsByClass(
        #     'Measure')[0].voices), 1)

        # s2 = s0.partsToVoices((['Violino I', 'Violino II'], ['Viola', 'Bassi'], ['Basso']),
        #        permitOneVoicePerPart=True)
        # self.assertEqual(len(s2.parts), 3)
        # self.assertEqual(len(s2.parts[0].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(len(s2.parts[1].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(len(s2.parts[2].getElementsByClass(
        #     'Measure')[0].voices), 1)
        # # this will keep the voice part unaltered
        # s2 = s0.partsToVoices((['Violino I', 'Violino II'], ['Viola', 'Bassi'], 'Basso'),
        #        permitOneVoicePerPart=False)
        # self.assertEqual(len(s2.parts), 3)
        # self.assertEqual(len(s2.parts[0].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(len(s2.parts[1].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(s2.parts[2].getElementsByClass(
        #     'Measure')[0].hasVoices(), False)

        # # mm 16-19 are a good examples
        # s1 = corpus.parse('hwv56', '1-05').measures(16, 19)
        # s2 = s1.partsToVoices((['Violino I', 'Violino II'], ['Viola', 'Bassi'], 'Basso'))
        # # s.show()

        # self.assertEqual(len(s2.parts), 3)
        # self.assertEqual(len(s2.parts[0].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(len(s2.parts[1].getElementsByClass(
        #     'Measure')[0].voices), 2)
        # self.assertEqual(s2.parts[2].getElementsByClass(
        #     'Measure')[0].hasVoices(), False)

    def testPartsToVoicesSpanner(self):
        # NOTE: this test spanners merged from two parts into one part
        clef1 = clef.TrebleClef()
        clef2 = clef.TrebleClef()
        ts1 = meter.TimeSignature('12/8')
        ts2 = meter.TimeSignature('12/8')

        m1 = Measure()
        m2 = Measure()
        n1 = note.Note('C#5', type='eighth')
        n2 = note.Note('D5', type='eighth')
        n3 = note.Note('A5', type='eighth')
        n4 = note.Note('B-5', type='eighth')
        n5 = note.Note('D5', type='eighth')
        n6 = note.Note('C#5', type='eighth')
        n7 = note.Note('C6', type='eighth')
        n8 = note.Note('B-5', type='eighth')

        m1.append((
            clef1, ts1, note.Rest(type='eighth'), n1, n2,
            note.Rest(type='eighth'), n3, n4,
            spanner.Slur(n3, n4),
            chord.Chord(['E4', 'G4']), note.Rest(type='eighth'),
            chord.Chord(['G4', 'C#5']), note.Rest(type='eighth'),
        ))
        m1.rightBarline = bar.Barline('regular')
        m2.append((
            clef2, ts2, chord.Chord(['D4', 'F4']), note.Rest(type='eighth'),
            chord.Chord(['F4', 'A4']), note.Rest(type='eighth'),
            note.Rest(type='eighth'), n5, n6,
            note.Rest(type='eighth'), n7, n8,
        ))
        m2.rightBarline = bar.Barline('regular')

        p1 = Part()
        p1.append(m1)
        p1.append(spanner.Slur(n1, n2))
        p2 = Part()
        p2.append(spanner.Slur(n5, n6))
        p2.append(spanner.Slur(n7, n8))
        p2.append(m2)
        s = Score()
        s.insert(0, p1)
        s.insert(0, p2)

        s_ = s.partsToVoices(2, permitOneVoicePerPart=True)
        self.assertEqual(len(s_), 1)
        self.assertEqual(len(s_[0].getElementsByClass('Slur')), 3)
        self.assertEqual(len(s_[0]['Slur']), 4)
        self.assertEqual(len(s_[0]), 4)  # 1 measure + 3 slurs
        self.assertIsInstance(s_[0][0], Measure)
        self.assertEqual(s_[0][0][0], clef1)
        self.assertEqual(s_[0][0][1], ts1)
        self.assertEqual(len(s_[0][0].voices), 2)  # 2 voices
        self.assertEqual(len(s_[0][0][2]['Slur']), 1)  # 1 slur inside the first voice
        self.assertEqual(s_[0][0][2]['Slur'][0][0], n3)
        self.assertEqual(s_[0][0][2]['Slur'][0][1], n4)

    def testVoicesToPartsA(self):

        s0 = corpus.parse('bwv66.6')
        # s.show()
        s1 = s0.partsToVoices(2)  # produce two parts each with two voices

        s2 = s1.parts[0].voicesToParts()
        # now a two part score
        self.assertEqual(len(s2.parts), 2)
        # makes sure we have what we started with
        self.assertEqual(len(s2.parts[0].flatten().notesAndRests),
                         len(s0.parts[0].flatten().notesAndRests))

        s1 = s0.partsToVoices(4)  # create one staff with all parts
        self.assertEqual(s1.classes[0], 'Score')  # we get a Score back
        # we have a Score with one part and measures, each with 4 voices
        self.assertEqual(len(s1.parts[0].getElementsByClass(Measure).first().voices), 4)
        # need to access part
        s2 = s1.voicesToParts()  # return to four parts in a score;
        # make sure we have what we started with
        self.assertEqual(len(s2.parts[0].flatten().notesAndRests),
                         len(s0.parts[0].flatten().notesAndRests))
        self.assertEqual(str(list(s2.parts[0].flatten().notesAndRests)),
                         str(list(s0.parts[0].flatten().notesAndRests)))

        self.assertEqual(len(s2.parts[1].flatten().notesAndRests),
                         len(s0.parts[1].flatten().notesAndRests))
        self.assertEqual(str(list(s2.parts[1].flatten().notesAndRests)),
                         str(list(s0.parts[1].flatten().notesAndRests)))

        self.assertEqual(len(s2.parts[2].flatten().notesAndRests),
                         len(s0.parts[2].flatten().notesAndRests))
        self.assertEqual(str(list(s2.parts[2].flatten().notesAndRests)),
                         str(list(s0.parts[2].flatten().notesAndRests)))

        self.assertEqual(len(s2.parts[3].flatten().notesAndRests),
                         len(s0.parts[3].flatten().notesAndRests))
        self.assertEqual(str(list(s2.parts[3].flatten().notesAndRests)),
                         str(list(s0.parts[3].flatten().notesAndRests)))

        # try on a built Stream that has no Measures
        # build a stream
        s0 = Stream()
        v1 = Voice()
        v1.repeatAppend(note.Note('c3'), 4)
        v2 = Voice()
        v2.repeatAppend(note.Note('g4'), 4)
        v3 = Voice()
        v3.repeatAppend(note.Note('b5'), 4)
        s0.insert(0, v1)
        s0.insert(0, v2)
        s0.insert(0, v3)
        # s2.show()
        s1 = s0.voicesToParts()
        self.assertEqual(len(s1.parts), 3)
        # self.assertEqual(len(s1.parts[0].flatten()), len(v1.flatten()))
        self.assertEqual(list(s1.parts[0].flatten()), list(v1.flatten()))

        self.assertEqual(len(s1.parts[1].flatten()), len(v2.flatten()))
        self.assertEqual(list(s1.parts[1].flatten()), list(v2.flatten()))

        self.assertEqual(len(s1.parts[2].flatten()), len(v3.flatten()))
        self.assertEqual(list(s1.parts[2].flatten()), list(v3.flatten()))

        # s1.show()

    def testVoicesToPartsNonNoteElementPropagation(self):
        k = key.Key('E')
        ts = meter.TimeSignature('2/4')
        b1 = bar.Barline('regular')
        b2 = bar.Barline('final')

        s = Score()
        m1 = Measure()  # No voices
        m1.append((k, ts, note.Note(type='half')))
        m1.rightBarline = b1
        m2 = Measure()  # Has voices
        v1 = Voice()
        v2 = Voice()
        v1.append(note.Note(type='half'))
        v2.append(note.Note(type='half'))
        m2.insert(0, v1)
        m2.insert(0, v2)
        m2.rightBarline = b2
        s.append((m1, m2))

        partScore = s.voicesToParts()
        for part in partScore.parts:
            flattenedPart = part.flatten()
            self.assertIn(k, flattenedPart)
            self.assertIn(ts, flattenedPart)
            self.assertIsNotNone(part.getElementsByClass(Measure)[0].rightBarline)
            self.assertIsNotNone(part.getElementsByClass(Measure)[1].rightBarline)

    def testMergeElements(self):
        s1 = Stream()
        s2 = Stream()
        s3 = Stream()

        n1 = note.Note('f#')
        n2 = note.Note('g')
        s1.append(n1)
        s1.append(n2)

        s2.mergeElements(s1)
        self.assertEqual(len(s2), 2)
        self.assertEqual(id(s1[0]), id(s2[0]))
        self.assertEqual(id(s1[1]), id(s2[1]))

        s3.mergeElements(s1, classFilterList=['Rest'])
        self.assertEqual(len(s3), 0)

        s3.mergeElements(s1, classFilterList=['GeneralNote'])
        self.assertEqual(len(s3), 2)

    def testDeepcopySpanners(self):
        n1 = note.Note()
        n2 = note.Note('a4')
        n3 = note.Note('g#4')
        n3.quarterLength = 0.25

        su1 = spanner.Slur(n1, n2)
        s1 = Stream()
        s1.append(n1)
        s1.repeatAppend(n3, 4)
        s1.append(n2)
        s1.insert(su1)

        self.assertIn(s1.notesAndRests[0], s1.spanners[0].getSpannedElements())
        self.assertIn(s1.notesAndRests[-1], s1.spanners[0].getSpannedElements())

        s2 = copy.deepcopy(s1)

        # old relations are still valid
        self.assertEqual(len(s1.spanners), 1)
        self.assertIn(s1.notesAndRests[0], s1.spanners[0].getSpannedElements())
        self.assertIn(s1.notesAndRests[-1], s1.spanners[0].getSpannedElements())

        # new relations exist in new stream.
        self.assertEqual(len(s2.spanners), 1)
        self.assertIn(s2.notesAndRests[0], s2.spanners[0].getSpannedElements())
        self.assertIn(s2.notesAndRests[-1], s2.spanners[0].getSpannedElements())

        self.assertEqual(s2.spanners[0].getSpannedElements(),
                         [s2.notesAndRests[0], s2.notesAndRests[-1]])

        GEX = m21ToXml.GeneralObjectExporter()
        unused_mx = GEX.parse(s2).decode('utf-8')
        # s2.show('t')
        # s2.show()

    def testAddSlurByMelisma(self):
        s = corpus.parse('luca/gloria')
        ex = s.parts[0]
        nStart = None
        nEnd = None

        exFlatNotes = ex.flatten().notesAndRests
        nLast = exFlatNotes[-1]

        for i, n in enumerate(exFlatNotes):
            if i < len(exFlatNotes) - 1:
                nNext = exFlatNotes[i + 1]
            else:
                continue

            if n.lyrics:
                nStart = n
            # if next is a "begin", then this is an "end"
            elif nStart is not None and nNext.lyrics and n.tie is None:
                nEnd = n
            elif nNext is nLast:
                nEnd = n

            if nStart is not None and nEnd is not None:
                # insert in top-most container
                ex.insert(spanner.Slur(nStart, nEnd))
                nStart = None
                nEnd = None
        # ex.show()
        exFlat = ex.flatten()
        melismaByBeat = {}
        for sp in ex.spanners:
            n = sp.getFirst()
            oMin = min(exFlat.elementOffset(e) for e in sp.getSpannedElements())
            oMax = min(exFlat.elementOffset(e) for e in sp.getSpannedElements())
            dur = oMax - oMin
            beatStr = n.beatStr
            if beatStr not in melismaByBeat:
                melismaByBeat[beatStr] = []
            melismaByBeat[beatStr].append(dur)
            # environLocal.printDebug(['start note:', n, 'beat:', beatStr,
            #     'slurred duration:', dur])

        for beatStr in sorted(list(melismaByBeat.keys())):
            unused_avg = sum(melismaByBeat[beatStr]) / len(melismaByBeat[beatStr])
            # environLocal.printDebug(['melisma beat:', beatStr.ljust(6), 'average duration:', avg])

    def testTwoZeroOffset(self):
        p = Part()
        # p.append(instrument.Voice())
        p.append(note.Note('D#4'))
        # environLocal.printDebug([p.offsetMap()])

    def testStripTiesBuiltB(self):
        s1 = Stream()
        s1.append(meter.TimeSignature('4/4'))
        s1.append(note.Note(type='quarter'))
        s1.append(note.Note(type='half'))
        s1.append(note.Note(type='half'))
        s1.append(note.Note(type='half'))
        s1.append(note.Note(type='quarter'))
        s2 = s1.makeNotation()

        self.assertEqual(len(s2.flatten().notesAndRests), 6)
        self.assertEqual(str([n.tie for n in s2.flatten().notesAndRests]),
                         '[None, None, <music21.tie.Tie start>, '
                         + '<music21.tie.Tie stop>, None, None]')
        self.assertEqual([n.quarterLength for n in s2.flatten().notesAndRests],
                         [1.0, 2.0, 1.0, 1.0, 2.0, 1.0])

        s3 = s2.stripTies()
        self.assertEqual(str([n.tie for n in s3.flatten().notesAndRests]),
                         '[None, None, None, None, None]')
        self.assertEqual([n.quarterLength for n in s3.flatten().notesAndRests],
                         [1.0, 2.0, 2.0, 2.0, 1.0])

        first_m_notesAndRests = s3.getElementsByClass(Measure).first().notesAndRests
        self.assertEqual([n.offset for n in first_m_notesAndRests],
                         [0.0, 1.0, 3.0])
        self.assertEqual([n.quarterLength
                            for n in first_m_notesAndRests],
                         [1.0, 2.0, 2.0])
        self.assertEqual([n.beatStr for n in first_m_notesAndRests],
                         ['1', '2', '4'])

        self.assertEqual(
            [n.offset for n in s3.getElementsByClass(Measure)[1].notesAndRests],
            [1.0, 3.0])
        self.assertEqual(
            [n.quarterLength for n in s3.getElementsByClass(Measure)[1].notesAndRests],
            [2.0, 1.0])
        self.assertEqual(
            [n.beatStr for n in s3.getElementsByClass(Measure)[1].notesAndRests],
            ['2', '4'])

        # s3.show()

    def testStripTiesImportedB(self):

        # this file was imported by sibelius and does not have completed ties
        sMonte = corpus.parse('monteverdi/madrigal.4.2.xml')
        s1 = sMonte.parts['#Alto']
        mStream = s1.getElementsByClass(Measure)
        self.assertEqual([n.offset for n in mStream[3].notesAndRests], [0.0])
        self.assertEqual(str([n.tie for n in mStream[3].notesAndRests]),
                         '[<music21.tie.Tie start>]')
        self.assertEqual([n.offset for n in mStream[4].notesAndRests], [0.0, 2.0])
        self.assertEqual(str([n.tie for n in mStream[4].notesAndRests]),
                         '[None, None]')

        # post strip ties; must use matchByPitch
        s2 = s1.stripTies(matchByPitch=True)
        mStream = s2.getElementsByClass(Measure)
        self.assertEqual([n.offset for n in mStream[3].notesAndRests], [0.0])
        self.assertEqual(str([n.tie for n in mStream[3].notesAndRests]), '[None]')

        self.assertEqual([n.offset for n in mStream[4].notesAndRests], [2.0])
        self.assertEqual(str([n.tie for n in mStream[4].notesAndRests]), '[None]')

        self.assertEqual([n.offset for n in mStream[5].notesAndRests],
                         [0.0, 0.5, 1.0, 1.5, 2.0, 3.0])

    def testDerivationA(self):

        s1 = Stream()
        s1.repeatAppend(note.Note(), 10)
        s1.repeatAppend(chord.Chord(), 10)

        # for testing against
        s2 = Stream()

        s3 = s1.notesAndRests.stream()
        self.assertEqual(len(s3), 20)
        # environLocal.printDebug(['s3.derivation.origin', s3.derivation.origin])
        self.assertIs(s3.derivation.origin, s1)
        self.assertIsNot(s3.derivation.origin, s2)

        s4 = s3.getElementsByClass(chord.Chord).stream()
        self.assertEqual(len(s4), 10)
        self.assertIs(s4.derivation.origin, s3)

        # test imported and flat
        s = corpus.parse('bach/bwv66.6')
        p1 = s.parts[0]
        # the part is not derived from anything yet
        self.assertEqual(p1.derivation.origin, None)

        p1Flat = p1.flatten()
        self.assertIs(p1.flatten().derivation.origin, p1)
        self.assertIsNot(p1.flatten().derivation.origin, s)

        p1FlatNotes = p1Flat.notesAndRests.stream()
        self.assertIs(p1FlatNotes.derivation.origin, p1Flat)
        self.assertIsNot(p1FlatNotes.derivation.origin, p1)

        self.assertEqual(list(p1FlatNotes.derivation.chain()), [p1Flat, p1])

        # we cannot do this, as each call to flat could produce a new Stream
        # self.assertIsNot(p1.flatten().notesAndRests.derivation.origin, p1.flatten())

        # chained calls to .derives from can be used
        self.assertIs(p1.flatten().notesAndRests.stream().derivation.origin.derivation.origin, p1)

        # can use rootDerivation to get there faster
        self.assertIs(p1.flatten().notesAndRests.stream().derivation.rootDerivation, p1)

        # this does not work because are taking an item via in index
        # value, and this Measure is not derived from a Part
        self.assertIsNot(p1.getElementsByClass(Measure)[3].flatten().notesAndRests.stream()
                         .derivation.rootDerivation,
                         p1)

        # the root here is the Measure
        self.assertIs(p1.getElementsByClass(Measure)[3].flatten().notesAndRests.stream()
                      .derivation.rootDerivation,
                      p1.getElementsByClass(Measure)[3])

        m4 = p1.measure(4)
        self.assertIs(m4.flatten().notesAndRests.stream().derivation.rootDerivation, m4,
                        list(m4.flatten().notesAndRests.stream().derivation.chain()))

        # part is the root derivation of a measures() call
        mRange = p1.measures(4, 6)
        self.assertEqual(mRange.derivation.rootDerivation, p1)
        self.assertEqual(mRange.flatten().notesAndRests.stream().derivation.rootDerivation, p1)

        self.assertIs(
            s.flatten().getElementsByClass(note.Rest).stream().derivation.rootDerivation,
            s
        )

        # As of v3, we CAN use the activeSite to get the Part from the Measure, as
        # the activeSite was not set when doing the getElementsByClass operation
        self.assertIs(p1.getElementsByClass(Measure)[3].activeSite, p1)

    def testDerivationB(self):
        s1 = Stream()
        s1.repeatAppend(note.Note(), 10)
        s1Flat = s1.flatten()
        self.assertIs(s1Flat.derivation.origin, s1)
        # check what the derivation object thinks its container is
        self.assertIs(s1Flat._derivation.client, s1Flat)

        s2 = copy.deepcopy(s1Flat)
        self.assertIs(s2.derivation.origin, s1Flat)
        self.assertIs(s2.derivation.origin.derivation.origin, s1)
        # check low level attributes
        self.assertIs(s2._derivation.client, s2)

    def testDerivationC(self):
        s = corpus.parse('bach/bwv66.6')
        p1 = s.parts['#Soprano']
        pMeasures = p1.measures(3, 10)
        pMeasuresFlat = pMeasures.flatten()
        pMeasuresFlatNotes = pMeasuresFlat.notesAndRests.stream()
        self.assertEqual(list(pMeasuresFlatNotes.derivation.chain()),
                         [pMeasuresFlat, pMeasures, p1])

    def testDerivationMethodA(self):
        s1 = Stream()
        s1.repeatAppend(note.Note(), 10)
        s1Flat = s1.flatten()
        self.assertIs(s1Flat.derivation.origin, s1)
        self.assertEqual(s1Flat.derivation.method, 'flat')

        s1Elements = s1Flat.getElementsByClass(note.Note).stream()
        self.assertEqual(s1Elements.derivation.method, 'getElementsByClass')

        s1 = converter.parse('tinyNotation: 4/4 C2 D2')
        s1m = s1.makeMeasures()
        self.assertEqual(s1m.derivation.method, 'makeMeasures')
        s1m1 = s1m.measure(1)
        self.assertEqual(s1m1.derivation.origin, None)

    def testContainerHierarchyA(self):
        s = corpus.parse('bach/bwv66.6')
        # the part is not derived from anything yet
        self.assertEqual([str(e.__class__) for e in s[1][2][3].containerHierarchy()],
                         ["<class 'music21.stream.base.Measure'>",
                          "<class 'music21.stream.base.Part'>",
                          "<class 'music21.stream.base.Score'>"])

        # after extraction and changing activeSite, cannot find
        n = s.flatten().notesAndRests[0]
        self.assertEqual([common.classToClassStr(e.__class__) for e in n.containerHierarchy()],
                         ['Score', 'Score'])

        # still cannot get hierarchy
        # self.assertEqual([str(e.__class__) for e in s.parts[0].containerHierarchy()], [])

    def testMakeMeasuresTimeSignatures(self):
        sSrc = Stream()
        sSrc.append(note.Note('C4', type='quarter'))
        sSrc.append(note.Note('D4', type='quarter'))
        sSrc.append(note.Note('E4', type='quarter'))
        sMeasures = sSrc.makeMeasures()
        # added 4/4 here as default
        self.assertEqual(str(sMeasures[0].timeSignature),
                         '<music21.meter.TimeSignature 4/4>')

        # no time signature are in the source
        self.assertEqual(len(sSrc.flatten().getElementsByClass(meter.TimeSignature)), 0)
        # we add one time signature
        sSrc.insert(0.0, meter.TimeSignature('2/4'))
        self.assertEqual(len(sSrc.flatten().getElementsByClass(meter.TimeSignature)), 1)

        sMeasuresTwoFour = sSrc.makeMeasures()
        self.assertEqual(str(sMeasuresTwoFour[0].timeSignature),
                         '<music21.meter.TimeSignature 2/4>')
        self.assertTrue(sMeasuresTwoFour.isSorted)

        # check how many TimeSignatures we have:
        # we should have 1
        self.assertEqual(len(
            sMeasuresTwoFour.flatten().getElementsByClass(meter.TimeSignature)), 1)

    def testDeepcopyActiveSite(self):
        # test that active sites make sense after deepcopying
        s = Stream()
        n = note.Note()
        s.append(n)
        self.assertEqual(id(n.activeSite), id(s))

        # test that elements in stream get their active site properly copied
        s1 = copy.deepcopy(s)
        n1 = s1[0]
        self.assertEqual(id(n1.activeSite), id(s1))

        s = Stream()
        m = Measure()
        n = note.Note()
        m.append(n)
        s.append(m)
        self.assertEqual(id(n.activeSite), id(m))
        self.assertEqual(id(m.activeSite), id(s))

        s1 = copy.deepcopy(s)
        m1 = s1[0]
        n1 = m1[0]
        self.assertEqual(id(n1.activeSite), id(m1))
        self.assertEqual(id(m1.activeSite), id(s1))

        # try imported
        s = corpus.parse('bwv66.6')
        p = s.getElementsByClass(Part).first()  # for test, not .parts, use .iter()
        m = p.iter().getElementsByClass(Measure)[2]  # for test, not .getElementsByClass(Measure)
        rn = m[2]

        self.assertEqual(id(rn.activeSite), id(m))
        self.assertEqual(id(m.activeSite), id(p))
        self.assertEqual(id(p.activeSite), id(s))

        s1 = copy.deepcopy(s)
        p1 = s1[1]
        m1 = p1[2]
        rn1 = m1[2]

        self.assertEqual(id(rn1.activeSite), id(m1))
        self.assertEqual(id(m1.activeSite), id(p1))
        self.assertEqual(id(p1.activeSite), id(s1))

    def testRecurseA(self):
        s = corpus.parse('bwv66.6')
        # default
        rElements = list(s.recurse(includeSelf=True))  # NOTE: list(s.recurse())
        # removes self, while [x for x in s.recurse()] does not.
        self.assertTrue(s in rElements)
        self.assertEqual(len(rElements), 244)

        # rElements = list(s.recurse(streamsOnly=True))
        # self.assertEqual(len(rElements), 45)
        #
        # p1 = rElements[1]
        # m1 = rElements[2]
        # # m = rElements[3]
        # m2 = rElements[4]
        # self.assertIs(p1.activeSite, s)
        # self.assertIs(m1.activeSite, p1)
        # self.assertIs(m2.activeSite, p1)
        #
        #
        # rElements = list(s.recurse(classFilter='KeySignature'))
        # self.assertEqual(len(rElements), 4)
        # # the first elements active site is the measure
        # self.assertEqual(id(rElements[0].activeSite), id(m1))
        #
        # rElements = list(s.recurse(classFilter=['TimeSignature']))
        # self.assertEqual(len(rElements), 4)
        #
        #
        # s = corpus.parse('bwv66.6')
        # m1 = s[2][1]  # cannot use parts here as breaks active site
        # rElements = list(m1.recurse(direction='upward'))
        # self.assertEqual([str(e.classes[0]) for e in rElements], ['Measure',
        #                                                           'Instrument',
        #                                                           'Part',
        #                                                           'Metadata',
        #                                                           'Part',
        #                                                           'Score',
        #                                                           'Part',
        #                                                           'Part',
        #                                                           'StaffGroup',
        #                                                           'Measure',
        #                                                           'Measure',
        #                                                           'Measure',
        #                                                           'Measure',
        #                                                           'Measure',
        #                                                           'Measure',
        #                                                           'Measure',
        #                                                           'Measure',
        #                                                           'Measure'])
        # self.assertEqual(len(rElements), 18)


    def testRecurseB(self):

        s = corpus.parse('madrigal.5.8.rntxt')
        self.assertEqual(len(s['KeySignature']), 1)
        for e in s.recurse(classFilter='KeySignature'):
            e.activeSite.remove(e)
        self.assertEqual(len(s['KeySignature']), 0)

    def testTransposeScore(self):

        s = corpus.parse('bwv66.6')
        p1 = s.parts[0]
        pitch1 = p1.flatten().notesAndRests[0]
        pitch2 = pitch1.transpose('P4', inPlace=False)
        self.assertEqual(str(pitch1), '<music21.note.Note C#>')
        self.assertEqual(str(pitch2), '<music21.note.Note F#>')

        # can now transpose a part alone as is recursive
        p2 = p1.transpose('P4', inPlace=False)
        self.assertEqual(str(p1.flatten().notesAndRests[0]), '<music21.note.Note C#>')
        self.assertEqual(str(p2.flatten().notesAndRests[0]), '<music21.note.Note F#>')

        p2 = p1.flatten().transpose('P4', inPlace=False)
        self.assertEqual(str(p1.flatten().notesAndRests[0]), '<music21.note.Note C#>')
        self.assertEqual(str(p2.flatten().notesAndRests[0]), '<music21.note.Note F#>')

    def testExtendDurationA(self):
        # spanners in this were causing some problems
        from music21.musicxml import testFiles
        # testing a file with dynamics
        a = converter.parse(testFiles.schumannOp48No1)
        unused_b = a.flatten()
        # b= a.flatten().extendDuration(dynamics.Dynamic)

    def testSpannerTransferA(self):
        # test getting spanners after .measures extraction
        s = corpus.parse('corelli/opus3no1/1grave')
        post = s.parts[0].measures(5, 10)

        rbSpanners = post.getElementsByClass(spanner.Slur)
        self.assertEqual(len(rbSpanners), 5)
        # post.parts[0].show()
        unused_firstSpannedElementIds = [id(x) for x in rbSpanners[0].getSpannedElements()]
        unused_secondSpannedElementIds = [id(x) for x in rbSpanners[1].getSpannedElements()]
        # self.assertEqual()
        # TODO: compare ids of new measures

    def testMeasureGrouping(self):

        def parseMeasures(piece):
            # The measures of the piece, for a unique extraction
            voicesMeasures = []
            for part in piece.parts:
                # not all things in a Part are Measure objects; you might
                # also find Instruments and Spanners, for example.
                # thus, filter by Measure first to get the highest measure number
                mMax = part.getElementsByClass(Measure)[-1].number
                # the measures() method returns more than just measures;
                # the Part it returns includes Slurs, that may reside at the
                # Part level
                voicesMeasures.append(part.measures(0, mMax))

            # The problem itself : print a measure to check if len(notes) == 0
            for voice in voicesMeasures:
                # only get the Measures, not everything in the Part
                for meas in voice.getElementsByClass(Measure):
                    # some Measures contain Voices, some do not
                    # do get all notes regardless of Voices, take a flat measure
                    self.assertTrue(meas.flatten().notesAndRests)
        corelli = corpus.parse('corelli/opus3no1/1grave')
        parseMeasures(corelli)
        bach = corpus.parse('bach/bwv7.7')
        parseMeasures(bach)

    def testMakeNotationByMeasuresA(self):
        m = Measure()
        m.repeatAppend(note.Note('c#', quarterLength=0.5), 4)
        m.repeatAppend(note.Note('c', quarterLength=1 / 3), 6)
        # calls makeAccidentals, makeBeams, makeTuplets
        m.makeNotation(inPlace=True)

        # after running, there should only be two displayed accidentals
        self.assertEqual([str(n.pitch.accidental) for n in m.notes],
                         ['sharp', 'sharp',
                          'sharp', 'sharp',
                          'natural', 'None', 'None',
                          'None', 'None', 'None'])
        self.assertEqual([n.pitch.accidental.displayStatus for n in m.notes[:5]],
                         [True, False, False, False, True])

        GEX = m21ToXml.GeneralObjectExporter()
        raw = GEX.parse(m).decode('utf-8')
        self.assertTrue(raw.find(
            '<tuplet bracket="yes" number="1" placement="above" type="start">') > 0, raw)
        self.assertGreater(raw.find('<beam number="1">begin</beam>'), 0, raw)

    def testMakeNotationByMeasuresB(self):
        m = Measure()
        m.repeatAppend(note.Note('c#', quarterLength=0.5), 4)
        m.repeatAppend(note.Note('c', quarterLength=1 / 3), 6)
        GEX = m21ToXml.GeneralObjectExporter()
        raw = GEX.parse(m).decode('utf-8')
        self.assertGreater(raw.find('<beam number="1">begin</beam>'), 0, raw)
        self.assertTrue(raw.find(
            '<tuplet bracket="yes" number="1" placement="above" type="start"') > 0, raw)

    def testHaveAccidentalsBeenMadeA(self):
        m = Measure()
        m.append(note.Note('c#'))
        m.append(note.Note('c'))
        m.append(note.Note('c#'))
        m.append(note.Note('c'))
        # m.show() on musicxml output, accidentals will be made
        self.assertFalse(m.haveAccidentalsBeenMade())
        m.makeAccidentals(inPlace=True)
        self.assertTrue(m.haveAccidentalsBeenMade())

    def testHaveAccidentalsBeenMadeB(self):
        m1 = Measure()
        m1.repeatAppend(note.Note('c#'), 4)
        m2 = Measure()
        m2.repeatAppend(note.Note('c'), 4)
        p = Part()
        p.append([m1, m2])
        # p.show()
        # test result of xml output to make sure a natural has been added
        GEX = m21ToXml.GeneralObjectExporter()
        raw = GEX.parse(p).decode('utf-8')
        self.assertGreater(raw.find('<accidental>natural</accidental>'), 0)
        # make sure original is not changed
        self.assertFalse(p.haveAccidentalsBeenMade())

    def testHaveAccidentalsBeenMadeInVoices(self):
        s = Score()
        s.insert(key.Key('Gb'))
        s.insert(0, note.Note('D-5'))
        s.insert(0, note.Note('D-4'))
        self.assertFalse(s.haveAccidentalsBeenMade())
        post = s.makeNotation()  # makes voices, makes measures, makes accidentals
        self.assertEqual(len(post.recurse().getElementsByClass(Voice)), 2)
        self.assertTrue(post.haveAccidentalsBeenMade())

    def testHaveBeamsBeenMadeA(self):
        m1 = Measure()
        m1.timeSignature = meter.TimeSignature('4/4')
        m1.repeatAppend(note.Note('c#', quarterLength=0.5), 8)
        m2 = Measure()
        m2.repeatAppend(note.Note('c', quarterLength=0.5), 8)
        p = Part()
        p.append([m1, m2])
        self.assertFalse(p.streamStatus.beams)
        p.makeBeams(inPlace=True)
        self.assertTrue(p.streamStatus.beams)

    def testHaveBeamsBeenMadeB(self):
        m1 = Measure()
        m1.timeSignature = meter.TimeSignature('4/4')
        m1.repeatAppend(note.Note('c#', quarterLength=0.5), 8)
        m2 = Measure()
        m2.repeatAppend(note.Note('c', quarterLength=0.5), 8)
        p = Part()
        p.append([m1, m2])
        self.assertFalse(p.streamStatus.beams)
        GEX = m21ToXml.GeneralObjectExporter()
        raw = GEX.parse(p).decode('utf-8')
        # after getting musicxml, make sure that we have not changed the source
        # p.show()
        self.assertFalse(p.streamStatus.beams)
        self.assertGreater(raw.find('<beam number="1">end</beam>'), 0)

    def testFlatCachingA(self):
        s = corpus.parse('bwv66.6')
        flat1 = s.flatten()
        flat2 = s.flatten()
        self.assertEqual(id(flat1), id(flat2))

        flat1.insert(0, note.Note('g'))
        self.assertNotEqual(id(flat1), s.flatten())

    def testFlatCachingB(self):
        sSrc = corpus.parse('bach/bwv13.6.xml')
        sPart = sSrc.getElementById('Alto')
        ts = meter.TimeSignature('6/8')
#         for n in sPart.flatten().notesAndRests:
#             bs = n.beatStr
        # environLocal.printDebug(['calling makeMeasures'])
        sPartFlat = sPart.flatten()
        unused_notesAndRests = sPartFlat.notesAndRests
        # test cache
        sMeasures = sPart.flatten().notesAndRests.stream().makeMeasures(ts)
        target = []
        for n in sMeasures.flatten().notesAndRests:
            target.append(n.beatStr)
        self.assertEqual(target, ['1', '1 2/3', '2 1/3', '1', '1 2/3', '2 1/3', '1',
                                  '1 2/3', '2 1/3', '2 2/3', '1', '1 1/3', '1 2/3',
                                  '2', '2 1/3', '1', '1 2/3', '1', '1 2/3', '2 1/3',
                                  '1', '1 2/3', '2 1/3', '1', '1', '1 2/3', '2 1/3',
                                  '1', '1 2/3', '2 1/3', '1 2/3', '2 1/3', '1', '1 1/3',
                                  '1 2/3', '2', '2 1/3', '2 2/3', '1', '1 1/3', '1 2/3',
                                  '2 1/3', '1', '1 2/3', '2 1/3', '1', '1 1/3', '1 2/3',
                                  '2 1/3', '2 2/3', '1', '1 2/3', '2', '2 1/3'])

    def testFlatCachingC(self):
        qj = corpus.parse('ciconia/quod_jactatur').parts.first()
        unused_idFlat1 = id(qj.flatten())
        # environLocal.printDebug(['idFlat1', idFlat1])

        k1 = qj[key.KeySignature].first()
        qj.flatten().replace(k1, key.KeySignature(-3))

        unused_idFlat2 = id(qj.flatten())
        # environLocal.printDebug(['idFlat2', idFlat2])

        unused_m1 = qj.getElementsByClass(Measure)[1]
        # m1.show('t')
        # m.insert(0, key.KeySignature(5))
        qj[1].insert(0, key.KeySignature(5))
        # qj.coreElementsChanged()
        unused_keySigSearch = qj[key.KeySignature]

        for n in qj.flatten().notes:
            junk = n.getContextByClass(key.KeySignature)
            # print(junk)

        unused_qj2 = qj.invertDiatonic(note.Note('F4'), inPlace=False)
        # q2.measures(1, 2).show('text')

    def testInvertDiatonicQuickSearch(self):
        '''
        doctests sufficiently search invertDiatonic for complex cases,
        but not simple ones.
        '''
        m = Measure()
        m.insert(0, note.Note('G4'))
        m2 = m.invertDiatonic()
        self.assertEqual(m2.recurse().notes[0].nameWithOctave, 'F3')
        m.insert(0, key.Key('G'))
        m3 = m.invertDiatonic()
        self.assertEqual(m3.recurse().notes[0].nameWithOctave, 'F#3')
        m4 = m.invertDiatonic(note.Note('G4'))
        self.assertEqual(m4.recurse().notes[0].nameWithOctave, 'G4')
        m5 = m.invertDiatonic(note.Note('G3'))
        self.assertEqual(m5.recurse().notes[0].nameWithOctave, 'G2')

    def testSemiFlatCachingA(self):

        s = corpus.parse('bwv66.6')
        ssf1 = s.flatten(retainContainers=True)
        ssf2 = s.flatten(retainContainers=True)
        self.assertEqual(id(ssf1), id(ssf2))

        ts = s.parts[0].getElementsByClass(Measure)[3].getContextByClass(meter.TimeSignature)
        self.assertEqual(str(ts), '<music21.meter.TimeSignature 4/4>')
        # environLocal.printDebug(['ts', ts])

        beatStr = s.parts[0].getElementsByClass(Measure)[3].notes[3].beatStr
        self.assertEqual(beatStr, '3')
        # environLocal.printDebug(['beatStr', beatStr])

    def testFlattenUnnecessaryVoicesA(self):
        s = Stream()
        v1 = Voice()
        v2 = Voice()
        s.insert(0, v1)
        s.insert(0, v2)

        self.assertEqual(len(s.voices), 2)
        s.flattenUnnecessaryVoices(inPlace=True)
        # as empty, are removed
        self.assertEqual(len(s.voices), 0)

        # next case: one voice empty, other with notes
        s = Stream()
        v1 = Voice()
        v2 = Voice()
        n1 = note.Note()
        n2 = note.Note()
        v1.insert(10, n1)
        v1.insert(20, n2)

        s.insert(50, v1)  # need to test inclusion of this offset
        s.insert(50, v2)

        self.assertEqual(len(s.voices), 2)
        s.flattenUnnecessaryVoices(inPlace=True)
        # as empty, are removed
        self.assertEqual(len(s.voices), 0)
        self.assertEqual(len(s.notes), 2)
        self.assertEqual(n1.getOffsetBySite(s), 60)
        self.assertEqual(n2.getOffsetBySite(s), 70)

        # last case: two voices with notes
        s = Stream()
        v1 = Voice()
        v2 = Voice()
        n1 = note.Note()
        n2 = note.Note()
        n3 = note.Note()
        v1.insert(10, n1)
        v1.insert(20, n2)
        v2.insert(20, n3)

        s.insert(50, v1)  # need to test inclusion of this offset
        s.insert(50, v2)

        self.assertEqual(len(s.voices), 2)
        s.flattenUnnecessaryVoices(inPlace=True)
        # none are removed by default
        self.assertEqual(len(s.voices), 2)
        # can force
        s.flattenUnnecessaryVoices(force=True, inPlace=True)
        self.assertEqual(len(s.voices), 0)
        self.assertEqual(len(s.notes), 3)

    def testGetElementBeforeOffsetA(self):
        s = Stream()
        n1 = note.Note()
        n2 = note.Note()
        n3 = note.Note()
        s.insert(0, n1)
        s.insert(3, n2)
        s.insert(5, n3)

        self.assertEqual(s.getElementBeforeOffset(5), n2)
        self.assertEqual(s.getElementBeforeOffset(5.1), n3)
        self.assertEqual(s.getElementBeforeOffset(3), n1)
        self.assertEqual(s.getElementBeforeOffset(3.2), n2)
        self.assertEqual(s.getElementBeforeOffset(0), None)
        self.assertEqual(s.getElementBeforeOffset(0.3), n1)

        self.assertEqual(s.getElementBeforeOffset(5, ['Note']), n2)
        self.assertEqual(s.getElementBeforeOffset(0.3, ['GeneralNote']), n1)

    def testGetElementBeforeOffsetB(self):
        s = Stream()
        # fill with clefs to test class matching
        n1 = note.Note()
        n2 = note.Note()
        n3 = note.Note()
        s.insert(0, n1)
        s.insert(0, clef.SopranoClef())
        s.insert(2, clef.BassClef())
        s.insert(3, n2)
        s.insert(3, clef.TrebleClef())
        s.insert(3.1, clef.TenorClef())
        s.insert(5, n3)

        self.assertEqual(s.getElementBeforeOffset(5, ['Note']), n2)
        self.assertEqual(s.getElementBeforeOffset(5.1, ['Note']), n3)
        self.assertEqual(s.getElementBeforeOffset(3, ['Note']), n1)
        self.assertEqual(s.getElementBeforeOffset(3.2, ['Note']), n2)
        self.assertEqual(s.getElementBeforeOffset(0, ['Note']), None)
        self.assertEqual(s.getElementBeforeOffset(0.3, ['Note']), n1)

    def testFinalBarlinePropertyA(self):
        s = Stream()
        m1 = Measure()
        m1.repeatAppend(note.Note(quarterLength=2.0), 2)
        m2 = Measure()
        m2.repeatAppend(note.Note(quarterLength=2.0), 2)
        s.append([m1, m2])

        s.finalBarline = 'dotted'
        self.assertEqual(str(s.getElementsByClass(Measure)[-1].rightBarline),
                         '<music21.bar.Barline type=dotted>')
        self.assertEqual(str(s.finalBarline),
                         '<music21.bar.Barline type=dotted>')

        s.finalBarline = 'final'
        self.assertEqual(str(s.getElementsByClass(Measure)[-1].rightBarline),
                         '<music21.bar.Barline type=final>')

        self.assertEqual(str(s.finalBarline),
                         '<music21.bar.Barline type=final>')
        # s.show()

    def testFinalBarlinePropertyB(self):
        s = corpus.parse('bwv66.6')
        sop = s.parts[0]
        self.assertEqual(str(sop.finalBarline), '<music21.bar.Barline type=final>')
        sop.finalBarline = 'double'
        self.assertEqual(str(sop.finalBarline), '<music21.bar.Barline type=double>')

        # process entire Score
        s.finalBarline = 'tick'
        self.assertEqual(str(s.finalBarline),
                         '[<music21.bar.Barline type=tick>, <music21.bar.Barline type=tick>, '
                         + '<music21.bar.Barline type=tick>, <music21.bar.Barline type=tick>]')

        # can set heterogeneous final barlines
        s.finalBarline = ['final', 'none']
        self.assertEqual(str(s.finalBarline),
                         '[<music21.bar.Barline type=final>, <music21.bar.Barline type=none>, '
                         + '<music21.bar.Barline type=final>, <music21.bar.Barline type=none>]')

    def testSetElementsFromOtherStreamWithEndElements(self):
        b = bar.Barline('double')

        s = Stream()
        s.storeAtEnd(b)

        c = Stream()
        c.elements = s
        self.assertIn(b, s)

    def testStreamElementsComparison(self):
        s1 = Stream()
        s1.repeatAppend(note.Note(), 7)
        n1 = note.Note()
        s1.append(n1)

        s2 = Stream()
        s2.elements = s1
        match = []
        for e in s2.elements:
            match.append(e.getOffsetBySite(s2))
        self.assertEqual(match, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        # have the same object in each stream
        self.assertEqual(id(s2[-1]), id(s1[-1]))

        s3 = Stream()

        s4 = Stream()
        s4.insert(25, n1)  # active site is now changed

        s3.elements = s1.elements
        match = []
        for e in s3.elements:
            match.append(e.getOffsetBySite(s3))
        # this is not desirable but results from setting of last active site
        # before elements assignment
        self.assertEqual(match, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 25.0])

        # s.elements = s1
        s3 = Stream(s1[:])
        match = []
        for e in s3.elements:
            match.append(e.getOffsetBySite(s3))
        self.assertEqual(match, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 25.0])

        # this resets active site, so we get the right offsets on element
        # assignment
        s3.elements = s1
        match = []
        for e in s3.elements:
            match.append(e.getOffsetBySite(s3))
        self.assertEqual(match, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])

        s5 = Stream()
        s5.elements = s1
        match = []
        for e in s5.elements:
            match.append(e.getOffsetBySite(s5))
        self.assertEqual(match, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])

    def testSecondsPropertyA(self):
        # simple case of one tempo
        s = Stream()
        s.insert(0, tempo.MetronomeMark(number=60))
        s.repeatAppend(note.Note(), 60)
        self.assertEqual(s.seconds, 60.0)

        s = Stream()
        s.insert(0, tempo.MetronomeMark(number=90))
        s.repeatAppend(note.Note(), 60)
        self.assertEqual(s.seconds, 40.0)

        s = Stream()
        s.insert(0, tempo.MetronomeMark(number=120))
        s.repeatAppend(note.Note(), 60)
        self.assertEqual(s.seconds, 30.0)

        # changing tempo mid-stream
        s = Stream()
        s.insert(0, tempo.MetronomeMark(number=60))
        s.repeatAppend(note.Note(), 60)
        s.insert(30, tempo.MetronomeMark(number=120))
        # 30 notes at 60, 30 notes at 120
        self.assertEqual(s.seconds, 30.0 + 15.0)

        s = Stream()
        s.insert(0, tempo.MetronomeMark(number=60))
        s.repeatAppend(note.Note(), 60)
        s.insert(15, tempo.MetronomeMark(number=120))
        s.insert(30, tempo.MetronomeMark(number=240))
        s.insert(45, tempo.MetronomeMark(number=480))

        # 15 notes at 60, 15 notes at 120, 15 at 240, 15 at 480
        self.assertEqual(s.seconds, 15.0 + 7.5 + 3.75 + 1.875)

    def testSecondsPropertyB(self):
        s = corpus.parse('bwv66.6')
        sFlat = s.flatten()
        # we have not tempo
        self.assertEqual(len(sFlat.getElementsByClass(tempo.TempoIndication)), 4)
        sFlat.insert(0, tempo.MetronomeMark('adagio'))
        self.assertAlmostEqual(sFlat.seconds, 38.57142857)

        sFlat.removeByClass(tempo.TempoIndication)
        sFlat.insert(0, tempo.MetronomeMark('presto'))
        self.assertAlmostEqual(sFlat.seconds, 11.73913043)

        sFlat.removeByClass(tempo.TempoIndication)
        sFlat.insert(0, tempo.MetronomeMark('prestissimo'))
        self.assertAlmostEqual(sFlat.seconds, 10.38461538)

    def testSecondsPropertyC(self):
        s = Stream()
        m1 = Measure()
        m1.timeSignature = meter.TimeSignature('3/4')
        mm = tempo.MetronomeMark(number=60)
        m1.insert(0, mm)
        m1.insert(note.Note(quarterLength=3))
        s.append(m1)

        m2 = Measure()
        m2.timeSignature = meter.TimeSignature('5/4')
        m2.insert(note.Note(quarterLength=5))
        s.append(m2)

        m3 = Measure()
        m3.timeSignature = meter.TimeSignature('2/4')
        m3.insert(note.Note(quarterLength=2))
        s.append(m3)

        self.assertEqual([m.seconds for m in s.getElementsByClass(Measure)], [3.0, 5.0, 2.0])

        mm.number = 120
        self.assertEqual([m.seconds for m in s.getElementsByClass(Measure)], [1.5, 2.5, 1.0])

        mm.number = 30
        self.assertEqual([m.seconds for m in s.getElementsByClass(Measure)], [6.0, 10.0, 4.0])

    # TODO: New piece with Metronome Mark Boundaries
    # def testMetronomeMarkBoundaries(self):
    #     s = corpus.parse('hwv56/movement2-09.md')
    #     mmBoundaries = s.metronomeMarkBoundaries()
    #     self.assertEqual(str(mmBoundaries),
    #            '[(0.0, 20.0, <music21.tempo.MetronomeMark Largo e piano Quarter=46>)]')

    def testAccumulatedTimeA(self):
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        s.insert([0, tempo.MetronomeMark(number=60)])
        mmBoundaries = s.metronomeMarkBoundaries()
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 0, 1), 1.0)
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 0, 2), 2.0)
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 0, 8), 8.0)

        # changing in the middle of boundary
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        s.insert([0, tempo.MetronomeMark(number=60),
                  4, tempo.MetronomeMark(number=120)])
        mmBoundaries = s.metronomeMarkBoundaries()
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 0, 4), 4.0)
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 4, 8), 2.0)
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 0, 8), 6.0)

    def testAccumulatedTimeB(self):
        # changing in the middle of boundary
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        s.insert([0, tempo.MetronomeMark(number=60),
                  4, tempo.MetronomeMark(number=120),
                  6, tempo.MetronomeMark(number=240)])
        mmBoundaries = s.metronomeMarkBoundaries()
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 0, 4), 4.0)
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 4, 6), 1.0)
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 6, 8), 0.5)
        self.assertEqual(s._accumulatedSeconds(mmBoundaries, 0, 8), 5.5)

    def testSecondsMapA(self):
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        s.insert([0, tempo.MetronomeMark(number=90),
                  4, tempo.MetronomeMark(number=120),
                  6, tempo.MetronomeMark(number=240)])
        self.assertEqual(str(s.metronomeMarkBoundaries()),
                         '[(0.0, 4.0, <music21.tempo.MetronomeMark maestoso Quarter=90>), '
                         + '(4.0, 6.0, <music21.tempo.MetronomeMark animato Quarter=120>), '
                         + '(6.0, 8.0, <music21.tempo.MetronomeMark Quarter=240>)]')

        # not starting
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        s.insert([4, tempo.MetronomeMark(number=120),
                  6, tempo.MetronomeMark(number=240)])
        self.assertEqual(str(s.metronomeMarkBoundaries()),
                         '[(0.0, 4.0, <music21.tempo.MetronomeMark animato Quarter=120>), '
                         + '(4.0, 6.0, <music21.tempo.MetronomeMark animato Quarter=120>), '
                         + '(6.0, 8.0, <music21.tempo.MetronomeMark Quarter=240>)]')

        # none
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        self.assertEqual(str(s.metronomeMarkBoundaries()),
                         '[(0.0, 8.0, <music21.tempo.MetronomeMark animato Quarter=120>)]')

        # Change mid-stream
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        s.insert([6, tempo.MetronomeMark(number=240)])
        self.assertEqual(str(s.metronomeMarkBoundaries()),
                         '[(0.0, 6.0, <music21.tempo.MetronomeMark animato Quarter=120>), '
                         + '(6.0, 8.0, <music21.tempo.MetronomeMark Quarter=240>)]')

        # one at the start of the stream
        s = Stream()
        s.repeatAppend(note.Note(), 8)
        s.insert([0, tempo.MetronomeMark(number=240)])
        self.assertEqual(str(s.metronomeMarkBoundaries()),
                         '[(0.0, 8.0, <music21.tempo.MetronomeMark Quarter=240>)]')

    def testSecondsMapB(self):
        # one start stream
        s = Stream()
        s.repeatAppend(note.Note(), 2)
        s.insert([0, tempo.MetronomeMark(number=60)])

        sMap = s._getSecondsMap()
        sMapStr = '['  # construct string from dict in fixed order
        for ob in sMap:
            sMapStr += ("{'durationSeconds': " + str(ob['durationSeconds'])
                        + ", 'voiceIndex': " + str(ob['voiceIndex'])
                        + ", 'element': " + str(ob['element'])
                        + ", 'offsetSeconds': " + str(ob['offsetSeconds'])
                        + ", 'endTimeSeconds': " + str(ob['endTimeSeconds'])
                        + '}, ')
        sMapStr = sMapStr[0:-2]
        sMapStr += ']'

        self.assertEqual(sMapStr,
                         "[{'durationSeconds': 0.0, 'voiceIndex': None, "
                         + "'element': <music21.tempo.MetronomeMark larghetto Quarter=60>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 0.0}, "
                         + "{'durationSeconds': 1.0, 'voiceIndex': None, "
                         + "'element': <music21.note.Note C>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 1.0}, "
                         + "{'durationSeconds': 1.0, 'voiceIndex': None, "
                         + "'element': <music21.note.Note C>, "
                         + "'offsetSeconds': 1.0, 'endTimeSeconds': 2.0}]")

        s = Stream()
        s.repeatAppend(note.Note(), 2)
        s.insert([0, tempo.MetronomeMark(number=15)])

        sMap = s._getSecondsMap()
        sMapStr = '['  # construct string from dict in fixed order
        for ob in sMap:
            sMapStr += ("{'durationSeconds': " + str(ob['durationSeconds'])
                        + ", 'voiceIndex': " + str(ob['voiceIndex'])
                        + ", 'element': " + str(ob['element'])
                        + ", 'offsetSeconds': " + str(ob['offsetSeconds'])
                        + ", 'endTimeSeconds': " + str(ob['endTimeSeconds'])
                        + '}, ')
        sMapStr = sMapStr[0:-2]
        sMapStr += ']'

        self.assertEqual(str(sMapStr),
                         "[{'durationSeconds': 0.0, 'voiceIndex': None, "
                         + "'element': <music21.tempo.MetronomeMark larghissimo Quarter=15>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 0.0}, "
                         + "{'durationSeconds': 4.0, 'voiceIndex': None, "
                         + "'element': <music21.note.Note C>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 4.0}, "
                         + "{'durationSeconds': 4.0, 'voiceIndex': None, "
                         + "'element': <music21.note.Note C>, "
                         + "'offsetSeconds': 4.0, 'endTimeSeconds': 8.0}]")

        s = Stream()
        s.repeatAppend(note.Note(), 2)
        s.insert([0, tempo.MetronomeMark(number=15),
                  1, tempo.MetronomeMark(number=60)])

        sMap = s._getSecondsMap()
        sMapStr = '['  # construct string from dict in fixed order  # TODO: use OrderedDict.
        for ob in sMap:
            sMapStr += ("{'durationSeconds': " + str(ob['durationSeconds'])
                        + ", 'voiceIndex': " + str(ob['voiceIndex'])
                        + ", 'element': " + str(ob['element'])
                        + ", 'offsetSeconds': " + str(ob['offsetSeconds'])
                        + ", 'endTimeSeconds': " + str(ob['endTimeSeconds'])
                        + '}, ')
        sMapStr = sMapStr[0:-2]
        sMapStr += ']'

        self.assertEqual(sMapStr,
                         "[{'durationSeconds': 0.0, 'voiceIndex': None, "
                         + "'element': <music21.tempo.MetronomeMark larghissimo Quarter=15>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 0.0}, "
                         + "{'durationSeconds': 4.0, 'voiceIndex': None, "
                         + "'element': <music21.note.Note C>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 4.0}, "
                         + "{'durationSeconds': 0.0, 'voiceIndex': None, "
                         + "'element': <music21.tempo.MetronomeMark larghetto Quarter=60>, "
                         + "'offsetSeconds': 4.0, 'endTimeSeconds': 4.0}, "
                         + "{'durationSeconds': 1.0, 'voiceIndex': None, "
                         + "'element': <music21.note.Note C>, "
                         + "'offsetSeconds': 4.0, 'endTimeSeconds': 5.0}]")

        s = Stream()
        s.append(note.Note(quarterLength=2.0))
        s.insert([0, tempo.MetronomeMark(number=15),
                  1, tempo.MetronomeMark(number=60)])

        sMap = s._getSecondsMap()
        sMapStr = '['  # construct string from dict in fixed order  # TODO: use OrderedDict.
        for ob in sMap:
            sMapStr += ("{'durationSeconds': " + str(ob['durationSeconds'])
                        + ", 'voiceIndex': " + str(ob['voiceIndex'])
                        + ", 'element': " + str(ob['element'])
                        + ", 'offsetSeconds': " + str(ob['offsetSeconds'])
                        + ", 'endTimeSeconds': " + str(ob['endTimeSeconds'])
                        + '}, ')
        sMapStr = sMapStr[0:-2]
        sMapStr += ']'

        self.maxDiff = None
        self.assertEqual(sMapStr,
                         "[{'durationSeconds': 0.0, 'voiceIndex': None, "
                         + "'element': <music21.tempo.MetronomeMark larghissimo Quarter=15>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 0.0}, "
                         + "{'durationSeconds': 5.0, 'voiceIndex': None, "
                         + "'element': <music21.note.Note C>, "
                         + "'offsetSeconds': 0.0, 'endTimeSeconds': 5.0}, "
                         + "{'durationSeconds': 0.0, 'voiceIndex': None, "
                         + "'element': <music21.tempo.MetronomeMark larghetto Quarter=60>, "
                         + "'offsetSeconds': 4.0, 'endTimeSeconds': 4.0}]")

    def testPartDurationA(self):
        # s= corpus.parse('bach/bwv7.7')
        p1 = Part()
        p1.append(note.Note(quarterLength=72))
        p2 = Part()
        p2.append(note.Note(quarterLength=72))

        sNew = Score()
        sNew.append(p1)
        self.assertEqual(str(sNew.duration), '<music21.duration.Duration 72.0>')
        self.assertEqual(sNew.duration.quarterLength, 72.0)
        sNew.append(p2)
        self.assertEqual(sNew.duration.quarterLength, 144.0)

        # sPost = sNew.chordify()
        # sPost.show()

    def testPartDurationB(self):
        s = corpus.parse('bach/bwv66.6')
        sNew = Score()
        sNew.append(s.parts[0])
        self.assertEqual(str(s.parts[0].duration), '<music21.duration.Duration 36.0>')
        self.assertEqual(str(sNew.duration), '<music21.duration.Duration 36.0>')
        self.assertEqual(sNew.duration.quarterLength, 36.0)
        sNew.append(s.parts[1])
        self.assertEqual(sNew.duration.quarterLength, 72.0)

    def testChordifyTagPartA(self):
        p1 = Part()
        p1.id = 'a'
        p1.repeatAppend(note.Note('g4', quarterLength=2), 6)
        p2 = Part()
        p2.repeatAppend(note.Note('c4', quarterLength=3), 4)
        p2.id = 'b'

        s = Score()
        s.insert(0, p1)
        s.insert(0, p2)
        post = s.chordify(addPartIdAsGroup=True, removeRedundantPitches=False)
        self.assertEqual(len(post.flatten().notes), 8)
        # test that each note has its original group
        idA = []
        idB = []
        for c in post.flatten().getElementsByClass(chord.Chord):
            for p in c.pitches:
                if 'a' in p.groups:
                    idA.append(p.name)
                if 'b' in p.groups:
                    idB.append(p.name)
        self.assertEqual(idA, ['G', 'G', 'G', 'G', 'G', 'G', 'G', 'G'])
        self.assertEqual(idB, ['C', 'C', 'C', 'C', 'C', 'C', 'C', 'C'])

    def testChordifyTagPartB(self):
        s = corpus.parse('bwv66.6')
        idSoprano = []
        idAlto = []
        idTenor = []
        idBass = []

        post = s.chordify(addPartIdAsGroup=True, removeRedundantPitches=False)
        for c in post.flatten().getElementsByClass(chord.Chord):
            for p in c.pitches:
                if 'Soprano' in p.groups:
                    idSoprano.append(p.name)
                if 'Alto' in p.groups:
                    idAlto.append(p.name)
                if 'Tenor' in p.groups:
                    idTenor.append(p.name)
                if 'Bass' in p.groups:
                    idBass.append(p.name)

        self.assertEqual(idSoprano, ['C#', 'B', 'A', 'B', 'C#', 'E', 'C#', 'C#', 'B',
                                     'B', 'A', 'C#', 'A', 'B', 'G#', 'G#', 'F#', 'A',
                                     'B', 'B', 'B', 'B', 'F#', 'F#', 'E', 'A', 'A',
                                     'B', 'B', 'C#', 'C#', 'A', 'B', 'C#', 'A', 'G#',
                                     'G#', 'F#', 'F#', 'G#', 'F#', 'F#', 'F#', 'F#',
                                     'F#', 'F#', 'F#', 'F#', 'F#', 'E#', 'F#'])

        self.assertEqual(idAlto, ['E', 'E', 'F#', 'E', 'E', 'E', 'E', 'A', 'G#',
                                  'G#', 'E', 'G#', 'F#', 'G#', 'E#', 'E#', 'C#',
                                  'F#', 'F#', 'F#', 'E', 'E', 'D#', 'D#', 'C#',
                                  'C#', 'F#', 'E', 'E', 'E', 'A', 'F#', 'F#',
                                  'G#', 'F#', 'F#', 'E#', 'F#', 'F#', 'C#',
                                  'C#', 'D', 'E', 'E', 'D', 'C#', 'B', 'C#',
                                  'D', 'D', 'C#'])

        # length should be the same
        self.assertEqual(len(idSoprano), len(idAlto))

    def testTransposeByPitchA(self):
        i1 = instrument.EnglishHorn()  # -p5
        i2 = instrument.Clarinet()  # -M2

        p1 = Part()
        p1.repeatAppend(note.Note('C4'), 4)
        p1.insert(0, i1)
        p1.insert(2, i2)
        p1.makeMeasures(inPlace=True)
        p2 = Part()
        p2.repeatAppend(note.Note('C4'), 4)
        p2.insert(0, i2)
        p2.makeMeasures(inPlace=True)
        s = Score()
        s.insert(0, p1)
        s.insert(0, p2)

        test = p1._transposeByInstrument(inPlace=False, reverse=True)
        self.assertEqual([str(p) for p in test.pitches], ['G4', 'G4', 'D4', 'D4'])

        # declare that at written pitch
        p1.atSoundingPitch = False
        test = p1.toSoundingPitch(inPlace=False)
        # all transpositions should be downward
        self.assertEqual([str(p) for p in test.pitches], ['F3', 'F3', 'B-3', 'B-3'])

        # declare that at written pitch
        p1.atSoundingPitch = False
        test = p1.toWrittenPitch(inPlace=False)

        # no change; already at written
        self.assertEqual([str(p) for p in test.pitches], ['C4', 'C4', 'C4', 'C4'])

        # declare that at sounding pitch
        p1.atSoundingPitch = True
        # no change happens
        test = p1.toSoundingPitch(inPlace=False)
        self.assertEqual([str(p) for p in test.pitches], ['C4', 'C4', 'C4', 'C4'])

        # declare at sounding pitch
        p1.atSoundingPitch = True
        # reverse intervals; app pitches should be upward
        test = p1.toWrittenPitch(inPlace=False)
        self.assertEqual([str(p) for p in test.pitches], ['G4', 'G4', 'D4', 'D4'])
        self.assertFalse(test.atSoundingPitch)

        # test on a complete score
        s.parts[0].atSoundingPitch = False
        s.parts[1].atSoundingPitch = False
        test = s.toSoundingPitch(inPlace=False)
        self.assertEqual([str(p) for p in test.parts[0].pitches], ['F3', 'F3', 'B-3', 'B-3'])
        self.assertEqual([str(p) for p in test.parts[1].pitches], ['B-3', 'B-3', 'B-3', 'B-3'])

        # test same in place
        self.assertEqual(s.parts[0].atSoundingPitch, False)
        self.assertEqual(s.parts[1].atSoundingPitch, False)
        s.toSoundingPitch(inPlace=True)
        self.assertEqual([str(p) for p in s.parts[0].pitches], ['F3', 'F3', 'B-3', 'B-3'])
        self.assertEqual([str(p) for p in s.parts[1].pitches], ['B-3', 'B-3', 'B-3', 'B-3'])

        # mixture of atSoundingPitch=True and False; and unknown top-level
        s.atSoundingPitch = 'unknown'
        s.parts[0].atSoundingPitch = True
        s.parts[1].atSoundingPitch = False
        for measure in s.parts[1][Measure]:
            # This was made True, above, and we have no way of knowing we need to
            # transpose again unless we say so
            measure.atSoundingPitch = False
        s.toWrittenPitch(inPlace=True)
        self.assertEqual([str(p) for p in s.parts[0].pitches], ['C4', 'C4', 'C4', 'C4'])
        self.assertEqual([str(p) for p in s.parts[1].pitches], ['B-3', 'B-3', 'B-3', 'B-3'])

    def testTransposeByPitchB(self):
        from music21.musicxml import testPrimitive

        s = converter.parse(testPrimitive.transposingInstruments72a)
        self.assertFalse(s.parts[0].atSoundingPitch)
        self.assertFalse(s.parts[1].atSoundingPitch)

        self.assertEqual(str(s.parts[0].getElementsByClass(instrument.Instrument)[0].transposition),
                         '<music21.interval.Interval M-2>')
        self.assertEqual(str(s.parts[1].getElementsByClass(instrument.Instrument)[0].transposition),
                         '<music21.interval.Interval M-6>')

        # Set each part's first note's natural to be visible, to test that it will remain so
        # after transposition
        for p in s.parts:
            firstPitch = p.pitches[0]
            self.assertIsNone(firstPitch.accidental)
            firstPitch.accidental = 0
            firstPitch.accidental.displayStatus = True

        self.assertEqual([str(p) for p in s.parts[0].pitches],
                         ['D4', 'E4', 'F#4', 'G4', 'A4', 'B4', 'C#5', 'D5'])
        self.assertEqual([None if p.accidental is None else p.accidental.displayStatus
                            for p in s.parts[0].pitches],
                         [True, None, False, None, None, None, False, None])
        self.assertEqual([str(p) for p in s.parts[1].pitches],
                         ['A4', 'B4', 'C#5', 'D5', 'E5', 'F#5', 'G#5', 'A5'])
        self.assertEqual([None if p.accidental is None else p.accidental.displayStatus
                            for p in s.parts[1].pitches],
                         [True, None, False, None, None, False, False, None])

        self.assertEqual(s.atSoundingPitch, 'unknown')
        s.toSoundingPitch(inPlace=True, preserveAccidentalDisplay=True)

        self.assertEqual([str(p) for p in s.parts[0].pitches],
                         ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'])
        self.assertEqual([None if p.accidental is None else p.accidental.displayStatus
                            for p in s.parts[0].pitches],
                         [True, None, None, None, None, None, None, None])
        self.assertEqual([str(p) for p in s.parts[1].pitches],
                         ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'])
        self.assertEqual([None if p.accidental is None else p.accidental.displayStatus
                            for p in s.parts[1].pitches],
                         [True, None, None, None, None, None, None, None])

    def testTransposeByPitchC(self):
        p = converter.parse('tinyNotation: c1 d1')
        p.insert(0, instrument.Horn())
        s = Score(p)
        s.atSoundingPitch = True
        self.assertEqual(p.atSoundingPitch, 'unknown')

        # Following case fails because we check sites, not containerHierarchy
        # so the only site is the Part, which is 'unknown' and raises StreamException
        # m = p.measure(1)
        # m.toWrittenPitch(inPlace=True)
        # self.assertEqual(m.notes[0].nameWithOctave, 'G4')

        # Can still perform toWrittenPitch by getting the value of atSoundingPitch
        # from the score
        p.toWrittenPitch(inPlace=True)
        self.assertEqual(p.flatten().notes[0].nameWithOctave, 'G4')

    def testExtendTiesA(self):
        s = Stream()
        s.append(note.Note('g4'))
        s.append(chord.Chord(['c3', 'g4', 'a5']))
        s.append(note.Note('a5'))
        s.append(chord.Chord(['c4', 'a5']))
        s.extendTies()
        post = []
        for n in s.flatten().notesAndRests:
            if isinstance(n, chord.Chord):
                post.append([repr(q.tie) for q in n])
            else:
                post.append(repr(n.tie))
        self.assertEqual(post,
                         ['<music21.tie.Tie start>',
                          ['None',
                           '<music21.tie.Tie stop>',
                           '<music21.tie.Tie start>'
                           ],
                          '<music21.tie.Tie continue>',
                           ['None',
                            '<music21.tie.Tie stop>'
                            ]
                          ])

    def testExtendTiesB(self):
        self.maxDiff = None

        s = corpus.parse('bwv66.6')
        sChords = s.measures(9, 9).chordify()
        sChords.extendTies()
        post = []
        for ch in sChords.flatten().getElementsByClass(chord.Chord):
            post.append([repr(n.tie) for n in ch])

        self.assertEqual(post,
                         [['<music21.tie.Tie start>',
                           '<music21.tie.Tie start>',
                           '<music21.tie.Tie continue>'],
                          ['<music21.tie.Tie stop>',
                           '<music21.tie.Tie continue>',
                           'None',
                           '<music21.tie.Tie continue>'],
                          ['<music21.tie.Tie start>',
                           '<music21.tie.Tie continue>',
                           '<music21.tie.Tie start>',
                           '<music21.tie.Tie stop>'],
                          ['<music21.tie.Tie stop>',
                           '<music21.tie.Tie stop>',
                           '<music21.tie.Tie stop>',
                           'None'],
                          ['None', 'None', 'None', 'None']]
                         )
        # sChords.show()

    def testInsertIntoNoteOrChordA(self):
        s = Stream()
        s.repeatAppend(note.Note('d4'), 8)
        s.insertIntoNoteOrChord(3, note.Note('g4'))
        self.assertEqual([repr(e) for e in s],
                         ['<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.chord.Chord D4 G4>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>'])

        s.insertIntoNoteOrChord(3, note.Note('b4'))
        self.assertEqual([repr(e) for e in s],
                         ['<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.chord.Chord D4 G4 B4>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>'])

        s.insertIntoNoteOrChord(5, note.Note('b4'))
        self.assertEqual([repr(e) for e in s],
                         ['<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.chord.Chord D4 G4 B4>',
                          '<music21.note.Note D>',
                          '<music21.chord.Chord D4 B4>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>'])

        s.insertIntoNoteOrChord(5, chord.Chord(['c5', 'e-5']))
        self.assertEqual([repr(e) for e in s],
                         ['<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>',
                          '<music21.chord.Chord D4 G4 B4>',
                          '<music21.note.Note D>',
                          '<music21.chord.Chord D4 B4 C5 E-5>',
                          '<music21.note.Note D>',
                          '<music21.note.Note D>'])
        # s.show('text')

    def testInsertIntoNoteOrChordB(self):
        s = Stream()
        s.repeatAppend(chord.Chord(['c4', 'e4', 'g4']), 8)

        s.insertIntoNoteOrChord(5, note.Note('b4'))
        s.insertIntoNoteOrChord(3, note.Note('b4'))
        s.insertIntoNoteOrChord(6, chord.Chord(['d5', 'e-5', 'b-5']))

        self.assertEqual([repr(e) for e in s],
                         ['<music21.chord.Chord C4 E4 G4>',
                          '<music21.chord.Chord C4 E4 G4>',
                          '<music21.chord.Chord C4 E4 G4>',
                          '<music21.chord.Chord C4 E4 G4 B4>',
                          '<music21.chord.Chord C4 E4 G4>',
                          '<music21.chord.Chord C4 E4 G4 B4>',
                          '<music21.chord.Chord C4 E4 G4 D5 E-5 B-5>',
                          '<music21.chord.Chord C4 E4 G4>'])

    def testSortingAfterInsertA(self):
        import math

        s = corpus.parse('bwv66.6')
        # s.show()
        p = s.parts[0]
        for m in p.getElementsByClass(Measure):
            for n in m.notes:
                targetOffset = n.getOffsetBySite(m)
                if targetOffset != math.floor(targetOffset):
                    # remove all offbeats
                    r = note.Rest(quarterLength=n.quarterLength)
                    m.remove(n)
                    m.insert(targetOffset, r)

        # not sure what changed, but hidden 8th beams otherwise stay in place.
        p.makeBeams(inPlace=True)
        # if we iterate, we get a sorted version
        # self.assertEqual([str(n) for n in p.flatten().notesAndRests], [])

        # when we just call show(), we were not getting a sorted version;
        # this was due to making the stream immutable before sorting
        # this is now fixed

        # m. 3
        match = '''      <note>
        <pitch>
          <step>A</step>
          <octave>4</octave>
        </pitch>
        <duration>5040</duration>
        <type>eighth</type>
        <stem>up</stem>
      </note>
      <note>
        <rest/>
        <duration>5040</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch>
          <step>G</step>
          <alter>1</alter>
          <octave>4</octave>
        </pitch>
        <duration>10080</duration>
        <type>quarter</type>
        <stem>up</stem>
      </note>
      <note>'''
        GEX = m21ToXml.GeneralObjectExporter()
        originalRaw = GEX.parse(p).decode('utf-8')
        match = match.replace(' ', '')
        match = match.replace('\n', '')
        raw = originalRaw.replace(' ', '')
        raw = raw.replace('\n', '')
        self.assertEqual(raw.find(match) > 0, True, originalRaw)

    def testInvertDiatonicA(self):
        # TODO: Check results

        qj = corpus.parse('ciconia/quod_jactatur').parts[0]

        k1 = qj.flatten().getElementsByClass(key.KeySignature)[0]
        qj.flatten().replace(k1, key.KeySignature(-3))
        qj.getElementsByClass(Measure)[1].insert(0, key.KeySignature(5))
        unused_qj2 = qj.invertDiatonic(note.Note('F4'), inPlace=False)

    def testMeasuresA(self):
        s = corpus.parse('bwv66.6')
        ex = s.parts[0].measures(3, 6)

        self.assertEqual(str(ex.flatten().getElementsByClass(clef.Clef)[0]),
                         '<music21.clef.TrebleClef>')
        self.assertEqual(str(ex.flatten().getElementsByClass(instrument.Instrument)[0]),
                         'P1: Soprano: Instrument 1')

        # check that we have the exact same Measure instance
        mTarget = s.parts[0].getElementsByClass(Measure)[3]
        self.assertEqual(id(ex.getElementsByClass(Measure)[0]), id(mTarget))

        for m in ex.getElementsByClass(Measure):
            for n in m.notes:
                if n.name == 'B':
                    o = n.getOffsetBySite(m)
                    m.remove(n)
                    r = note.Rest(quarterLength=n.quarterLength)
                    m.insert(o, r)
        # s.parts[0].show()
        self.assertEqual(len(ex[note.Rest]), 5)

    def testMeasuresB(self):
        s = corpus.parse('luca/gloria')
        y = s.measures(50, 90)

        self.assertEqual(len(
            y.parts[0].flatten().getElementsByClass(meter.TimeSignature)), 2)
        # make sure that ts is being found in musicxml score generation
        # as it is in the Part, and not the Measure, this req an extra check
        GEX = m21ToXml.GeneralObjectExporter()
        raw = GEX.parse(y.parts[0]).decode('utf-8')

        match = '''        <time>
          <beats>2</beats>
          <beat-type>4</beat-type>
        </time>
        '''
        raw = raw.replace(' ', '')
        raw = raw.replace('\n', '')
        match = match.replace(' ', '')
        match = match.replace('\n', '')

        self.assertGreater(raw.find(match), 0)

    def testMeasuresC(self):
        s = corpus.parse('bwv66.6')
        ex = s.parts[0].measures(3, 6)
        for n in list(ex.recurse(classFilter=['Note'])):
            if n.name == 'B':  # should do a list(recurse()) because manipulating
                o = n.offset   # the stream while iterating.
                site = n.activeSite
                n.activeSite.remove(n)
                r = note.Rest(quarterLength=n.quarterLength)
                site.insert(o, r)
        self.assertEqual(len(ex[note.Rest]), 5)
        # ex.show()

    def testMeasuresSuffix(self):
        p = Part()
        m1 = Measure(number=1)
        m2a = Measure(number='2a')
        m2b = Measure(number='2b')
        m3 = Measure(number=3)
        p.append(m1)
        p.append(m2a)
        p.append(m2b)
        p.append(m3)

        def numM(p_excerpt):
            return len(p_excerpt.getElementsByClass(Measure))

        mm1 = p.measures(1, '2a')
        self.assertEqual(numM(mm1), 2)
        self.assertIn(m1, mm1)
        self.assertIn(m2a, mm1)

        mm2 = p.measures('2a', '2b')
        self.assertEqual(numM(mm2), 2)
        self.assertIn(m2a, mm2)
        self.assertIn(m2b, mm2)

        mm3 = p.measures('2a', 3)
        self.assertEqual(numM(mm3), 3)
        self.assertIn(m2a, mm3)
        self.assertIn(m2b, mm3)
        self.assertIn(m3, mm3)

        mm4 = p.measures('2b', 3)
        self.assertEqual(numM(mm4), 2)
        self.assertIn(m2b, mm4)
        self.assertIn(m3, mm4)

        mm5 = p.measures(1, 3)
        self.assertEqual(numM(mm5), 4)
        self.assertIn(m1, mm5)
        self.assertIn(m2a, mm5)
        self.assertIn(m2b, mm5)
        self.assertIn(m3, mm5)

    def testChordifyF(self):
        # testing chordify handling of triplets
        from music21.musicxml import testPrimitive

        # TODO: there are still errors in this chordify output
        s = converter.parse(testPrimitive.triplets01)
        # s.parts[0].show()
        self.maxDiff = None
        self.assertMultiLineEqual(
            s.parts[0].getElementsByClass(Measure)[0]._reprText(addEndTimes=True,
                                                                  useMixedNumerals=True),
            '''{0 - 0} <music21.layout.SystemLayout>
{0 - 0} <music21.clef.TrebleClef>
{0 - 0} <music21.tempo.MetronomeMark Quarter=120 (playback only)>
{0 - 0} <music21.key.Key of B- major>
{0 - 0} <music21.meter.TimeSignature 4/4>
{0 - 2/3} <music21.note.Note B->
{2/3 - 1 1/3} <music21.note.Note C>
{1 1/3 - 2} <music21.note.Note B->
{2 - 4} <music21.note.Note A>''')
        self.assertMultiLineEqual(
            s.parts[1].getElementsByClass(Measure)[0]._reprText(addEndTimes=True),
            '''{0.0 - 0.0} <music21.clef.BassClef>
{0.0 - 0.0} <music21.tempo.MetronomeMark Quarter=120 (playback only)>
{0.0 - 0.0} <music21.key.Key of B- major>
{0.0 - 0.0} <music21.meter.TimeSignature 4/4>
{0.0 - 4.0} <music21.note.Note B->''')
        chords = s.chordify()
        m1 = chords.getElementsByClass(Measure)[0]
        self.assertMultiLineEqual(m1._reprText(addEndTimes=True, useMixedNumerals=True),
                                  '''{0 - 0} <music21.layout.SystemLayout>
{0 - 0} <music21.clef.TrebleClef>
{0 - 0} <music21.tempo.MetronomeMark Quarter=120 (playback only)>
{0 - 0} <music21.key.Key of B- major>
{0 - 0} <music21.meter.TimeSignature 4/4>
{0 - 2/3} <music21.chord.Chord B-2 B-4>
{2/3 - 1 1/3} <music21.chord.Chord B-2 C5>
{1 1/3 - 2} <music21.chord.Chord B-2 B-4>
{2 - 4} <music21.chord.Chord B-2 A4>''')
        match = [([str(p) for p in n.pitches],
                  str(round(float(n.offset), 2)),
                  str(round(float(n.quarterLength), 3))) for n in m1.notes]
        self.assertEqual(
            str(match),
            "[(['B-2', 'B-4'], '0.0', '0.667'), "
            + "(['B-2', 'C5'], '0.67', '0.667'), "
            + "(['B-2', 'B-4'], '1.33', '0.667'), "
            + "(['B-2', 'A4'], '2.0', '2.0')]")

        # chords.show()
        GEX = m21ToXml.GeneralObjectExporter()
        raw = GEX.parse(m1).decode('utf-8')
        # there should only be 2 tuplet indications in the produced chords: start and stop
        self.assertEqual(raw.count('<tuplet '), 2, raw)
        # pitch grouping in measure index 1 was not allocated properly
        # for c in chords.getElementsByClass(chord.Chord):
        #    self.assertEqual(len(c), 2)

    def testChordifyG(self):
        # testing a problem in triplets in makeChords
        s = Stream()
        s.repeatAppend(note.Note('G4', quarterLength=1 / 3), 6)
        s.insert(0, note.Note('C4', quarterLength=2))
        chords = s.chordify()
        # s.chordify().show('t')
        for c in chords.getElementsByClass(chord.Chord):
            self.assertEqual(len(c), 2)

        # try with small divisions
        s = Stream()
        s.repeatAppend(note.Note('G4', quarterLength=1 / 6), 12)
        s.insert(0, note.Note('C4', quarterLength=2))
        chords = s.chordify()
        # s.chordify().show('t')
        for c in chords.getElementsByClass(chord.Chord):
            self.assertEqual(len(c), 2)

        s = Stream()
        s.repeatAppend(note.Note('G4', quarterLength=1 / 12), 24)
        s.insert(0, note.Note('C4', quarterLength=2))
        chords = s.chordify()
        # s.chordify().show('t')
        for c in chords.getElementsByClass(chord.Chord):
            self.assertEqual(len(c), 2)

        s = Stream()
        s.repeatAppend(note.Note('G4', quarterLength=1 / 24), 48)
        s.insert(0, note.Note('C4', quarterLength=2))
        chords = s.chordify()
        # s.chordify().show('t')
        for c in chords.getElementsByClass(chord.Chord):
            self.assertEqual(len(c), 2)

    def testMakeVoicesA(self):
        s = Stream()
        s.repeatAppend(note.Note('d-4', quarterLength=1), 8)
        s.insert(0, note.Note('C4', quarterLength=8))
        s.makeVoices(inPlace=True)
        self.assertEqual(len(s.voices), 2)
        self.assertEqual(len(s.voices[0]), 8)
        self.assertEqual(len(s.voices[1]), 1)

        # s.show()

    def testMakeVoicesB(self):
        s = corpus.parse('bwv66.6')
        # s.measures(6, 7).show()
        sMeasures = s.measures(6, 7)
        sFlatVoiced = sMeasures.flatten().makeVoices(inPlace=False)
        # sFlatVoiced.show('t')
        # sFlatVoiced.show()
        self.assertEqual(len(sMeasures.flatten().notes), len(sFlatVoiced.flatten().notes))
        self.assertEqual(sMeasures.flatten().highestTime,
                         sFlatVoiced.flatten().notes.stream().highestTime)
        self.assertEqual(len(sFlatVoiced.voices), 4)

    def testSplitAtQuarterLengthA(self):
        def getS():
            ss = Measure()
            ss.append(note.Note('a', quarterLength=1))
            ss.append(note.Note('b', quarterLength=2))
            ss.append(note.Note('c', quarterLength=1))
            return ss

        s = getS()
        l, r = s.splitAtQuarterLength(2, retainOrigin=True)
        # if retain origin is true, l is the original
        self.assertIs(l, s)
        self.assertEqual(l.highestTime, 2)
        self.assertEqual(len(l.notes), 2)
        self.assertEqual(r.highestTime, 2)
        self.assertEqual(len(r.notes), 2)

        sPost = Stream()
        sPost.append(l)
        sPost.append(r)

        s = getS()
        l2, r2 = s.splitAtQuarterLength(2, retainOrigin=False)
        self.assertIsNot(l2, s)
        self.assertEqual(l2.highestTime, l.highestTime)
        self.assertEqual(len(l2), len(l))
        self.assertEqual(len(r2.notes), 2)

        s = getS()
        l3, r3 = s.splitAtQuarterLength(5)
        self.assertEqual(len(l3.notes), 3)
        self.assertEqual(len(r3), 0, r3.elements)

        s = getS()
        s.insert(0, meter.TimeSignature('2/2'))
        l4, r4 = s.splitAtQuarterLength(5)
        self.assertEqual(len(l4), 4)
        self.assertEqual(len(r4), 1)
        self.assertIsInstance(r4[0], meter.TimeSignature)
        self.assertEqual(r4[0].ratioString, '2/2')


    def testSplitAtQuarterLengthB(self):
        '''
        Test if recursive calls work over voices in a Measure
        '''
        m1 = Measure()
        v1 = Voice()
        v1.repeatAppend(note.Note('g4', quarterLength=2), 3)
        v2 = Voice()
        v2.repeatAppend(note.Note(quarterLength=6), 1)
        m1.insert(0, v1)
        m1.insert(0, v2)

        # m1.show()
        mLeft, mRight = m1.splitAtQuarterLength(3)
        self.assertEqual(len(mLeft.flatten().notes), 3)
        self.assertEqual(len(mLeft.voices), 2)
        self.assertEqual(len(mRight.flatten().notes), 3)
        self.assertEqual(len(mRight.voices), 2)

        sPost = Stream()
        sPost.append(mLeft)
        sPost.append(mRight)
        # sPost.show()

    def testSplitAtQuarterLengthC(self):
        '''
        Test splitting a Score
        '''
        s = corpus.parse('bwv66.6')
        sLeft, sRight = s.splitAtQuarterLength(6)

        self.assertEqual(len(sLeft.parts), 4)
        self.assertEqual(len(sRight.parts), 4)
        for i in range(4):
            self.assertEqual(
                str(sLeft.parts[i].getElementsByClass(Measure)[0].timeSignature),
                str(sRight.parts[i].getElementsByClass(Measure)[0].timeSignature))
        for i in range(4):
            self.assertEqual(
                str(sLeft.parts[i].getElementsByClass(Measure)[0].clef),
                str(sRight.parts[i].getElementsByClass(Measure)[0].clef))
        for i in range(4):
            self.assertEqual(
                str(sLeft.parts[i].getElementsByClass(Measure)[0].keySignature),
                str(sRight.parts[i].getElementsByClass(Measure)[0].keySignature))
        # sLeft.show()
        # sRight.show()

    def testSplitByQuarterLengths(self):
        '''
        Was not returning splitTuples before
        '''
        m = Measure([
            note.Note(quarterLength=8.0)
        ])

        with self.assertRaisesRegex(Music21Exception,
                                    'cannot split by quarter length list whose sum is not equal'):
            m.splitByQuarterLengths([1.0, 2.0])

        parts = m.splitByQuarterLengths([1.0, 2.0, 5.0])
        self.assertIsInstance(parts, _SplitTuple)
        self.assertEqual(len(parts), 3)
        self.assertIsInstance(parts[0], Measure)
        self.assertEqual(parts[0].quarterLength, 1.0)
        self.assertEqual(len(parts[0]), 1)
        self.assertEqual(parts[0][0].quarterLength, 1.0)

        self.assertEqual(parts[1].quarterLength, 2.0)
        self.assertEqual(len(parts[1]), 1)
        self.assertEqual(parts[1][0].quarterLength, 2.0)

        self.assertEqual(parts[2].quarterLength, 5.0)
        self.assertEqual(len(parts[2]), 1)
        self.assertEqual(parts[2][0].quarterLength, 5.0)
        self.assertEqual(parts[2][0].duration.type, 'complex')



    def testGracesInStream(self):
        '''
        testing grace notes
        '''
        s = Measure()
        s.append(note.Note('G3'))
        self.assertEqual(s.highestTime, 1.0)
        # shows up in the same position as the following note, not the grace
        s.append(dynamics.Dynamic('mp'))

        gn1 = note.Note('d#4', quarterLength=0.5)
        # could create a NoteRest method to get a GraceNote from a Note
        gn1.duration = gn1.duration.getGraceDuration()
        self.assertEqual(gn1.duration.quarterLength, 0.0)
        s.append(gn1)
        # highest time is the same after adding the gracenote
        self.assertEqual(s.highestTime, 1.0)

        s.append(note.Note('A4'))
        self.assertEqual(s.highestTime, 2.0)

        # this works just fine
        # s.show()

        match = [str(e.pitch) for e in s.notes]
        self.assertEqual(match, ['G3', 'D#4', 'A4'])

        # s.sort()

        # this insert and shift creates an ambiguous situation
        # the grace note seems to move with the note itself
        s.insertAndShift(1, note.Note('c4'))
        match = [str(e) for e in s.pitches]
        self.assertEqual(match, ['G3', 'C4', 'D#4', 'A4'])
        # s.show('t')
        # s.show()
        # inserting and shifting this results in it appearing before
        # the note at offset 2
        gn2 = note.Note('c#4', quarterLength=0.25).getGrace()
        gn2.duration.slash = False
        s.insertAndShift(1, gn2)
        # s.show('t')
        # s.show()
        match = [str(e) for e in s.pitches]
        self.assertEqual(match, ['G3', 'C#4', 'C4', 'D#4', 'A4'])

    def testGraceChords(self):


        s = Measure()
        s.append(chord.Chord(['G3', 'd4']))

        gc1 = chord.Chord(['d#4', 'a#4'], quarterLength=0.5)
        gc1.duration = gc1.duration.getGraceDuration()
        s.append(gc1)

        gc2 = chord.Chord(['e4', 'b4'], quarterLength=0.5)
        gc2.duration = gc2.duration.getGraceDuration()
        s.append(gc2)

        s.append(chord.Chord(['f4', 'c5'], quarterLength=2))

        gc3 = chord.Chord(['f#4', 'c#5'], quarterLength=0.5)
        gc3.duration = gc3.duration.getGraceDuration()
        s.append(gc3)

        s.append(chord.Chord(['e4', 'b4'], quarterLength=1))

        # s.show()

    def testScoreShowA(self):
        # this checks the specific handling of Score.makeNotation()

        s = Stream()
        s.append(key.Key('G'))
        GEX = m21ToXml.GeneralObjectExporter()
        raw = GEX.parse(s).decode('utf-8')

        self.assertGreater(raw.find('<fifths>1</fifths>'), 0, raw)

    def testGetVariantsA(self):
        s = Stream()
        v1 = variant.Variant()
        v2 = variant.Variant()
        s.append(v1)
        s.append(v2)
        self.assertEqual(len(s[variant.Variant]), 2)

    def testActivateVariantsA(self):
        '''
        This tests a single-measure variant
        '''
        s = Stream()
        s.repeatAppend(note.Note('d2'), 12)
        s.makeMeasures(inPlace=True)

        v1 = variant.Variant()
        m2Alt = Measure()
        m2Alt.repeatAppend(note.Note('G#4'), 4)
        v1.append(m2Alt)  # embed a complete Measure in v1

        # insert the variant at the desired location
        s.insert(4, v1)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 1)

        s.activateVariants(matchBySpan=False, inPlace=True)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'G#', 'G#', 'G#', 'G#', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 1)
        # activating again will restore the previous
        s.activateVariants(matchBySpan=False, inPlace=True)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 1)

    def testActivateVariantsB(self):
        '''
        This tests two variants with different groups, each a single measure
        '''
        s = Stream()
        s.repeatAppend(note.Note('d2'), 12)
        s.makeMeasures(inPlace=True)

        v1 = variant.Variant()
        m2Alt = Measure()
        m2Alt.repeatAppend(note.Note('a#4'), 4)
        v1.append(m2Alt)  # embed a complete Measure in v1
        v1.groups.append('m2-a')

        v2 = variant.Variant()
        m2Alt = Measure()
        m2Alt.repeatAppend(note.Note('b-4'), 4)
        v2.append(m2Alt)  # embed a complete Measure in v1
        v2.groups.append('m2-b')

        # insert the variant at the desired location
        s.insert(4, v1)
        s.insert(4, v2)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 2)

        s.activateVariants(group='m2-a', matchBySpan=False, inPlace=True)
        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'A#', 'A#', 'A#', 'A#', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 2)

        # if we try the same group twice, it is now not active, so there is no change
        s.activateVariants(group='m2-a', matchBySpan=False, inPlace=True)
        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'A#', 'A#', 'A#', 'A#', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 2)

        # activate a different variant
        s.activateVariants('m2-b', matchBySpan=False, inPlace=True)
        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'B-', 'B-', 'B-', 'B-', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 2)

        # TODO: keep groups
        # we now have 2 variants that have been stripped of their groups
        match = [e.groups for e in s[variant.Variant]]
        self.assertEqual(str(match), "[['default'], ['default']]")

    def testActivateVariantsC(self):
        '''
        This tests a two-measure variant
        '''
        s = Stream()
        s.repeatAppend(note.Note('d2'), 12)
        s.makeMeasures(inPlace=True)

        v1 = variant.Variant()
        m2Alt = Measure()
        m2Alt.repeatAppend(note.Note('G#4'), 4)
        v1.append(m2Alt)  # embed a complete Measure in v1
        m3Alt = Measure()
        m3Alt.repeatAppend(note.Note('A#4'), 4)
        v1.append(m3Alt)  # embed a complete Measure in v1

        # insert the variant at the desired location
        s.insert(4, v1)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 1)

        s.activateVariants(matchBySpan=False, inPlace=True)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'G#', 'G#', 'G#', 'G#', 'A#', 'A#', 'A#', 'A#']")
        self.assertEqual(len(s[variant.Variant]), 1)
        # s.show('t')
        # can restore the removed two measures
        s.activateVariants(matchBySpan=False, inPlace=True)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s[variant.Variant]), 1)

    def testActivateVariantsD(self):
        '''
        This tests a note-level variant
        '''
        s = Stream()
        s.repeatAppend(note.Note('d2'), 12)

        v = variant.Variant()
        v.append(note.Note('G#4'))
        v.append(note.Note('a#4'))
        v.append(note.Note('c#5'))

        s.insert(5, v)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s.notes), 12)
        self.assertEqual(len(s[variant.Variant]), 1)

        s.activateVariants(matchBySpan=False, inPlace=True)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'G#', 'A#', 'C#', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s.notes), 12)
        self.assertEqual(len(s[variant.Variant]), 1)
        # s.show('t')
        s.activateVariants(matchBySpan=False, inPlace=True)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s.notes), 12)
        self.assertEqual(len(s[variant.Variant]), 1)

        # note that if the start times of each component do not match, the
        # variant part will not be matched

    def testActivateVariantsE(self):
        '''
        This tests a note-level variant with miss-matched rhythms
        '''
        s = Stream()
        s.repeatAppend(note.Note('d2'), 12)

        v = variant.Variant()
        v.append(note.Note('G#4', quarterLength=0.5))
        v.append(note.Note('a#4', quarterLength=1.5))
        v.append(note.Note('c#5', quarterLength=1))

        s.insert(5, v)

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s.notes), 12)
        self.assertEqual(len(s[variant.Variant]), 1)

        s.activateVariants(matchBySpan=False, inPlace=True)

        # TODO
        # this only matches the Notes that start at the same position

        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'G#', 'D', 'C#', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s.notes), 12)
        self.assertEqual(len(s[variant.Variant]), 1)

        self.assertEqual(str(list(s[variant.Variant].first().elements)),
                         '[<music21.note.Note D>, <music21.note.Note D>]')

    def testActivateVariantsBySpanA(self):
        '''
        test replacing 1 note with a 3-note variant
        '''
        s = Stream()
        s.repeatAppend(note.Note('d2'), 12)

        v = variant.Variant()
        v.insert(0, dynamics.Dynamic('ff'))
        v.append(note.Note('G#4', quarterLength=0.5))
        v.append(note.Note('a#4', quarterLength=0.25))
        v.append(note.Note('c#5', quarterLength=0.25))
        s.insert(5, v)

        # pre-check
        self.assertEqual(len(s.flatten().notes), 12)
        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s.getElementsByClass(dynamics.Dynamic)), 0)

        s.activateVariants(matchBySpan=True, inPlace=True)
        self.assertEqual(len(s.flatten().notes), 14)  # replace 1 w/ 3, for +2
        self.assertEqual(
            str([p.name for p in s.pitches]),
            "['D', 'D', 'D', 'D', 'D', 'G#', 'A#', 'C#', 'D', 'D', 'D', 'D', 'D', 'D']")
        self.assertEqual(len(s.getElementsByClass(dynamics.Dynamic)), 1)

        s.activateVariants(matchBySpan=True, inPlace=True)
        self.assertEqual(len(s.flatten().notes), 12)
        self.assertEqual(str([p.name for p in s.pitches]),
                         "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        # TODO: as we are presently matching removal by classes in the Variant
        # the variant now has no dynamics, and thus leaves the dyn from the
        # old variant here
        self.assertEqual(len(s.getElementsByClass(dynamics.Dynamic)), 1)

        # s.show()

    def testActivateVariantsBySpanB(self):
        '''
        test replacing 2 measures by a longer single measure
        '''
        s = Stream()
        s.repeatAppend(note.Note('d2'), 16)
        s.makeMeasures(inPlace=True)

        v1 = variant.Variant()
        m2Alt = Measure()
        m2Alt.repeatAppend(note.Note('a#4'), 8)
        m2Alt.timeSignature = meter.TimeSignature('8/4')
        v1.append(m2Alt)  # embed a complete Measure in v1
        v1.groups.append('m2-a')

        # insert the variant at the desired location
        s.insert(4, v1)
        self.assertEqual(len(s.flatten().notes), 16)
        self.assertEqual(len(s.getElementsByClass(Measure)), 4)
        self.assertEqual(
            str([p.name for p in s.pitches]),
            "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")

        # replace 2 measures for 1
        s.activateVariants(matchBySpan=True, inPlace=True)
        self.assertEqual(len(s.flatten().notes), 16)
        self.assertEqual(len(s.getElementsByClass(Measure)), 3)
        self.assertEqual([p.name for p in s.pitches],
                         ['D', 'D', 'D', 'D',
                          'A#', 'A#', 'A#', 'A#', 'A#', 'A#', 'A#', 'A#',
                          'D', 'D', 'D', 'D'])

        # replace the one for two
        s.activateVariants('default', matchBySpan=True, inPlace=True)
        self.assertEqual(len(s.getElementsByClass(Measure)), 4)
        self.assertEqual(
            str([p.name for p in s.pitches]),
            "['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D']")
        # s.show()

    def testTemplateAll(self):
        b = corpus.parse('bwv66.6')
        bass = b.parts[3]
        bassEmpty = bass.template(fillWithRests=False, removeClasses=True)
        for x in bassEmpty:
            if isinstance(x, Measure):
                self.assertEqual(len(x), 0)

    def testSetElements(self):
        s = Stream()
        s.append(note.Note('C', type='half'))
        s.append(note.Note('D', type='half'))
        s.append(note.Note('E', type='half'))
        s.append(note.Note('F', type='half'))
        n1 = s.notes[0]
        n2 = s.notes[len(s.notes) // 2]
        n3 = s.notes[-1]
        sp1 = dynamics.Diminuendo(n1, n2)
        sp2 = dynamics.Crescendo(n2, n3)
        s.append(sp1)
        s.append(sp2)
        s2 = Stream()
        s2.elements = s  # do not set elements to s.elements, use s instead.
        for el in s2:
            self.assertEqual(el.getOffsetBySite(s2),
                             el.getOffsetBySite(s))

    def testGetElementAfterElement(self):
        n1 = note.Note('A3')
        n2 = note.Note('B3')
        n2.id = 'firstB'
        n3 = note.Note('B3')
        n3.id = 'secondB'
        n4 = note.Note('D4')

        m1 = note.Note('E4')
        m2 = note.Note('F4')
        m3 = note.Note('G4')
        m4 = note.Note('A-5')

        bass = Stream()
        bass.append([n1, n2, n3, n4])
        sop = Stream()
        sop.append([m1, m2, m3, m4])
        for i in range(len(bass.notes) - 1):
            note1 = bass.notes[i]
            note2 = bass.getElementAfterElement(note1, ['Note'])
            unused_note3 = sop.playingWhenAttacked(note1)
            unused_note4 = sop.playingWhenAttacked(note2)
            # print(note1, note2, note3, note4)
            # print(note1.id, note2.id, note3.id, note4.id)
        # TEST???

    def testCoreGuardBeforeAddElement(self):
        n = note.Note()
        s = Stream()
        with self.assertRaises(StreamException):
            Stream([n, n])
        with self.assertRaises(StreamException):
            Stream([n, None, s.iter()])

    # REMOVED: Turns out that it DOES have fermata on every note!
    # def testSchoenbergChordifyFermatas(self):
    #     '''
    #     test that after chordification, only
    #     the specific time point with a fermata has a fermata.
    #     '''
    #     schoenberg = corpus.parse('schoenberg/opus19', 6)
    #     excerpt = schoenberg.measures(10, 10)
    #     chordBefore = excerpt.parts[0].getElementsByClass(Measure)[0].notes[0]
    #     for n in chordBefore:
    #         print(n, n.expressions)
    #     return
    #     chordStream = excerpt.chordify()
    #
    #     m10 = chordStream.getElementsByClass(Measure)[0]
    #     c0 = m10.notes[0]
    #     self.assertEqual(c0.expressions, [])
    #     cLastButOne = m10.notes[-2]
    #     self.assertEqual(len(cLastButOne.expressions), 1)
    #     self.assertIn('Fermata', cLastButOne.expressions[0])
    #     cLast = m10.notes[-1]
    #     self.assertEqual(cLast.expressions, [])

    @staticmethod
    def get_beams_from_stream(srcList):
        '''
        Helper function to return beam list for all notes and rests in the stream.
        '''
        return [n.beams for n in srcList if isinstance(n, GeneralNote)]

    def test_makeBeams__all_quarters(self):
        '''
        Test that for a measure full of quarters, there are no beams
        '''
        m = Measure()
        m.timeSignature = meter.TimeSignature('4/4')
        m.repeatAppend(note.Note(quarterLength=1), 4)

        m2 = m.makeBeams()
        beams = self.get_beams_from_stream(m2)

        self.assertEqual([beam.Beams(), beam.Beams(), beam.Beams(), beam.Beams()], beams)

    def test_makeBeams__all_eighths(self):
        '''
        Test a full measure full of eighth is grouped by beams into couples
        '''
        m = Measure()
        m.timeSignature = meter.TimeSignature('4/4')
        m.repeatAppend(note.Note(quarterLength=0.5), 8)

        m2 = m.makeBeams()
        beams = self.get_beams_from_stream(m2)

        # Prepare: should be beams
        first_note_beams = beam.Beams()
        first_note_beams.append('start')

        second_note_beams = beam.Beams()
        second_note_beams.append('stop')

        # Now test that they are equal
        self.assertEqual(first_note_beams, beams[0])
        self.assertEqual(second_note_beams, beams[1])

        self.assertEqual(first_note_beams, beams[2])
        self.assertEqual(second_note_beams, beams[3])

        self.assertEqual(first_note_beams, beams[4])
        self.assertEqual(second_note_beams, beams[5])

        self.assertEqual(first_note_beams, beams[6])
        self.assertEqual(second_note_beams, beams[7])

    def test_makeBeams__eighth_rests_and_eighth(self):
        '''
        Test a full measure of 8th rest followed by 8th note
        '''
        m = Measure()
        m.timeSignature = meter.TimeSignature('4/4')
        for i in range(4):
            m.append(note.Rest(quarterLength=0.5))
            m.append(note.Note(quarterLength=0.5))

        m2 = m.makeBeams()
        beams = self.get_beams_from_stream(m2)

        self.assertEqual([beam.Beams(), ] * 8, beams)

    def test_makeBeams__repeated_1_e_a(self):
        '''
        Test that the pattern of "1 e a" repeated more than once has correct beams.

        Note: proper beams repr: https://share.getcloudapp.com/12uE7eBA
        '''
        m = Measure()
        m.timeSignature = meter.TimeSignature('2/4')
        for i in range(2):
            m.append(note.Note(quarterLength=0.25))
            m.append(note.Note(quarterLength=0.50))
            m.append(note.Note(quarterLength=0.25))

        m2 = m.makeBeams()
        beams = self.get_beams_from_stream(m2)

        # Prepare: should be beams
        first_note_beams = beam.Beams()
        first_note_beams.append('start')
        first_note_beams.append('partial', 'right')

        second_note_beams = beam.Beams()
        second_note_beams.append('continue')

        third_note_beams = beam.Beams()
        third_note_beams.append('stop')
        third_note_beams.append('partial', 'left')

        # Now test that they are equal
        self.assertEqual(first_note_beams, beams[0])
        self.assertEqual(second_note_beams, beams[1])
        self.assertEqual(third_note_beams, beams[2])

        self.assertEqual(first_note_beams, beams[3])
        self.assertEqual(second_note_beams, beams[4])
        self.assertEqual(third_note_beams, beams[5])

    def test_makeBeams__1_e_n_a(self):
        '''
        Test that 4 16th notes have proper beams across them all.
        '''
        m = Measure()
        m.timeSignature = meter.TimeSignature('1/4')
        m.repeatAppend(note.Note(quarterLength=0.25), 4)

        m2 = m.makeBeams()
        beams = self.get_beams_from_stream(m2)

        # Prepare: should be beams
        first_note_beams = beam.Beams()
        first_note_beams.append('start')
        first_note_beams.append('start')

        second_note_beams = beam.Beams()
        second_note_beams.append('continue')
        second_note_beams.append('continue')

        third_note_beams = beam.Beams()
        third_note_beams.append('continue')
        third_note_beams.append('continue')

        fourth_note_beams = beam.Beams()
        fourth_note_beams.append('stop')
        fourth_note_beams.append('stop')

        # Now test that they are equal
        self.assertEqual(first_note_beams, beams[0])
        self.assertEqual(second_note_beams, beams[1])
        self.assertEqual(third_note_beams, beams[2])
        self.assertEqual(fourth_note_beams, beams[3])

    def test_makeBeams__1_e__after_16th_note(self):
        '''
        Test that a 16th+8th notes after a 16th notes have proper beams.
        '''
        m = Measure()
        m.timeSignature = meter.TimeSignature('2/4')

        m.append(note.Note(quarterLength=0.50))
        m.append(note.Note(quarterLength=0.25))
        m.append(note.Note(quarterLength=0.25))

        m.append(note.Note(quarterLength=0.25))
        m.append(note.Note(quarterLength=0.75))

        m2 = m.makeBeams()
        beams = self.get_beams_from_stream(m2)

        # Prepare: should be beams
        fourth_note_beams = beam.Beams()
        fourth_note_beams.append('start')
        fourth_note_beams.append('partial', 'right')

        # Now test that they are equal
        self.assertEqual(fourth_note_beams, beams[3])

    def test_makeBeams__paddingLeft_2_2(self):
        m = Measure()
        m.timeSignature = meter.TimeSignature('2/2')
        m.paddingLeft = 1.5  # 5-eighth-note pickup
        m.repeatAppend(note.Note(type='eighth'), 5)

        m.makeBeams(inPlace=True)
        beams = self.get_beams_from_stream(m)

        start_beam = beam.Beams()
        start_beam.append('start')
        continue_beam = beam.Beams()
        continue_beam.append('continue')
        stop_beam = beam.Beams()
        stop_beam.append('stop')

        self.assertEqual(beams[0], beam.Beams())  # first should have no beams
        self.assertEqual(beams[1], start_beam)  # second should be "start"
        self.assertEqual(beams[2], continue_beam)  # third should be "continue"
        self.assertEqual(beams[3], continue_beam)  # fourth should be "continue"
        self.assertEqual(beams[4], stop_beam)  # last should be "stop"

    def test_makeBeams__paddingRight(self):
        m = Measure()
        m.timeSignature = meter.TimeSignature('6/8')
        m.paddingRight = 1.0
        m.append(note.Note(type='quarter'))
        m.append(note.Note(type='eighth'))
        m.append(note.Note(type='eighth'))

        m.makeBeams(inPlace=True)
        beams = self.get_beams_from_stream(m)

        no_beam = beam.Beams()
        start_beam = beam.Beams()
        start_beam.append('start')
        stop_beam = beam.Beams()
        stop_beam.append('stop')

        self.assertEqual(beams, [no_beam, no_beam, no_beam])

        m.paddingRight = 0.5
        m.append(note.Note(type='eighth'))

        m.makeBeams(inPlace=True)
        beams = self.get_beams_from_stream(m)

        self.assertEqual(beams, [no_beam, no_beam, start_beam, stop_beam])

    def testWrite(self):
        s = Stream([note.Note()])
        tmpMusicxml = environLocal.getTempFile(suffix='musicxml')
        tmpXml = environLocal.getTempFile(suffix='xml')
        tmpNoSuffix = environLocal.getTempFile()

        # Default: .musicxml
        out1 = s.write()
        # .musicxml pathlib.Path
        out2 = s.write(fp=tmpMusicxml)
        # .xml pathlib.Path
        out3 = s.write(fp=tmpXml)
        # .musicxml string
        out4 = s.write(fp=str(tmpMusicxml))
        # .xml string
        out5 = s.write(fp=str(tmpXml))
        # no suffix
        out6 = s.write(fp=tmpNoSuffix)

        self.assertEqual(out1.suffix, '.musicxml')
        self.assertEqual(out2.suffix, '.musicxml')
        self.assertEqual(out3.suffix, '.xml')
        self.assertEqual(out4.suffix, '.musicxml')
        self.assertEqual(out5.suffix, '.xml')
        # Provide suffix if user didn't provide one
        self.assertEqual(out6.suffix, '.musicxml')

        self.assertEqual(str(out2), str(out4))
        self.assertEqual(str(out3), str(out5))

        for fp in (out1, tmpMusicxml, tmpXml, tmpNoSuffix, out6):
            os.remove(fp)

    def testOpusWrite(self):
        o = Opus()
        s1 = Score()
        s2 = Score()
        p1 = converter.parse('tinyNotation: 4/4 e1')
        p2 = converter.parse('tinyNotation: 4/4 f1')
        s1.append(p1)
        s2.append(p2)
        o.append([s1, s2])

        out = o.write()
        otherFile = str(out).replace('-2', '-1')
        self.assertIsNotNone(out)
        os.remove(out)
        os.remove(otherFile)

        # test no fp
        out = o.write()
        otherFile = str(out).replace('-2', '-1')
        self.assertTrue(str(out).endswith('-2.musicxml'))
        self.assertTrue(os.path.exists(otherFile))
        os.remove(out)
        os.remove(otherFile)

        # test giving fp
        tmp = environLocal.getTempFile(suffix='xml')
        out = o.write(fp=tmp)
        otherFile = str(out).replace('-2', '-1')
        self.assertTrue(str(out).endswith('-2.xml'))
        self.assertTrue(os.path.exists(otherFile))
        os.remove(tmp)
        os.remove(out)
        os.remove(otherFile)

        # test another format
        out = o.write(fmt='midi')
        otherFile = str(out).replace('-2', '-1')
        self.assertTrue(str(out).endswith('-2.mid'))
        self.assertTrue(os.path.exists(otherFile))
        os.remove(out)
        os.remove(otherFile)

    def testActiveSiteAfterBoolIteration(self):
        n = note.Note()
        s1 = Stream([n])
        s2 = Stream([n])
        self.assertIs(n.activeSite, s2)
        self.assertTrue(s1.notes)
        self.assertIs(n.activeSite, s2)
# -----------------------------------------------------------------------------


if __name__ == '__main__':
    music21.mainTest(Test, 'verbose')
