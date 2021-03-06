from Bio.Alphabet import generic_dna
import logging

class PseudoMSA:
    """
    This class represents a pseudo Multiple Sequence alignment
    That will be build from a BLAST result and having the following
    properties:
    - columns having GAPS in the query are removed
    - subjects having several hsps are merged in the
    same sequence, filled with gaps around
    """

    query_id = ""
    query_seq = ""
    blast_prog = ""
    # Subject Sequences without insertions compared to query sequence
    sequences = dict()  # Dict: key: seqname, value: sequence
    # insertions: key=seqname, value=array of insertions
    # If there is an insertion in the subject (gap in the query)
    # then the insertion is appended at the given position in this
    # array
    insertions=dict()
    starts=dict()
    ends=dict()
    scores = dict()  # Dict: key: seqname, value: blast score
    frame = 0

    def __init__(self, query_id, query_seq, query_seq_bk, frame, blast_prog):
        """
        query : blast query sequence without gaps
        """
        self.query_id = str(query_id)
        self.query_seq = list(query_seq)
        self.query_seq_bk = query_seq_bk
        self.frame = frame
        self.blast_prog = blast_prog
        # For croping query sequence at the end
        # (only for blastx because we translate it)

    def add_hsp(self, sbjct_name, hsp):
        """
        sbjct_name: name of the subject sequence
        hsp: Bio.Blast.Record.HSP
        """
        if ((self.blast_prog != "blastx" and self.blast_prog != "tblastx")  or hsp.frame[0] == self.frame):
            seq = self.sequences.get(str(sbjct_name))
            ins = self.insertions.get(str(sbjct_name))
            sco = self.scores.get(str(sbjct_name))
            if seq is None:
                seq = ["-"] * len(self.query_seq)
            if sco is None:
                sco = 0
            if ins is None:
                ins =  [""] * (len(self.query_seq) + 1)
            start = hsp.query_start

            if self.blast_prog=='blastx' or self.blast_prog=='tblastx':
                # Computing start on the translated query sequence
                if self.frame > 0:
                    start = (hsp.query_start - self.frame) / 3 + 1
                else:
                    start = (len(self.query_seq_bk) - hsp.query_end + 1 + self.frame) / 3 + 1

            position = start-1
            self.starts[str(sbjct_name)]=position
            gapstart = -1
            for p in range(0, len(hsp.sbjct)):
                # If no gap in the query at that position
                if hsp.query[p] != '-':
                    gapstart=-1
                    if hsp.sbjct[p] != '-':
                        seq[position] = hsp.sbjct[p]
                    position += 1
                else:
                    if gapstart==-1:
                        gapstart=position
                    ins[gapstart] += hsp.sbjct[p]
            self.ends[str(sbjct_name)]=position-1
            self.sequences[str(sbjct_name)] = seq
            self.insertions[str(sbjct_name)] = ins
            self.scores[str(sbjct_name)] = max(sco, hsp.score)

    def crop_alignment(self,maxseqs):
        """
        Will compute minstart and maxend to crop the query sequence
        to remove parts that are not covered by the n max score subject sequences
        useful with blastx when we need to translate the query sequence
        """
        minstart=-1
        maxend=0
        nseqs=0
        for key, value in sorted(self.scores.iteritems(), reverse=True, key=lambda (k,v): (v,k)):
            if nseqs >= maxseqs :
                break
            s=self.starts[str(key)]
            e=self.ends[str(key)]
            minstart = s if minstart==-1 or s<minstart else minstart
            maxend = e if e>maxend else maxend
            nseqs+=1
            
        ids = self.sequences.keys()
        for id in ids:
            seq = self.sequences[id]
            self.sequences[id] = seq[minstart:maxend+1]
            ins = self.insertions[id]
            self.insertions[id] = ins[minstart:maxend+2]
        self.query_seq = self.query_seq[minstart:maxend+1]

    def all_sequences(self):
        for id, seq in self.sequences.iteritems():
            yield (str(id), "".join(seq))

    def first_n_max_score_sequences(self, maxseqs):
        nseqs = 0
        for key, value in sorted(self.scores.iteritems(), reverse=True, key=lambda (k,v): (v,k)):
            if nseqs >= maxseqs :
                break
            else:
                seq = self.sequences.get(str(key))
                ins = self.insertions.get(str(key))
                fullseq = list(seq)
                fullseq[0] = ins[0] + fullseq[0]
                for i in range(1,len(ins)):
                    fullseq[i-1] += ins[i]
                yield (str(key), "".join(seq), "".join(fullseq))
                nseqs = nseqs+1

    def to_string(self):
        msa = ">%s\n%s\n" % (self.query_id, "".join(self.query_seq))
        for id, seq in self.sequences.iteritems():
            msa += ">%s\n%s\n" % (id, "".join(seq))
        return msa
