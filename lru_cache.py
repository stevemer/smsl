from collections import namedtuple
from functools import update_wrapper
from threading import RLock
import time

"""
CACHE HIT = True, CACHE MISS = False
PREV = 0
NEXT = 1
KEY = 2
RESULT = 3
"""

class LRU(object):

    def __init__(self, count=100, expire=None, cb_dispose=None, pairs=[]):
        self.cache = dict()
        self.cache_get = self.cache.get
        self.stats = [0, 0]
        self.lock = RLock()
        self.root = []
        self.root[:] = [self.root, self.root, None, None]
        self.nonlocal_root = [self.root]
        self.count = count
        self.expire = expire

        if count == 0:
            # This makes no sense, might as well use a dict
            raise Exception("Mass stupidity detected")

        for key, val in pairs:
            self[key] = val

    def __getitem__(self, key):
        with self.lock:
            link = self.cache_get(key)
            if link is not None:
                # record use of the key by moving it to the front of the list
                link_prev, link_next, key, result = link
                # check if key has expired
                if self.expire and result[1] + self.expire < time.time():
                    raise KeyError(key)

                self.root, = self.nonlocal_root

                link_prev[1] = link_next
                link_next[0] = link_prev
                last = self.root
                last[1] = self.root[0] = link
                link[0] = last
                link[1] = self.root
                self.stats[True] += 1
                return result[0]
            pass
        raise KeyError(key)

    def __setitem__(self, key, val):
        val = (val, time.time())
        with self.lock:
            self.root, = self.nonlocal_root
            if key in self.cache:
                # Key was added to the cache while the lock was released
                pass
            elif len(self.cache) >= self.count:
                # use the old root to store the new key and value
                oldroot = self.root
                oldroot[2] = key
                oldroot[3] = val
                # empty the oldest link and make it the new root
                self.root = self.nonlocal_root[0] = oldroot[1]
                oldkey = self.root[2]
                oldvalue = self.root[3]
                self.root[2] = self.root[3] = None
                # now update the cache dictionary for the new links
                del self.cache[oldkey]
                self.cache[key] = oldroot
                pass
            else:
                # put val in a new link at the front of the list
                last = self.root[0]
                link = [last, self.root, key, val]
                last[1] = self.root[0] = self.cache[key] = link
                pass
            pass
        pass

    def cache_info(self):
        """Report cache statistics"""
        with self.lock:
            return _CacheInfo(self.stats[True], self.stats[False], self.count, len(self.cache))

    def cache_clear(self):
        """Clear the cache and cache statistics"""
        with self.lock:
            self.cache.clear()
            self.root = self.nonlocal_root[0]
            self.root[:] = [self.root, self.root, None, None]
            self.stats[:] = [0, 0]
            pass
        pass

    def __contains__(self, item):
        return self.cache.__contains__(item)

    def __delitem__(self, item):
        return self.cache.__delitem__(item)

    def __iter__(self):
        return self.cache.__iter__()

    def __len__(self):
        return len(self.cache)

    def iteritems(self):
        return self.cache.iteritems()

    def iterkeys(self):
        return self.cache.iterkeys()

    def itervalues(self):
        return self.cache.itervalues()

    def keys(self):
        return self.cache.keys()

    def values(self):
        return self.cache.values()

    def items(self):
        return self.cache.items()

    def get(self, obj, default=None):
        # Handle KeyError instead of doing __contains__ then
        # __getitem__ because an item may expire between those two
        # calls.
        try:
            return self[obj]
        except KeyError:
            return default
        pass

    def clear(self):
        self.cache_clear()
        pass

    def pop(self, item):
        return self.cache.pop(item)
