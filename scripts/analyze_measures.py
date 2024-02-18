from sympy.ntheory import factorint
import numpy as np
from collections import Counter

with open('measure_lengths.txt') as infile:
  content = infile.read()

mc = Counter()

for line in content.split('\n'):
    if line == '':
        continue
    l = eval(line)
    mc.update(l)
