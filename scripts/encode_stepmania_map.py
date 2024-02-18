import argparse
import numpy as np
import sys

import re

IGNORE_LINE_RE = re.compile(r'^(#| )')
MEASURE_RE = re.compile(r'^[0-9M]+$')

NOTE_SUBS = {
  'M': '9',
  '=': '8',
  '.': '7',
  '-': '6',
}

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'stepmania_map',
        help='File path of the Stepmania beatmap file to encode'
    )

    # parser.add_argument(
    #     'output_file',
    #     help='File path to save the encoded file'
    # )

    return parser

def encode_stepmania_map(file_contents):
    difficulties = []
    current_difficulty = []
    measure = []

    map_started = False

    lineno = -1

    lines = file_contents.split('\n')

    for line in file_contents.split('\n'):
        lineno += 1
        # print(lineno)
        if line.startswith('//'):
            map_started = True
            # print(line)
        elif line == '':
            continue
        elif line.startswith(','):
            current_difficulty.append(pad_measure_to_192(measure))
            measure = []
        elif line.startswith(';'):
            current_difficulty.append(pad_measure_to_192(measure))
            measure = []

            difficulties.append(np.array(current_difficulty))
            current_difficulty = []

            map_started = False
        elif MEASURE_RE.match(line) and map_started: 
            for (before, after) in NOTE_SUBS.items():
                line = line.replace(before, after)

            beat = [int(note) for note in line]
            measure.append(beat) 

    return difficulties

def pad_measure_to_192(measure):
    padded = np.zeros([192,4], dtype=np.int8)
    width = len(measure)

    if width == 0:
        return padded

    if (192 % width) != 0:
        raise RuntimeError(f"Can't reencode measure of witdh {width}")

    pad_width = 192 // width

    p_index = 0
    for beat in measure:
        padded[p_index] = beat
        p_index += pad_width

    return padded

if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()

    parser = get_parser()

    with open(args.stepmania_map) as stepfile:
        contents = stepfile.read()

    # try:
    encoded_map = encode_stepmania_map(contents)
    #except:
    #    print(f"Couldn't proccess {args.stepmania_map}")
    #    sys.exit(1)

    for (i, diff) in enumerate(encoded_map):
        print(type(diff))
        print(f'// Difficulty {i} {diff.shape}')
        for measure in diff:
            for beat in measure:
                print(''.join(map(str, beat)))
            if i != len(encoded_map) - 1:
                print(',')
        print(';')

    # measure_lengths = [[len(m) for m in diff] for diff in encoded_map]
    # measure_sizes = set(sum(measure_lengths, []))

    # print(sorted(measure_sizes))

    # np.save(args.output_file, encoded_map)
