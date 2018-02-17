#!/usr/bin/env python3
# Roger Volden and Chris Vollmers
# Last updated: 16 Feb 2018

'''
Concatemeric Consensus Caller with Partial Order Alignments (C3POa)

Analyses reads by reading them in, doing self-self alignments, calling
peaks in alignment scores, splitting reads, aligning those to each other,
and giving back a consensus sequence.

Usage:
    python3 C3POa_racon_sam.py /current/directory/ reads.fastq

Dependencies:
    Python 3.6
    NumPy 1.13.3
    poa v1.0.0 Revision: 1.2.2.9
    EMBOSS water: watHerON v8
    minimap2 2.7-r654

To do:
    Add argument parser for more robust use.
'''

import os
import sys
import numpy as np

'''Putting these globals here until I decide to make a class'''
poa = 'poa'
score_matrix = '/home/vollmers/scripts/NUC.4.4.mat'
water = '/home/vollmers/scripts/EMBOSS-6.6.0/emboss/water'
consensus = 'python3 /home/vollmers/scripts/consensus.py'
minimap2 = 'minimap2'
racon = '/home/vollmers/scripts/racon/bin/racon'

temp_folder = 'tmp1'
path = sys.argv[1]
input_file = sys.argv[2]
os.chdir(path)
out_file = 'R2C2_Consensus.fasta'
subread_file = 'subreads.fastq'
sub = open(path + '/' + subread_file, 'w')
os.system('rm -r ' + temp_folder)
os.system('mkdir ' + temp_folder)

def revComp(sequence):
    '''Returns the reverse complement of a sequence'''
    bases = {'A':'T', 'C':'G', 'G':'C', 'T':'A', 'N':'N', '-':'-'}
    return ''.join([bases[x] for x in list(sequence)])[::-1]

def split_read(split_list, sequence, out_file1, qual, out_file1q, name):
    '''
    split_list : list, peak positions
    sequence : str
    out_file1 : output FASTA file
    qual : str, quality line from FASTQ
    out_file1q : output FASTQ file
    name : str, read ID

    Writes sequences to FASTA and FASTQ files.
    Returns number of repeats in the sequence.
    '''
    out_F = open(out_file1, 'w')
    out_Fq = open(out_file1q, 'w')
    distance = []
    for i in range(len(split_list) - 1):
        split1 = split_list[i]
        split2 = split_list[i + 1]
        if len(sequence[split1:split2]) > 30:
            out_F.write('>' + str(i + 1) + '\n' + \
                        sequence[split1:split2] + '\n')
            out_Fq.write('@' + str(i + 1) + '\n' + \
                         sequence[split1:split2] + '\n + \n' + \
                         qual[split1:split2] + '\n')
            sub.write('@' + name + '_' + str(i + 1) +' \n' + \
                      sequence[split1:split2] + '\n + \n' + \
                      qual[split1:split2] + '\n')

    if len(sequence[:split_list[0]]) > 50 and len(sequence[split2:]) > 50:
        out_Fq.write('@' + str(0) + '\n' + \
                     sequence[0:split_list[0]] + '\n + \n' + \
                     qual[0:split_list[0]] + '\n')
        sub.write('@' + name + '_' + str(0) + '\n' + \
                  sequence[0:split_list[0]] + '\n + \n' + \
                  qual[0:split_list[0]] + '\n')
        out_Fq.write('@' +str(i + 2) + '\n' + \
                     sequence[split2:] + '\n + \n' + \
                     qual[split2:] + '\n')
        sub.write('@' + name + '_' + str(i + 2) + '\n' + \
                  sequence[split2:] + '\n + \n' + \
                  qual[split2:] + '\n')
    repeats = str(int(i + 1))
    out_F.close()
    out_Fq.close()
    return repeats

def read_fasta(inFile):
    '''Reads in FASTA files, returns a dict of header:sequence'''
    readDict = {}
    tempSeqs, headers, sequences = [], [], []
    for line in inFile:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith('>'):
            headers.append(line.split()[0][1:])
        # covers the case where the file ends while reading sequences
        if line.startswith('>'):
            sequences.append(''.join(tempSeqs).upper())
            tempSeqs = []
        else:
            tempSeqs.append(line)
    sequences.append(''.join(tempSeqs).upper())
    for i in range(len(headers)):
        readDict[headers[i]] = sequences[i]
    return readDict

def rounding(x, base):
    '''Rounds to the nearest base, we use 50'''
    return int(base * round(float(x)/base))

