import collections
import json
import random
import redis_wrap
import weakref
import os.path

class SongExists_Exception(Exception):
    def __init__(self, name, song):
        self.song = song
        self.name = name
        super(SongExists_Exception, self).__init__('Song {0} exists as {1}'.format(self.name, self.song.key))
        pass
    pass

class JSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        self._encoders = { 
            Album: self.__encode_album, 
            Artist: self.__encode_artist, 
            Song: self.__encode_song, 
            Library: self.__encode_library 
            }
        super(JSONEncoder, self).__init__(*args, **kwargs)
        pass
    def __encode_album(self, album):
        encoded = album.items()
        encoded.extend([('_key', album.key), 
                        ('songs', album.songs.values())])
        return dict(encoded)
    def __encode_artist(self, artist):
        encoded = artist.items()
        encoded.extend([('_key', artist.key), 
                        ('albums', artist.albums.values())])
        return dict(encoded)
    def __encode_song(self, song):
        encoded = song.items()
        encoded.append(('_key', song.key))
        encoded = dict(encoded)
        encoded['path'] = song.file_url
        return encoded
    def __encode_library(self, library):
        return {'artists': library.artists.values()}
    def default(self, obj):
        if type(obj) in self._encoders:
            return self._encoders[type(obj)](obj)
        else:
            return super(JSONEncoder, self).default(obj)
        pass
    pass

class IdentifierGenerator(object):
    base = '234679ACDEFGHJKMNPQRTVWXYZ'
    characters = list(base.lower())
    characters.extend(base)
    def __init__(self, length=4):
        self.length = length
        pass
    def __iter__(self):
        return self
    def next(self):
        return ''.join(random.sample(self.characters, self.length))

class APIObject(redis_wrap.HashFu):
    def __init__(self, node, key):
        self.name = node
        self.system = 'default'
        self.__key = key
        pass

    def __setitem__(self, key, value):
        redis_wrap.get_redis(self.system).incr('library:version', 1)
        super(APIObject, self).__setitem__(key, value)
        pass

    @property
    def key(self):
        return self.__key

    def delete(self):
        redis_wrap.get_redis(self.system).delete(self.name)
        pass
    pass


class Artist(APIObject): 
    def __init__(self, node, key, art=None, **props):
        super(Artist, self).__init__(node, key)
        self.albums = ObjectList(
            node=':'.join([self.name, 'albums']), 
            sub_type=Album, 
            prefix='album'
            )
        self.songs = ObjectList(
            node=':'.join([self.name, 'songs']), 
            sub_type=Song, 
            prefix='song'
            )
        for prop_key, prop_value in props.items():
            self[prop_key] = prop_value
            pass
        pass
    pass

class Album(APIObject): 
    def __init__(self, node, key, art=None, **props):
        super(Album, self).__init__(node, key)
        self.songs = ObjectList(
            node=':'.join([self.name, 'songs']), 
            sub_type=Song, 
            prefix='song'
            )
        for prop_key, prop_value in props.items():
            self[prop_key] = prop_value
            pass
        pass
    pass

class Song(APIObject): 
    def __init__(self, node, key, art=None, **props):
        super(Song, self).__init__(node, key)
        for prop_key, prop_value in props.items():
            self[prop_key] = prop_value
            pass
        pass

    @property
    def file_url(self):
        if self['path'] == 'local':
            return '/song/{0}'.format(self.key)
            pass

    @property
    def file(self):
        if self['path'] == 'local':
            store = FileStore(base='/tmp')
            return store[self.name]
        pass
    pass

