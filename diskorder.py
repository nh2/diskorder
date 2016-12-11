#!/usr/bin/env python2

import os
import sys
import argparse

import fiemap

parser = argparse.ArgumentParser(description='Print files sorted by physical disk order.')
parser.add_argument('files', metavar='FILE', type=str, nargs='*',
                    help='Files to order; if not given, files are read from stdin')
args = parser.parse_args()

files = args.files

if files == []:
  # Get files from stdin, skip empty lines
  files = [line.rstrip('\n') for line in sys.stdin.readlines() if line != '']

physical_addresses = [0 for f in files]
inode_numbers = [0 for f in files]

for i, path in enumerate(files):
  with open(path, 'r') as fd:
    inode_numbers[i] = os.fstat(fd.fileno()).st_ino
    mappings = fiemap.get_all_mappings(fd)
    if len(mappings.extents) > 0:
      physical_addresses[i] = mappings.extents[0].physical
    else:
      # We put files without extents first (they will still be sorted by inode secondarily).
      physical_addresses[i] = 0

# Sort files first by physical address, then by inode (the latter is important
# for files that have no extents and thus we have no physical address for them).
print '\n'.join(f for (addr, ino, f) in sorted(zip(physical_addresses, inode_numbers, files)))
