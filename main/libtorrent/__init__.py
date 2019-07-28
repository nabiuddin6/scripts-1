"""Script to make torrenting movies and TV shows easier (wraps a P2P client).

Connects to a VPN (using Private Internet Access), downloads the torrent
(using a magnet file), disconnects from the VPN when the download is finished,
and then sends me a text message to let me know the download is complete.

Multiple torrents can be downloaded at the same time by simply running this
script multiple times (using different magnet files). If another instance of
this script is running, the primary instance will be signaled to enqueue the
new magnet file for download.
"""

import queue
import threading
import time
from typing import (  # noqa
    Any,
    Callable,
    Container,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    NoReturn,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import gutils

log = gutils.logging.getEasyLogger("torrent")

# This lock "protects" (i.e. blocks) the torrents from "catching the
# Plague" (i.e. removing themselves from the BitTorrent client)
# immediately after download. Instead, they seed until the very last
# torrent finishes downloading, at which point all torrents "become
# infected" and die, one after the other.
the_plague = threading.Lock()
magnet_queue: "queue.Queue[str]" = queue.Queue()

DELUGE = ["sudo", "-E", "deluge-console"]
_XDG_DATA_DIR = gutils.xdg.init("data")
ARGS_FILE = _XDG_DATA_DIR / "args"
# Created after the first torrent is successfully added to P2P client.
MASTER_IS_ONLINE_FILE = _XDG_DATA_DIR / "master_is_online"


def notify_and_log(msg):
    log.debug(msg)
    gutils.notify(msg)


def run_info_cmd(field: str, ID: str = None) -> Union[str, List[str]]:
    """Wrapper for the `deluge-console info` command.

    Returns:
        Return type is `str` when @ID is given and `List[str]` otherwise.
    """
    log.vdebug("ID = %s", ID)  # type: ignore

    cmd = (
        "{DELUGE} info --sort-reverse=time_added {ID} | "
        "awk -F: '{{if ($1==\"{field}\") print $0}}'".format(
            DELUGE=" ".join(DELUGE), field=field, ID=("" if ID is None else ID)
        )
    )
    out = gutils.shell(cmd)
    ret = out.split("\n")

    if ret[0] == "":
        raise ValueError(
            "Something went wrong with the `info` function. "
            "Local state:\n\n{}".format(locals())
        )

    return ret if ID is None else ret[0]


def wait_for_first_magnet() -> None:
    while magnet_queue.empty():
        time.sleep(0.5)