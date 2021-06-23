#!/usr/bin/env python3
# alice siqi chen

import os 
import sys 
/mithril/Data/Nanopore/projects/visium/210309_r2c2_sample6_test/c3poa_output/UMI_Splint_1/

path to 

def parse_args():
    '''Parses arguments.'''
    parser = argparse.ArgumentParser(description='calculate % total R2C2 reads with zero repeats.',
                                     add_help=True,
                                     prefix_chars='-')
    parser.add_argument('--input_R2C2_Consensus_file', '-i', type=str, action='store',
                        help='Fasta file with consensus called R2C2 reads (output from C3POa.py)'))
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    return parser.parse_args()
args = parse_args()
inFile =args.input_R2C2_Consensus_file

def zero_repeat(inFile):
  read_count = 0
  count = 0
  for line in open('inFile', 'r'):
    if line.startswith('>'):
        line=line.rstrip()
        subread=int(line.split('_')[3])
        if subread>=1:
            count+=1
        else: 
            continue
    else:
        read_count+=1
        continue
  #print(count)    
  #print(read_count)
  percent_zero_repeat = "{:.0%}".format(float((read_count-count)/read_count))
  print('%s of total reads has zero repeats'%percent_zero_repeat)
  return percent_zero_repeat

zero_repeat(inFile)

