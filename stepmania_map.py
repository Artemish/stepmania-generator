import sys
import re
import pandas as pd

from fractions import Fraction

from collections import defaultdict
from io import StringIO

class StepmaniaMap():
    def __init__(self, template_path):
        with open(template_path) as templatefile:
            self.template_string = templatefile.read()

    def load_from_file(self, filepath):
        with open(filepath) as f:
            file_contents = f.read()

        self._parse_sections(file_contents)

        self._parse_hitobjects()
        self._parse_timings()
        self._parse_offset()
        self._parse_metadata()
        self._make_notedata()

    def _parse_sections(self, file_contents):
        lines = file_contents.split('\n')

        SECTION_RE = re.compile('\[([a-zA-Z]+)\]')
        output = defaultdict(list)
        current_section = None

        for line in lines:
            match = SECTION_RE.match(line)
            if match is not None:
                current_section = match.groups()[0]
            elif current_section is not None:
                output[current_section].append(line)

        self.section_map = dict(output)

    def _parse_hitobjects(self):
        lines = self.section_map['HitObjects']
        preamble = 'x$y$time$type$hitSound$objectParams$hitSample'

        # Sliders and other objects have a comma-separated list of 
        # parameters, group them out so the CSV parsing trick works
        def munge_params(line):
            fields = line.split(',')
            obj_params = ','.join(fields[5:-2])
            reorg = fields[:5] + [obj_params, fields[-1]]
            return '$'.join(reorg)

        lines = lines[:-1] # Skip the last empty line
        munged = list(map(munge_params, lines))

        buffer = '\n'.join([preamble] + munged)

        # Turn the string into a buffer
        self.hits = pd.read_csv(
            StringIO(buffer),
            delimiter='$',
        )

    def _beat_gap_summary(hits):
        counter = defaultdict(int)
        last_time = 0

        for row in hits.itertuples():
            counter[row.time - last_time] += 1
            last_time = row.time

        return [k for k in counter.keys() if counter[k] > 10]

    def _parse_timings(self):
        lines =  self.section_map['TimingPoints'][:-1] # Skip the last empty line
        fields = [
            'time', 'beatLength', 'meter', 'sampleSet', 
            'sampleIndex', 'volume', 'uninherited', 'effects'
        ]
        preamble = ','.join(fields)
        buffer = '\n'.join([preamble] + lines)

        # Turn the string into a buffer
        self.timings = pd.read_csv(
            StringIO(buffer),
            delimiter=',',
        )

    def _osu_to_sm_bpm(self):
        def from_osu(timing):
            start_ms = timing.Index / 1000.
            bpm = 60000. / timing.beatLength
            return f"{start_ms:.3f}={bpm:.3f}"

        uninherited = self.timings[self.timings.uninherited == 1]
        return ','.join(map(from_osu, uninherited.itertuples()))

    def _parse_metadata(self):
        section = self.section_map['General']
        items = [line.split(': ') for line in section[:-1]]

        self.metadata = {
            item[0]: item[1] for item in items
        }

    def _parse_offset(self):
        timestamp = self.timings[self.timings.uninherited==1].iloc[0].time
        self.offset = str(round(timestamp / 1000., 3))

    def _make_notedata(self):
        hits = self.hits
        # Now this is where the magic happens
        timings = self.timings[:]
        uninherited = timings[timings.uninherited==1]
        # timings['time'] -= float(offset)*1000 # From zero

        def clamp_denominator(v, limit=24):
            v_fractional = v % 1 
            v_integral = int(v - v_fractional)
            return Fraction(v_fractional).limit_denominator(24) + v_integral

        def hits_in_timing_section(section):
            uninherited = timings[timings.uninherited==1]
            result = hits[hits.time >= section.time]

            sections_after = uninherited[uninherited.time > section.time]

            if len(sections_after):
                end_time = min(sections_after.time)
                result = result[result.time < end_time]

            return result

        beat_diffs = []

        for (index, timing_section) in uninherited.iterrows():
            current_time = timing_section.time
            section_hits = hits_in_timing_section(timing_section)
            for hit in section_hits.itertuples():
                # print(f'{hit.time}: ({hit.x}, {hit.y})')
                time_diff = hit.time - current_time
                beat_diff = time_diff / timing_section.beatLength

                # Only limit the denominator on the fractional part
                beat_diffs.append(clamp_denominator(beat_diff))

                current_time = hit.time

        # Broad strategy:
        ## Prepopulate the measures for the SM beatmap
        ## For each note in the osu map, put it in the right measure in the SM map
        ## For each note in the osu map, put it in the right measure in the SM map

        def empty_measure():
            return [[0,0,0,0] for i in range(16)]

        def shrink_measure(measure):
            pass

        def random_beat():
            from random import randint 

            beat = [0,0,0,0]
            beat[randint(0, 3)] = 1
            return beat

        all_measures = []

        beat_time = Fraction(0)
        beats_per_measure = 4
        measure = empty_measure()

        for diff in beat_diffs:
            beat_time += diff
            while beat_time >= beats_per_measure:
                all_measures.append(measure)
                measure = empty_measure()
                beat_time -= beats_per_measure
            # 0 <= beat_time < beats_per_measure
            position = int(beat_time*4)
            measure[position] = random_beat()

        all_measures.append(measure)

        output = StringIO()

        for (index, measure) in enumerate(all_measures):
            for beat in measure:
                output.write(''.join(map(str, beat)) + '\n')

            if index == len(all_measures) - 1:
                output.write(';')
            else:
                output.write(',\n')

        self.notedata = output.getvalue()

    def write_sm_beatmap(self, output_path):
        params = {
            'bpms': self._osu_to_sm_bpm(),
            'offset': self.offset,
            'audiopath': self.metadata['AudioFilename'],
            'notedata': self.notedata,
        }

        result = self.template_string.replace(
            '{BPMS}', params['bpms'],
        ).replace(
            '{AUDIOPATH}', params['audiopath'],
        ).replace(
            '{OFFSET}', params['offset'],
        ).replace(
            '{NOTEDATA}', params['notedata'],
        )

        with open(output_path, 'w') as dest:
            dest.write(result)