class ObjectList(collections.MutableMapping):
    build_index =  """
local keys = redis.call('SMEMBERS', '{0}')
for i=1, #keys do
  local node = '{1}' .. ':' .. keys[i]
  local prop = redis.call('HGET', node, '{2}')
  redis.call('HSET', ARGV[1], prop, keys[i])
end
"""
    squencer = IdentifierGenerator()
    def __init__(self, node, sub_type, prefix, system = 'default'):
        if prefix is not None:
            self.prefix = prefix
            pass
        else:
            self.prefix = node
            pass
        self.sub_type = sub_type
        self.name = node
        self.__refs = weakref.WeakValueDictionary()
        self.__keys = redis_wrap.get_set(self.name)
        self.system = system
        pass
    
    def fetch(self, prop, value):
        """Fetch an object with a prop equal value and return it, else return None""" 
        lua = self.build_index.format(self.name, self.prefix, prop)
        target = '-'.join([self.name, 'index', prop])
        redis_wrap.get_redis().eval(lua, 0, target)
        key = redis_wrap.get_redis().hget(target, value)
        if key is not None:
            return self[key]
        else:
            return None

    def __len__(self):
        return len(self.__keys)
    
    def __delitem__(self, key):
        self[key].delete()
        del self.__keys[key]
        pass

    def __iter__(self):
        return self.__keys.__iter__()

    def __contains__(self, key):
        return key in self.__keys

    def __getitem__(self, key):
        if not key in self.__keys:
            raise KeyError(key)
        obj = self.__refs.get(key)
        if obj is None:
            obj = self.sub_type(':'.join([self.prefix, key]), key)
            self.__refs[key] = obj
            pass
        return obj

    def __setitem__(self, key, value):
        if type(value) == self.sub_type:
            self.__keys.add(key)
            self.__refs[key] = value
            redis_wrap.get_redis(self.system).incr('library:version', 1)
            pass
        else:
            raise ValueError('Value must be of type ' + str(self.sub_type))
        pass

    def add(self, *args, **kwargs):
         key = self.squencer.next()
         value = self.sub_type(
             ':'.join([self.prefix, key]),
             key,
             *args,
             **kwargs
             )
         self[key] = value
         return value
    pass

class FileStore(redis_wrap.HashFu):
    squencer = IdentifierGenerator()
    def __init__(self, node = 'library:files', system = 'default', base = None):
        self.name = node
        self.system = system
        self.base = os.path.abspath(base)
        pass
    
    def __clean_filename(self, filename):
        if not os.path.supports_unicode_filenames and type(filename) == unicode:
            return filename.encode('ascii', errors = 'ignore')
        return filename
    
    def create(self, node, prefix, filename):
        filename = self.__clean_filename(filename)
        disk_path = os.path.join(self.base, prefix, filename).replace(' ', '_')
        if os.path.exists(disk_path):
            suffix_path = disk_path
            while os.path.exists(suffix_path):
                suffix_path = suffix_path + '-' + self.squencer.next()
                pass
            disk_path = suffix_path
            pass
        db_path = disk_path[len(self.base)+1:]
        if not os.path.exists(os.path.dirname(disk_path)):
            os.mkdir(os.path.dirname(disk_path))
            pass

        super(FileStore, self).__setitem__(node, db_path)
        return disk_path
    
    def __setitem__(key, value):
        if os.path.commonprefix(self.base, value):
            self[key] = value[len(self.base)+1:]
            pass
        else:
            self[key] = value
            pass
        pass
    
    def __getitem__(self, key):
        return os.path.join(
            self.base, 
            super(FileStore, self).__getitem__(key)
            )
    pass



class Library(object):
    def __init__(self, directory = '/tmp', system = 'default'):
        self.artists = ObjectList('artists', Artist, 'artist')
        self.songs = ObjectList('songs', Song, 'song')
        self.albums = ObjectList('albums', Album, 'album')
        self.files = FileStore(base=directory)
        self.system = system
        pass

    @property
    def version(self):
        return redis_wrap.get_redis(self.system).get('library:version') or -1

    def add(self, artist, album, song):
        stored_artist = self.artists.fetch('name', artist['name'])
        if stored_artist is None:
            stored_artist = self.artists.add(**artist)
            pass
        stored_album = stored_artist.albums.fetch('name', album['name'])
        if stored_album is None:
            stored_album = self.albums.add(**album)
            stored_artist.albums[stored_album.key] = stored_album
            pass
        stored_song = stored_album.songs.fetch('name', song['name'])
        if stored_song is None:
            stored_song = self.songs.add(**song)
            stored_album.songs[stored_song.key] = stored_song
            stored_artist.songs[stored_song.key] = stored_song
            pass
        else:
            raise SongExists_Exception(name=song['name'], song=stored_song)
        return stored_song
    pass

__all__ = [ 'Library', 'JSONEncoder', 'Song', 'Album', 'Artist', 'SongExists_Exception' ]
