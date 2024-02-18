from stepmania_map import StepmaniaMap

from multiprocessing import Pool

import pathlib as p
import os
import re

import librosa

from fractions import Fraction

BPMRE = re.compile('BPMS:(\d+\.\d+=\d+\d+,?)+')
MUSICRE = re.compile('MUSIC:(.+);')

def get_bpm(musicfile):
    y, sr = librosa.load(musicfile)
    onset_envelope = librosa.onset.onset_strength(y, sr)
    # onsets = librosa.onset.onset_detect(onset_envelope=onsent_envelope)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_envelope)

    return tempo

def process_mapfile(mapfile):
    # SM = StepmaniaMap(template_path='./template.sm')
    # SM.load_from_osu_file(mf)
    try:
        path = p.Path(mapfile)
        map_dir = path.parent
        with open(path) as f:
            contents = f.read()

        bpms = BPMRE.search(contents).groups()[0]
        bpm = float(bpms.split(',')[0].split('=')[1])
        musicf = MUSICRE.search(contents).groups()[0]

        music_file_path = p.Path(map_dir, musicf)

        rosa_tempo = get_bpm(music_file_path)
    except:
        return None

    # Attempt to correct fractions
    ratio = Fraction(rosa_tempo / bpm).limit_denominator(12)
    corrected = (1 / ratio) * rosa_tempo
    accuracy = 100.0 * (corrected - bpm) / (bpm)

    return (corrected, bpm)

    # print(f' {bpms} / {rosa_tempo} ({accuracy:2.4}%)')

def process_packdir(d):
    run_pool = Pool(5) 

    all_results = []

    stepmania_files = list(p.Path(d).rglob('*.sm'))

    iterator = run_pool.imap(process_mapfile, stepmania_files)

    finished = 0
    total_files = len(stepmania_files)

    for result in iterator: 
        finished += 1
        completion = finished * 100.0 / total_files
        progress = f'{completion:2.4}%'

        all_results += [result]
        print(f'\rdone {progress}')

    return all_results

if __name__ == '__main__':
    import sys
    packdir = sys.argv[1]

    results = process_packdir(packdir)
