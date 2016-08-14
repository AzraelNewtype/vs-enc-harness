#!/usr/bin/env python3

import os
import re
import shlex
import subprocess
import sys
import tempfile
import videoutilities as vu

class TSStream(object):
    def __init__(self):
        self.tid = None
        self.str_type = None
        self.sid = None
        self.sinfo = None
        self.slang = None
        self.sdelay = None
    
    def __repr__(self):
        repr_str = ""
        repr_str += "Track ID: {};".format(self.tid) if self.tid else ''
        repr_str += " Stream Type: {};".format(self.str_type) if self.str_type else ''
        repr_str += " Stream ID: {};".format(self.sid) if self.sid else ''
        repr_str += " Stream Info: {};".format(self.sinfo) if self.sinfo else ''
        repr_str += " Stream Lang: {};".format(self.slang) if self.slang else ''
        repr_str += " Stream Delay: {};".format(self.sdelay) if self.sdelay else ''
        repr_str = repr_str[:-1]
        return repr_str

        
def demux_aac(ts):
    settings = vu.load_global_settings()
    tsm_path = settings['tsmuxer']  
    meta_s = generate_meta(os.path.realpath(ts), tsm_path)
    
    f = tempfile.NamedTemporaryFile(delete=False)
    try:
        f.write(bytearray(meta_s, sys.getfilesystemencoding()))
        f.close()
        print("Demuxing")
        outstr = subprocess.check_output([tsm_path, f.name, '.'])
        print("Demux complete.")
        outstr = outstr.decode(sys.getfilesystemencoding())
        outlines = outstr.split(os.linesep)
        outlines.pop()
        print(outlines.pop())
    finally:
        os.unlink(f.name)
    
         
def generate_meta(ts, tsm_path):
    if os.name == 'nt' and '\\' in ts:
        cmd_safe_ts = vu.fix_windows_paths(ts)
    else:
        cmd_safe_ts = ts
        
    real_tsm_output = subprocess.check_output([tsm_path, cmd_safe_ts])
    tsm_output_str = real_tsm_output.decode(sys.getfilesystemencoding())
    tsm_output_lines = tsm_output_str.split(os.linesep)

    streams = []
    delimitre = re.compile(':\s+')
    cur_stream = TSStream()
    for line in tsm_output_lines:
        if ':' in line:
            toks = delimitre.split(line, maxsplit = 1)
            if toks[0] == 'Track ID':
                streams.append(cur_stream)
                cur_stream = TSStream()
                cur_stream.tid = int(toks[1])
            elif toks[0] == 'Stream ID':
                cur_stream.sid = toks[1]
            elif toks[0] == 'Stream info':
                cur_stream.sinfo = toks[1]
            elif toks[0] == 'Stream ID':
                cur_stream.sid = toks[1]
            elif toks[0] == 'Stream lang':
                cur_stream.slang = toks[1]
            elif toks[0] == 'Stream delay':
                cur_stream.sdelay = int(toks[1])

    aac_streams = list(filter(lambda x: x.sid == 'A_AAC', streams))

    meta_s = "MUXOPT --demux\r\n"
    for s in aac_streams:
        meta_s += '{}, "{}",'.format(s.sid, ts)
        if s.sdelay:
            meta_s += ' timeshift={}ms,'.format(s.sdelay)
        meta_s += ' track={}\r\n'.format(s.tid)
    return meta_s
    

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Usage: {} [ts]'.format(__file__))

    ts = sys.argv[1]
    demux_aac(ts)