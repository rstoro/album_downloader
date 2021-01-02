#!/usr/bin/env python3


from os import listdir as os_listdir
from os import mkdir as os_mkdir
from os import remove as os_remove
from os.path import isfile as os_path_isfile
from os.path import isdir as os_path_isdir
from os.path import exists as os_path_exists
from subprocess import call as subprocess_call
from argparse import ArgumentParser
from re import match as re_match
from re import compile as re_compile
from re import escape as re_escape
from youtube_dl import YoutubeDL


class UrlValidationException(Exception): pass


def validate_url(url):
    url_validation_regex = r'(?:http|https):\/\/www\.youtube\.com\/watch\?v=.+'
    compiled_url_validation_regex = re_compile(url_validation_regex)
    if not re_match(compiled_url_validation_regex, url):
        message = f'Url {url} is not a valid Youtube link.'
        raise UrlValidationException(message)


def download_url(url):
    # get metadata to format the filename and see if chapters exist
    with YoutubeDL() as ydl:
        info_dict = ydl.extract_info(url, download=False)
        tracklist = info_dict.get('chapters', None)
        title = info_dict.get('title', None)

    # NOTE: we do not know the extension until YoutubeDL downloads the file
    #       because we are downloading the highest audio quality which varies 
    # create the options for audio download, and progress hooks
    ydl_opts = { 'format': 'bestaudio/best', 'outtmpl': f'{title}' + '.%(ext)s' }

    # download the audio
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([ url ])

    # split album if tracklist exists
    if tracklist:
        # get album path
        album_path = get_album_path(title)

        # split
        split_album(album_path, tracklist)

        # clean-up
        os_remove(album_path)


def get_album_path(album_name_without_extension):
    # NOTE: download is relative to the directory the program is run in
    match = re_compile(f'{re_escape(album_name_without_extension)}\..+')
    album_path = next( f 
            for f in os_listdir('.') 
            if os_path_isfile(f) 
            and re_match(match, f) )

    return album_path


def split_album(album_path, tracklist):
    # get the unknown extension
    album_name, album_extension = album_path.rsplit('.', 1)

    # create new directory if it does not already exist
    if not os_path_exists(album_name) or not os_path_isdir(album_name):
        os_mkdir(album_name)

    # create reusable, formattable string 
    unformatted_cmd = ' '.join([ 
            f'ffmpeg -i "{album_path}"', 
            '-acodec copy',
            '-ss {start_time}', 
            '-to {end_time}', 
            (f'"{album_name}/' + '{i} - {title}' + f'.{album_extension}"') ])

    # create and call the subprocess for each track
    for index, track in enumerate(tracklist):
        start_time = track.get('start_time', None)
        end_time = track.get('end_time', None)
        title = track.get('title', None)

        # used to keep chapter order
        index_pad_len = len(str(len(tracklist)))

        cmd = unformatted_cmd.format(start_time=start_time, 
                end_time=end_time, i=str(index).zfill(index_pad_len), title=title)
        subprocess_call(cmd, shell=True)
    

def parse_args():
    program_description = ( 'Used to download an album from YouTube and split it' + 
            'into seperate audio tracks using FFMPEG.' )

    parser = ArgumentParser(description=program_description)
    parser.add_argument('-u', '--url', required=True,
            action='store', dest='download_url', default=None, 
            help='the url to be downloaded.')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    # parse args and add the description and arguments for -h/--help
    args = parse_args()

    # download url
    url = args.download_url
    download_url(url)


