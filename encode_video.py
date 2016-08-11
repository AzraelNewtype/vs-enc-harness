#!/usr/bin/env python3

import argparse
import glob
import os
import shlex
import subprocess
import sys
import videoutilities as vu


class Opts(object):
    pass

          
def encode_video(settings):
    type = settings['type']
    pipe_cmd = "{0} -y -a 'type={1}'".format(settings['vspipe'], type)
    if settings['vid_in']:
        pipe_cmd += ' -a "src_vid={}"'.format(settings['vid_in'])
    if settings['subs']:
        pipe_cmd += ' -a "subtitles={0}"'.format(settings['subs'])
    pipe_cmd += ' {0} -'.format(settings['script_in'])
    # Better safe than sorry; use 8-bit if not specified
    try:
        if settings[type + '_depth_out'] == 8:
            encoder = settings['x264_8']
        else:
            encoder = settings['x264_10']
    except KeyError:
        encoder = settings['x264_8']
    enc_opts = settings[type + '_opts'].strip()
    frame_info = vu.get_vid_info(settings)
    enc_cmd = "{0} {1} --demuxer y4m - -o {2} --frames {3}".format(
        encoder, enc_opts, settings['vid_out'], frame_info['Frames'])
    if settings['qpfile']:
        enc_cmd += ' --qpfile {}'.format(settings['qpfile'])
    if settings['pretend']:
        print('=== Generated Command ===')
        print('{} | {}'.format(
            vu.display_windows_paths(pipe_cmd), 
            vu.display_windows_paths(enc_cmd)))
    else:
        vsp = subprocess.Popen(shlex.split(pipe_cmd), stdout=subprocess.PIPE, 
                               stderr=subprocess.DEVNULL)
        enc = subprocess.Popen(shlex.split(enc_cmd), stdin=vsp.stdout)
        vsp.stdout.close()
        enc.communicate()


if __name__ == "__main__":
    # Build the menu.
    parser = argparse.ArgumentParser(description="Commands to automate the crap out of encoding")
    parser.add_argument('series', help="Series name, corresponding to series top level in encoder.yaml")
    parser.add_argument('script_in', help="Name of vpy script with final processing commands")
    parser.add_argument('enc_type', help="Which set of encoder commands to run?")
    parser.add_argument('-i', '--source-video', dest='vid_in', help="Lossless video filename")
    parser.add_argument('-d', '--depth', dest='enc_depth', type=int, choices=[8,10], help="Use standard x264 or x264-10bit?")
    parser.add_argument('--version', action='version', version='0.0001')
    parser.add_argument('-s', '--subtitles', dest="subs", help="Filename of ass script.")
    parser.add_argument('-c', '--tcfile', dest="tc", help="External timecodes file for HD/SD encodes.")
    parser.add_argument('-q', '--qpfile', dest='qpfile', help='QPFile to use.')
    parser.add_argument('-o', '--ouput', dest='vid_out', help="Filename to encode to.")
    parser.add_argument('--pretend', action='store_true', default=False)
    args = parser.parse_args(namespace=Opts)
    
    # Grab the settings from the yaml based on input
    settings = vu.load_settings(Opts.series)
    
    settings['pretend'] = Opts.pretend
    settings['tc'] = Opts.tc
    settings['type'] = Opts.enc_type
    
    # It's okay if the config doesn't explicitly say the subs are/aren't required,
    # but if they did explicitly require, enforce it. A missing key is tacit lack
    # of requirement.
    try:
        if settings[ settings['type'] + '_requires_subs'] and not Opts.subs:
            sys.exit("This type needs subtitles that you haven't provided")
    except KeyError:
        pass

    try:
        if settings[settings['type'] + '_requires_source'] and not Opts.vid_in:
            sys.exit("This encode type requires a source video that you haven't provided")
    except KeyError:
        pass
    
    # shlex.split posix=False doesn't really work for some reason
    # this is easier
    if os.name == 'posix':
        settings['subs'] = Opts.subs 
        settings['qpfile'] = Opts.qpfile 
        settings['script_in'] = Opts.script_in
        settings['vid_in'] = Opts.vid_in
    elif os.name == 'nt':
        settings['subs'] = vu.fix_windows_paths(Opts.subs) 
        settings['qpfile'] = vu.fix_windows_paths(Opts.qpfile)
        settings['script_in'] = vu.fix_windows_paths(Opts.script_in)
        settings['vid_in'] = vu.fix_windows_paths(Opts.vid_in)

        
    if not Opts.vid_out:
        settings['vid_out'] = '{0}.{1}.mkv'.format(os.path.splitext(settings['vid_in'])[0], Opts.enc_type)
    else:
        settings['vid_out'] = Opts.vid_out
    
    

    
    encode_video(settings)