def savitzky_golay(y, window_size, order, deriv=0, rate=1, returnScoreList=False):
    '''
    Smooths over data using a Ssavitzky Golay filter
    This can either return a list of scores, or a list of peaks

    y : array-like, score list
    window_size : int, how big of a window to smooth
    order : what order polynomial
    returnScoreList : bool
    '''
    from math import factorial
    y = np.array(y)
    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with values taken from the signal itself
    firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    filtered = np.convolve( m[::-1], y, mode='valid')

    if returnScoreList:
        return np.convolve( m[::-1], y, mode='valid')

    # set everything between 1 and -inf to 1
    posFiltered = []
    for i in range(len(filtered)):
        if 1 > filtered[i] >= -np.inf:
            posFiltered.append(1)
        else:
            posFiltered.append(filtered[i])

    # use slopes to determine peaks
    peaks = []
    slopes = np.diff(posFiltered)
    la = 45 # how far in sequence to look ahead
    for i in range(len(slopes)-50):
        if i > len(slopes)-la: # probably irrelevant now
            dec = all(slopes[i+x]<0 for x in range(1, 50))
            if slopes[i] > 0 and dec:
                if i not in peaks:
                    peaks.append(i)
        else:
            dec = all(slopes[i+x]<0 for x in range(1, la))
            if slopes[i] > 0 and dec:
                peaks.append(i)
    return peaks

def callPeaks(scoreListF, scoreListR, seed):
    '''
    scoreListF : list of forward scores
    scoreListR : list of reverse scores
    seed : position of the first occurrence of the splint
    returns a sorted list of all peaks
    '''
    allPeaks = []
    allPeaks.append(seed)
    # Filter out base level noise in forward scores
    if not scoreListF:
        smoothedScoresF = []
    else:
        noise = 0
        try:
            for i in range(500):
                if scoreListF[i] > noise:
                    noise = scoreListF[i]
            for j in range(len(scoreListF)):
                if scoreListF[j] <= noise*1.25:
                    scoreListF[j] = 1
        except IndexError:
            pass
        # Smooth over the data multiple times
        smoothedScoresF = savitzky_golay(scoreListF, 51, 2, deriv = 0, \
                                         rate = 1, returnScoreList = True)
        for iteration in range(3):
            smoothedScoresF = savitzky_golay(smoothedScoresF, 71, 2, deriv = 0, \
                                             rate = 1, returnScoreList = True)
        peaksF = savitzky_golay(smoothedScoresF, 51, 1, deriv = 0, \
                                rate = 1, returnScoreList = False)
        # Add all of the smoothed peaks to list of all peaks
        peaksFAdj = list(seed + np.array(peaksF))
        allPeaks += peaksFAdj

    # Covers the case where the seed is 0
    if not scoreListR:
        smoothedScoresR = []
    # Do the same-ish thing for the reverse peaks
    else:
        noise = 0
        try:
            for i in range(100):
                if scoreListR[i] > noise:
                    noise = scoreListR[i]
            for j in range(len(scoreListR)):
                if scoreListR[j] <= noise*1.15:
                    scoreListR[j] = 1
        except IndexError:
            pass
        smoothedScoresR = savitzky_golay(scoreListR, 51, 2, deriv = 0, \
                                         rate = 1, returnScoreList = True)
        for iteration in range(3):
            smoothedScoresR = savitzky_golay(smoothedScoresR, 71, 2, deriv = 0, \
                                             rate = 1, returnScoreList = True)
        peaksR = savitzky_golay(smoothedScoresR, 51, 1, deriv = 0, \
                                rate = 1, returnScoreList = False)
        peaksRAdj = list(seed - np.array(peaksR))
        allPeaks += peaksRAdj

    # calculates the median distance between detected peaks
    forMedian = []
    for i in range(len(allPeaks) - 1):
        forMedian.append(allPeaks[i + 1] - allPeaks[i])
    forMedian = [rounding(x, 50) for x in forMedian]
    medianDistance = np.median(forMedian)
    return sorted(list(set(allPeaks))), medianDistance

def split_SW(name, seq1, seq2, rc):
    '''
    I think there's some redundancy here that I can change or make more efficient
    '''
    for step in range(0, len(seq1), 1000):
        seq3 = seq1[step:min(len(seq1), step + 1000)]
        seq4 = seq2[:1000]

        align_file1 = open('seq3.fasta', 'w')
        align_file1.write('>' + name + '\n' + seq3 + '\n')
        align_file1.close()
        align_file2 = open('seq4.fasta', 'w')
        align_file2.write('>' + name + '\n' + seq4 + '\n')
        align_file2.close()

        diagonal = 'no'
        if step == 0 and not rc:
            diagonal = 'yes'

        x_limit1 = len(seq3)
        y_limit1 = len(seq4)

        os.system('%s -asequence seq3.fasta -bsequence seq4.fasta\
                  -datafile EDNAFULL -gapopen 25 -outfile align.whatever \
                  -gapextend 1  %s %s %s >./sw.txt 2>&1' \
                  %(water, diagonal, x_limit1, y_limit1))
        matrix_file = 'SW_PARSE.txt'
        diag_set, diag_dict = parse_file(matrix_file, rc, len(seq1), step)
        os.system('rm SW_PARSE.txt')

    diag_set = sorted(list(diag_set))
    plot_list = []
    for diag in diag_set:
        plot_list.append(diag_dict[diag])
    return plot_list

