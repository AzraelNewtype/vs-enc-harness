#!/usr/bin/env python3

import argparse
import os
import re
import shlex
import subprocess
import sys
import videoutilities as vu


class Opts(object):
    pass

    
def mux_matroska(settings, group):
    ep_num = settings['epnum']
    type = settings['type']
    
    if settings["ver"] and ep_num:
	    out_ep_num = " - {0}v{1}".format(ep_num, settings["ver"])
    elif settings['ver']:
        out_ep_num = ' v{}'.format(settings['ver'])
    elif ep_num:
	    out_ep_num = ' - {0}'.format(ep_num)
    else:
        out_ep_num = ''
    out_name = "[{0}] {1}{2}.mkv".format(group, settings["full_name"], out_ep_num)
    
    if settings['directory']:
        out_name = '{}/{}'.format(settings['directory'], out_name)
    
    cmd = '"{0}" -o "{1}"'.format(settings["mkvmerge"], out_name)

    if settings['vid_in']:
        finfo = vu.get_arbitrary_vid_info(settings)
        res = '{}x{}'.format(finfo['Width'], finfo['Height'])
        cmd += video_track_args(settings, res, type)
    if settings['aud_in']:
        cmd += audio_track_args(settings, type)
    if settings['vid_in'] and settings['aud_in']:
        cmd += ' "--track-order" "0:0,1:0"'
    if settings['chapters']:
        cmd += ' "--chapters" "{0}"'.format(settings['chapters'])
    try:
        if settings[type + '_mux_fonts']:
            cmd += mux_fonts_cmd(settings['fonts'])
    except KeyError:
        pass
    if settings['pretend']:
        print("==GENERATED COMMAND==")
        print(cmd)
    else:
        args = shlex.split(cmd)
        try:
            subprocess.check_call(args)
        except CalledProcessError as e:
            print('Failed to mux: {}'.format_cmd())
            sys.exit(e)
            
    return out_name

def video_track_args(settings, res, type):
    try:
        lang = settings[type + '_video_lang']
    except KeyError:
        lang = 'und'
    vid = ' "--language" "0:{}" "--default-track" "0:yes" "--forced-track" "0:no"'.format(
        lang)
    if settings['tags']:
        vid += ' "--tags" "0:{}"'.format(settings['tags'])
    vid += ' "--display-dimensions" "0:{}" "-d" "0" "-A" "-S" "-T"'.format(res)
    vid += ' "--no-global-tags" "--no-chapters" "{}"'.format(settings['vid_in'])
    return vid
    
def audio_track_args(settings, type):
    try:
        lang = settings[type + '_audio_lang']
    except KeyError:
        lang = 'und'
    aud = ' "--language" "0:{}" "--default-track" "0:yes" "--forced-track" "0:no"'.format(lang)
    aud += ' "-a" "0" "-D" "-S" "-T" "--no-global-tags" "--no-chapters" "{0}"'.format(
        settings['aud_in'])
    return aud

def mux_fonts_cmd(fonts):
    font_switches = ""
    for font in fonts:
        font_switches += ' --attachment-mime-type application/x-truetype-font'
        font_switches += ' --attachment-name "{0}"'.format(os.path.basename(font))
        font_switches += ' --attach-file "{0}"'.format(font)
    return font_switches


if __name__ == "__main__":
    #Build the menu.
    parser = argparse.ArgumentParser(description="Commands to automate matroska muxing")
    parser.add_argument('series', help="Series name, corresponding to series top level in encoder.yaml")
    parser.add_argument('enc_type', help="Which set of config lines to read?")
    parser.add_argument('-i', '--video-in', dest='video_in', help="Video track to mux")
    parser.add_argument('-a', '--audio-in', dest='audio_in', help="Audio track to mux")
    parser.add_argument('-e', '--epnum', type=int, help="Episode number, if applicable")
    parser.add_argument('-d', '--directory', help='Directory to write output to')
    parser.add_argument('-p', '--prefix', help="Override output filename prefix")
    parser.add_argument('-c', '--chapters', help="Chapters file to mux")
    parser.add_argument('-s', '--script', dest="script", help="Filename of subtitles to mux")
    parser.add_argument('-V', '--release-version', dest="ver", help="Release version number")
    parser.add_argument('--tags', help="Tags file for video trickery.")
    parser.add_argument('--version', action='version', version='0.00000000001')
    parser.add_argument('--pretend', action='store_true', default=False, help="Display command, don't run it")
    args = parser.parse_args(namespace=Opts)

    #Grab the settings from the yaml based on input
    settings = vu.load_settings(Opts.series)
    if Opts.prefix:
        group = Opts.prefix
    else:
        group = settings[Opts.enc_type + '_prefix']
        
    settings['pretend'] = Opts.pretend

    settings["ver"] = Opts.ver
    settings['type'] = Opts.enc_type
    
    if os.name == 'posix':
        settings['chapters'] = Opts.chapters
        settings['directory'] = Opts.directory
        settings['tags'] = Opts.tags
        settings['script'] = Opts.script
        settings['vid_in'] = Opts.video_in
        settings['aud_in'] = Opts.audio_in
    elif os.name == 'nt':
        settings['chapters'] = vu.fix_windows_paths(Opts.chapters)
        settings['directory'] = vu.fix_windows_paths(Opts.directory)
        settings['tags'] = vu.fix_windows_paths(Opts.tags)
        settings['script'] = vu.fix_windows_paths(Opts.script)
        settings['aud_in'] = vu.fix_windows_paths(Opts.audio_in)
        settings['vid_in'] = vu.fix_windows_paths(Opts.video_in)

    if not Opts.prefix:
        prefix = ""
    else:
        prefix = Opts.prefix

    if Opts.epnum and (Opts.epnum < 10):
        epnum = "0" + str(Opts.epnum)
    elif Opts.epnum:
        epnum = str(Opts.epnum)
    else:
        epnum = None
    settings['epnum'] = epnum
    if not Opts.script:
        settings["script"] = ""
    else:
        settings["script"] = Opts.script
    
    #vu.preprin(settings)
    print(mux_matroska(settings, group))