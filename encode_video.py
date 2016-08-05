#!/usr/bin/env python3

import argparse
import glob
import os
import re
import shlex
import subprocess
import sys
import tempfile


try:
    import yaml
except ImportError:
    sys.exit("You need to install PyYaml for this to work.")


class Opts(object):
    pass


def load_settings(series):
    try:
        script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        yaml_loc = os.path.join(script_dir,"encoder.yaml")
        with open(yaml_loc) as y:
            all_settings = yaml.load(y)
    except IOError:
        sys.exit("Cannot load encoder.yaml, cannot continue.")

    settings = all_settings['Global']
    try:
        settings.update(all_settings['Series'][series])
    except KeyError:
        print('No entry for series "{0}" in encoder.yaml, the available options are:'.format(series))
        for series in all_settings['Series']:
            print(series)
        raise SystemExit

    return settings

def fix_windows_paths(path_in):
    return re.sub(r'\\', '/', path_in)

def get_vid_info(settings):
    type = settings['type']
    info_cmd =  '{0} -i -a "type={1}" -a "src_vid={2}" {3} -'.format(
        settings['vspipe'], type, settings['vid_in'], settings['script_in'])
    iargs = shlex.split(info_cmd)
    finfo_raw = subprocess.check_output(iargs)
    finfo_raw = finfo_raw.decode('utf-8')
    finfo_lines = finfo_raw.split('\n')
    finfo = {}
    for line in finfo_lines:
        parts = line.split(": ")
        if len(parts) > 1:
            finfo[parts[0]] = parts[1]
    return finfo
    
# c:\enc_tools\vspipe64.exe -i -a type=hd -a "src_vid=c:\\users\\chris\\documents\\gobus\\test_lossless.mp4" c:\\users\\chris\\documents\\gobus\\test-out.vpy -

#py -3 encode_video.py zyuoh "c:\users\chris\documents\gobus\test_lossless.mp4" "c:\users\chris\documents\gobus\test-out.vpy" hd

def encode_video(settings):
    type = settings['type']
    pipe_cmd = "{0} -y -a 'type={1}' -a 'src_vid={2}'".format(
        settings['vspipe'], type, settings['vid_in'])
    if settings['subs']:
        pipe_cmd += ' -a "subtitles={0}"'.format(settings['subs'])
    pipe_cmd += ' {0} -'.format(settings['script_in'])
    
    if settings[type + '_depth_out'] == 8:
        encoder = settings['x264_8']
    else:
        encoder = settings['x264_10']
    enc_opts = settings[type + '_opts'].strip()
    frame_info = get_vid_info(settings)
    enc_cmd = "{0} {1} --demuxer y4m - -o {2} --frames {3}".format(
        encoder, enc_opts, settings['vid_out'], frame_info['Frames'])
    if settings['qpfile']:
        enc_cmd += ' --qpfile {}'.format(settings['qpfile'])
    #preprin(settings)
    sys.exit("{} | {}".format(pipe_cmd, enc_cmd))
    

    
def split_and_blind_call(cmd, is_python=False, is_shell=False):
    if is_shell:
        cmd = cmd.replace('/','\\\\')
    args = shlex.split(cmd)
    sys.exit(' '.join(args))
    if is_python:
        args.insert(0, sys.executable)
    f = subprocess.Popen(args, shell=is_shell)
    f.wait()


def preprin(foo):
    """Debug printing. It's not worth importing always, and lazier to type as needed."""
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(foo)


if __name__ == "__main__":
    # Build the menu.
    parser = argparse.ArgumentParser(description="Commands to automate the crap out of encoding")
    parser.add_argument('series', help="Series name, corresponding to series top level in encoder.yaml")
    parser.add_argument('vid_in', help="Lossless video filename")
    parser.add_argument('script_in', help="Name of vpy script with final processing commands")
    parser.add_argument('enc_type', help="Which set of encoder commands to run?")
    parser.add_argument('-d', '--depth', dest='enc_depth', type=int, choices=[8,10], help="Use standard x264 or x264-10bit?")
    parser.add_argument('--version', action='version', version='0.0001')
    parser.add_argument('-s', '--subtitles', dest="subs", help="Filename of ass script.")
    parser.add_argument('-c', '--tcfile', dest="tc", help="External timecodes file for HD/SD encodes.")
    parser.add_argument('-o', '--ouput', dest='vid_out', help="Filename to encode to.")
    parser.add_argument('-q', '--qpfile', dest='qpfile', help='QPFile to use.')
    args = parser.parse_args(namespace=Opts)

    # Grab the settings from the yaml based on input
    settings = load_settings(Opts.series)

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

    # shlex.split posix=False doesn't really work for some reason
    # this is easier
    if os.name == 'posix':
        settings['subs'] = Opts.subs
        settings['qpfile'] = Opts.qpfile
        settings['script_in'] = Opts.script_in
        settings['vid_in'] = Opts.vid_in
    elif os.name == 'nt':
        settings['subs'] = fix_windows_paths(Opts.subs)
        settings['qpfile'] = fix_windows_paths(Opts.qpfile)
        settings['script_in'] = fix_windows_paths(Opts.script_in)
        settings['vid_in'] = fix_windows_paths(Opts.vid_in)

        
    if not Opts.vid_out:
        settings['vid_out'] = '{0}.{1}.mkv'.format(os.path.splitext(settings['vid_in'])[0], Opts.enc_type)
    else:
        settings['vid_out'] = Opts.vid_out
    
    

    
    encode_video(settings)
