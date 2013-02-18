#!/usr/bin/env python
import mutagen
import mutagen.easyid3
import mutagen.easymp4
import mutagen.flac
import mutagen.id3
import os
import argparse
import tempfile
import mimetypes
import collections

mimetypes.init()
mimetypes.add_type('image/jpg', 'jpeg')

keys = ['genre', 'date', 'discnumber', 'artist', 'title', 'album', 'tracknumber']


def easymp4_cover_art(self, key):
    if 'covr' in self:
        return self['covr'][0]


def easyid3_cover_art(self, key):
    pictures = self.getall('APIC')
    if pictures:
        return pictures[0]

mutagen.easymp4.EasyMP4.RegisterKey('cover', getter=easymp4_cover_art)
mutagen.easyid3.EasyID3.RegisterKey('cover', getter=easyid3_cover_art)
taggers = {'mp3': mutagen.easyid3.EasyID3, 'flac': mutagen.flac.FLAC, 'm4a': mutagen.easymp4.EasyMP4}

def flatten(value):
    return value.pop()

def normalize_numbers(value):
    value = flatten(value)
    # '2/14' or '2' -> '2'
    value = value.split('/', 1).pop()
    try:
        return int(value)
    except ValueError as e:
        return None
    pass

def clean_keys(tag):
    tags = dict()
    for key in keys:
        if key in tag:
            tags[key] = normalize_funcs[key](tag[key])
        else:
            print 'Failed to find %s in %s' % (key, tag.filename)
            pass
        pass
    return tags

normalize_funcs = collections.defaultdict(lambda: flatten, {'tracknumber': normalize_numbers, 'discnumber': normalize_numbers})

def extract_data(tag):
    if type(tag) == mutagen.easymp4.EasyMP4:
        if 'cover' in tag:
            picture = tag['cover']
            exts = { picture.FORMAT_JPEG: '.jpeg', picture.FORMAT_PNG: '.png' }
            return ((picture, exts[picture.imageformat]), clean_keys(tag))
        else:
            return (None, clean_keys(tag))
        pass
    if type(tag) == mutagen.easyid3.EasyID3:
        if 'cover' in tag:
            picture = tag['cover']
            ext = mimetypes.guess_extension(picture.mime)
            return ((picture.data, ext), clean_keys(tag))
        else:
            return (None, clean_keys(tag))
        pass
    if type(tag) == mutagen.flac.FLAC:
        if tag.pictures:
            picture = tag.pictures[0]
            ext = mimetypes.guess_extension(picture.mime)
            return ((picture.data, ext), clean_keys(tag))
        else:
            return (None, clean_keys(tag))
    pass


def tag(filename):
    ext = os.path.splitext(filename)[1].strip('.')
    # Find the tagging class to be used.
    try:
        tagger = taggers[ext]
    except KeyError as e:
        return (None, None)
    
    try:
        tags = tagger(filename)
        pass
    except mutagen.id3.ID3NoHeaderError as e:
        return (None, None)
    return extract_data(tags)
    pass