def parse_file(matrix_file, rc, seq_length, step):
    '''
    matrix_file : watHerON output file
    rc : bool, not sure what it is <- I don't think this is even doing anything
    seq_length : int, length of the sequence
    step : int, some position
    Returns:
        diag_set : set, positions
        diag_dict : dict, position : diagonal alignment scores
    '''
    diag_dict, diag_set = {}, set()
    for line in open(matrix_file):
        line = line.strip().split(':')
        position = int(line[0]) + step
        if not rc: # this will always happen
            position = np.abs(position)
        value = int(line[1]) # actual score
        diag_set.add(position)
        try:
            diag_dict[position] += value
        except:
            diag_dict[position] = value
    return diag_set, diag_dict

def determine_consensus(name, seq, peaks, qual, median_distance):
    '''Aligns and returns the consensus'''
    repeats = ''
    corrected_consensus = ''
    if median_distance > 500 and len(peaks) > 1:
        out_F = temp_folder + '/' + name + '_F.fasta'
        out_Fq = temp_folder + '/' + name + '_F.fastq'
        poa_cons = temp_folder + '/' + name + '_consensus.fasta'
        final = temp_folder + '/' + name + '_corrected_consensus.fasta'
        overlap = temp_folder +'/' + name + '_overlaps.sam'
        pairwise = temp_folder + '/' + name + '_prelim_consensus.fasta'

        repeats = split_read(peaks, seq, out_F, qual, out_Fq, name)

        PIR = temp_folder + '/' + name + 'alignment.fasta'
        os.system('%s -read_fasta %s -hb -pir %s -do_progressive %s >./poa_messages.txt 2>&1' %(poa, out_F, PIR, score_matrix))
        reads = read_fasta(PIR)

        if repeats == '2':
            Qual_Fasta = open(pairwise, 'w')
            for read in reads:
                if 'CONSENS' not in read:
                    Qual_Fasta.write('>' + read + '\n' + reads[read] + '\n')
            Qual_Fasta.close()
            os.system('%s %s %s %s >> %s' %(consensus, pairwise, out_Fq, name, poa_cons))

        else:
            for read in reads:
              if 'CONSENS0' in read:
                out_cons_file = open(poa_cons, 'w')
                out_cons_file.write('>' + name + '\n' + reads[read].replace('-', '') + '\n')
                out_cons_file.close()

        os.system('%s --secondary=no -ax map-ont %s %s > %s 2> ./minimap2_messages.txt'% (minimap2, poa_cons, out_Fq, overlap))
        os.system('%s --sam --bq 0 -t 1 %s %s %s %s > ./racon_messages.txt 2>&1' %(racon,out_Fq, overlap, poa_cons, final))

        reads = read_fasta(final)
        for read in reads:
            corrected_consensus = reads[read]

    return corrected_consensus, repeats

def read_fastq_file(seq_file):
    '''
    Takes a FASTQ file and returns a list of tuples
    In each tuple:
        name : str, read ID
        seed : int, first occurrence of the splint
        seq : str, sequence
        qual : str, quality line
        average_quals : float, average quality of that line
        seq_length : int, length of the sequence
    '''
    read_list = []
    length = 0
    for line in open(seq_file):
        length += 1
    lineNum = 0
    seq_file_open = open(seq_file, 'r')
    while lineNum < length:
        name_root = seq_file_open.readline().strip()[1:].split('_')
        name, seed = name_root[0], int(name_root[1])
        seq = seq_file_open.readline().strip()
        plus = seq_file_open.readline().strip()
        qual = seq_file_open.readline().strip()
        quals = []
        for character in qual:
            number = ord(character) - 33
            quals.append(number)
        average_quals = np.average(quals)
        seq_length = len(seq)
        read_list.append((name, seed, seq, qual, average_quals, seq_length))
        lineNum += 4
    return read_list

def analyze_reads(read_list):
    '''
    Takes reads that are longer than 1000 bases and gives the consensus.
    Writes to R2C2_Consensus.fasta
    '''
    for name, seed, seq, qual, average_quals, seq_length in read_list:
        if 1000 < seq_length:
            final_consensus = ''
            # score lists are made for sequence before and after the seed
            score_lists_f = split_SW(name, seq[seed:], seq[seed:], False)
            score_lists_r = split_SW(name, revComp(seq[:seed]), revComp(seq[:seed]), False)
            # calculate where peaks are and the median distance between them
            peaks, median_distance = callPeaks(score_lists_f, score_lists_r, seed)
            print(name, seq_length, peaks)
            final_consensus, repeats1 = determine_consensus(name, seq, peaks, qual, median_distance)
            # output the consensus sequence
            if final_consensus:
                final_out = open(out_file, 'a')
                final_out.write('>' + name + '_' + str(round(average_quals, 2)) + '_' + str(seq_length) + '_' + str(repeats1) + '_' + str(len(final_consensus)))
                final_out.write('\n' + final_consensus + '\n')
                final_out.close()
                os.system('rm -rf ' + temp_folder)

def main():
    '''Controls the flow of the program'''
    final_out = open(out_file, 'w')
    final_out.close()
    print(input_file)
    read_list = read_fastq_file(input_file)
    analyze_reads(read_list)

if __name__ == '__main__':
    main()
