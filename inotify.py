import collections
import ctypes
import ctypes.util

# bit masks
IN_ISDIR        = 0x40000000
IN_ALL_EVENTS   = 0xfff
IN_WRITE_EVENTS = 0x00000002

class inotify_event_struct(ctypes.Structure):
    """
    Structure representation of the inotify_event structure
    (used in buffer size calculations)::
        struct inotify_event {
            __s32 wd;            /* watch descriptor */
            __u32 mask;          /* watch mask */
            __u32 cookie;        /* cookie to synchronize two events */
            __u32 len;           /* length (including nulls) of name */
            char  name[0];       /* stub for possible name */
        };
    """
    _fields_ = [('wd', ctypes.c_int),
                ('mask', ctypes.c_uint32),
                ('cookie', ctypes.c_uint32),
                ('len', ctypes.c_uint32),
                ('name', ctypes.c_char_p)]

InotifyEvent = collections.namedtuple('InotifyEvent', ['wd', 'mask', 'cookie', 'len', 'name'])

EVENT_SIZE = ctypes.sizeof(inotify_event_struct)
EVENT_BUFFER_SIZE = 1024 * (EVENT_SIZE + 16)

# wrap for inotify system call
libc_name = ctypes.util.find_library('c')
libc = ctypes.CDLL(libc_name, use_errno=True)
get_errno_func = ctypes.get_errno

libc.inotify_init.argtypes = []
libc.inotify_init.restype = ctypes.c_int
libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, 
                                   ctypes.c_uint32]
libc.inotify_add_watch.restype = ctypes.c_int
libc.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
libc.inotify_rm_watch.restype = ctypes.c_int

inotify_init = libc.inotify_init
inotify_add_watch = libc.inotify_add_watch
inotify_rm_watch = libc.inotify_rm_watch
