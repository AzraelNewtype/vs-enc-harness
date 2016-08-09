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

    
def mux_mp4(settings, group, real_aud, real_vid):
    ep_num = settings['epnum']
    type = settings['type']
    
    try:
        if ep_num and settings[type + '_suffix']:
            out_ep_num = '{}{}'.format(ep_num, settings[type + '_suffix'])
        elif settings[type + '_suffix']:
            out_ep_num = ' {}'.format(settings[type + '_suffix'])
        else:
            out_ep_num = ep_num
    except KeyError:
        out_ep_num = ep_num
       
    if settings["ver"] and ep_num:
	    out_ep_num = " - {0}v{1}".format(out_ep_num, settings["ver"])
    elif settings['ver']:
        out_ep_num = '{}v{}'.format(out_ep_num, settings['ver'])
    elif ep_num:
	    out_ep_num = ' - {0}'.format(out_ep_num)
        
    out_name = "[{0}] {1}{2}.mp4".format(group, settings["full_name"], out_ep_num)
    
    if settings['directory']:
        out_name_with_path = '{}/{}'.format(settings['directory'], out_name)
    else:
        out_name_with_path = out_name
    
    
    cmd = '"{0}/remuxer" -o "{1}"'.format(settings["l-smash_bin_path"], out_name_with_path)
    
    if settings['vid_in']:
        cmd += video_track_args(settings, type, real_vid)
    if settings['aud_in']:
        cmd += audio_track_args(settings, type, real_aud)
    if settings['chapters']:
        cmd += ' --chapter "{0}"'.format(settings['chapters'])

    if settings['pretend']:
        print("==GENERATED COMMAND==")
        print(cmd)
    else:
        args = shlex.split(cmd)
        try:
            subprocess.check_call(args)
        except subprocess.CalledProcessError as e:
            print('Failed to mux: {}'.format_cmd())
            sys.exit(e)
            
    return out_name

def video_track_args(settings, type, video):
    try:
        lang = settings[type + '_video_lang']
    except KeyError:
        lang = 'und'
    vid = ' -i "{}"?1:language={}'.format(video, lang)
    return vid
    
def audio_track_args(settings, type, audio):
    try:
        lang = settings[type + '_audio_lang']
    except KeyError:
        lang = 'und'
    aud = ' -i "{}"?1:language={}'.format(audio, lang)
    return aud

def check_and_prep_audio(aud_in, pretend):
    if pretend:
        print("====AUDIO CMDS====")
    aud_parts = os.path.splitext(aud_in)
    if aud_parts[1] == '.mka':
        ready_audio = repack_mka(
            aud_in, settings['mkvmerge'], settings['mkvextract'], settings['l-smash_bin_path'],
            pretend)
    elif aud_parts[1] in ['.mp4', '.m4a']:
        ready_audio = aud_in
    elif aud_parts[1] in ['.aac', '.mp3', '.wma', '.ac3']:
        ready_audio = mux_m4a(settings['l-smash_bin_path'], aud_in, pretend)
    return ready_audio
    
def check_and_prep_video(settings, pretend):
    if pretend:
        print("====VIDEO CMDS====")
    vid_parts = os.path.splitext(settings['vid_in'])
    if vid_parts[1] == '.mkv':
        return repack_mkv(
            settings['vid_in'], settings['mkvmerge'], settings['mkvextract'], 
            settings['l-smash_bin_path'], pretend)
    elif vid_parts[1] in ['.mp4', '.m4v']:
        return settings['vid_in']
    elif vid_parts[1] == '.264':
        if not settings['fps']:
            sys.exit('You are attempting to mux raw h.264 video without specifying fps')
        return mux_m4v(
            settings['l-smash_bin_path'], settings['vid_in'], settings['fps'], pretend)
    else:
        sys.exit('You have provided video that we cannot mux.')
        
        
def repack_mkv(vid_in, mkvmerge, mkvextract, lsmash_dir, pretend):
    ident = subprocess.check_output([mkvmerge, "--identify-for-mmg", vid_in])
    vinfo = vu.get_arbitrary_vid_info(settings)
    fps_str = vinfo['FPS'].split(' ')[0]
    identre = re.compile("Track ID (\d+): video")
    ret = identre.search(ident.decode(sys.getfilesystemencoding())) if ident else None
    if ret:
        tid = ret.group(1)
    else:
        sys.exit('idk yo')
    extract_cmd = '{} tracks {} {}:tmp'.format(mkvextract, vid_in, tid)
    if pretend:
        print(extract_cmd)
    else:
        args = shlex.split(extract_cmd)
        subprocess.run(args)
    settings['cleanup'].append('tmp')
    return mux_m4v(lsmash_dir, 'tmp', fps_str, pretend)
    
def mux_m4v(lsmash, infile, fps, pretend):
    outfile = 'tmp.m4v'
    remux_cmd = '{}/muxer -i {}?fps={} -o {}'.format(lsmash, infile, fps, outfile) 
    if pretend:
        print(remux_cmd)
    else:
        args = shlex.split(remux_cmd)
        subprocess.run(args)
    settings['cleanup'].append(outfile)
    return outfile
    

def repack_mka(infile, mkvmerge, mkvextract, lsmash_dir, pretend):
    ident = subprocess.check_output([mkvmerge, "--identify-for-mmg", infile])
    codecre = re.compile('codec_id:(\w+) ')
    ret = codecre.search(ident.decode(sys.getfilesystemencoding()))
    if ret:
        codec = ret.group(1)
    else:
        sys.exit("This doesn't appear to have an audio track")
    # print(ret.group(2))
    if codec not in ['A_AAC', 'A_AC3', 'A_MP3', 'A_WMA']:
        sys.exit('Currently this script will not try and stuff that kind of file into m4a')

    identre = re.compile("Track ID (\d+): audio( \(AAC\) \[aac_is_sbr:true\])?")
    ret = (identre.search(ident.decode(sys.getfilesystemencoding())) if ident else None)

    if ret:
        tid = ret.group(1)
    else:
        sys.exit('Audio in does not actually contain aac')
    extract_cmd = '{} tracks {} {}:tmp'.format(mkvextract, infile, tid)
    if pretend:
        print(extract_cmd)
    else:
        args = shlex.split(extract_cmd)
        subprocess.run(args)
    settings['cleanup'].append('tmp')
    sbr = ret.group(2)
    muxer_input = 'tmp'
    if codec == 'A_AAC' and sbr:
        muxer_input += '?sbr'
    
    return mux_m4a(lsmash_dir, muxer_input, pretend)
    
def mux_m4a(lsmash, infile, pretend):
    # Why yes, I do mean always output the same filename, because this
    # is in intermediary that should get nuked
    outfile = 'tmp.m4a'
    remux_cmd = '{}/muxer -i {} -o {}'.format(lsmash, infile, outfile) 
    if pretend:
        print(remux_cmd)
    else:
        args = shlex.split(remux_cmd)
        subprocess.run(args)
    settings['cleanup'].append(outfile)
    return outfile

if __name__ == "__main__":
    #Build the menu.
    parser = argparse.ArgumentParser(description="Commands to automate mp4 muxing")
    parser.add_argument('series', help="Series name, corresponding to series top level in encoder.yaml")
    parser.add_argument('enc_type', help="Which set of config lines to read")
    parser.add_argument('-i', '--video-in', dest='video_in', help="Video track to mux")
    parser.add_argument('-a', '--audio-in', dest='audio_in', help="Audio track to mux")
    parser.add_argument('-e', '--epnum', type=int, help="Episode number, if applicable")
    parser.add_argument('-f', '--fps', help="FPS for raw video stream")
    parser.add_argument('-d', '--directory', help='Directory to write output to')
    parser.add_argument('-p', '--prefix', help="Override output filename prefix")
    parser.add_argument('-c', '--chapters', help="Chapters file to mux")
    #parser.add_argument('-s', '--script', dest="script", help="Filename of subtitles to mux")
    parser.add_argument('-V', '--release-version', dest="ver", help="Release version number")
    parser.add_argument('--version', action='version', version='0.00000000001')
    parser.add_argument('--pretend', action='store_true', default=False)
    args = parser.parse_args(namespace=Opts)
    
    #Grab the settings from the yaml based on input
    settings = vu.load_settings(Opts.series)
    
    settings['cleanup'] = []
    
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
        settings['script'] = Opts.script
        settings['vid_in'] = Opts.video_in
        settings['aud_in'] = Opts.audio_in
    elif os.name == 'nt':
        settings['chapters'] = vu.fix_windows_paths(Opts.chapters)
        settings['directory'] = vu.fix_windows_paths(Opts.directory)
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
    
    if Opts.audio_in:
        ready_audio = check_and_prep_audio(settings['aud_in'], Opts.pretend)
    if Opts.video_in:
        ready_video = check_and_prep_video(settings, Opts.pretend)
    
    final_name = mux_mp4(settings, group, ready_audio, ready_video)
    cleanup_set = set(settings['cleanup'])

    if not Opts.pretend:
        for file in cleanup_set:
            os.remove(file)
    else:
        print("=FILES TO CLEANUP=")
        if cleanup_set:
            for file in cleanup_set:
                print('- {}'.format(file))
        else:
            print('NONE')
    print(final_name)
