import json
from time import ticks_ms, ticks_diff
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio


## Public API


def enable():
    """
    Once enabled, all new asyncio tasks will be tracked.
    Existing tasks will not be tracked.
    """
    asyncio.create_task = asyncio.core.create_task = create_task


def inject():
    """
    This enables aioprof and attempts to hook into all existing tasks.
    """
    tasks = list()
    enable()
    try:
        while t := asyncio.core._task_queue.pop():
            tasks.append(t)
    except IndexError:
        pass

    for t in tasks:
        asyncio.create_task(t.coro)

def reset():
    """
    Reset all the accumlated task data
    """
    global timing
    timing = {}


def report():
    """
    Print a report to repl of task run count and timing.
    """
    if not timing:
        print("No timing data")
        return

    # | name | run count | run time | max run time | latest exec cycle |
    headings = ["function name", "count", "ms", "max", "last exec"]

    # Assemble lists all functions worth of data as strings, sorted by run ms
    details = [
        (name.replace("generator object", "fn"), str(count), str(ms), str(max_ms), str(last))
        for name, (count, ms, max_ms, last) in reversed(sorted(timing.items(), key=lambda i: i[1][1]))
    ]

    # Add headings as first row of the table
    details.insert(0, headings)
    
    # Calculate the maximum width needed for each column
    nlen = max([len(n) for n, i, t, m, c in details])
    ilen = max([len(i) for n, i, t, m, c in details])
    tlen = max([len(t) for n, i, t, m, c in details])
    mlen = max([len(m) for n, i, t, m, c in details])
    clen = max([len(c) for n, i, t, m, c in details])
    collen = [nlen, ilen, tlen, mlen, clen]

    # Print table
    print(f'┌─{"─" * nlen}─┬─{"─" * ilen}─┬─{"─" * tlen}─┬─{"─" * mlen}─┬─{"─" * clen}─┐')
    print_divider = True
    for row in details:
        print("| " + (" | ".join(f"{c:<{collen[i]}}" for i, c in enumerate(row))) + " |")
        if print_divider:
            # Heading row just printed, print divider below
            print(f'├─{"─" * nlen}─┼─{"─" * ilen}─┼─{"─" * tlen}─┼─{"─" * mlen}─┼─{"─" * clen}─┤')
            print_divider = False
    print(f'└─{"─" * nlen}─┴─{"─" * ilen}─┴─{"─" * tlen}─┴─{"─" * mlen}─┴─{"─" * clen}─┘')


def json():
    """
    Directly dump the task [run-count,timing] details as json.
    """
    return json.dumps(timing)


## Internal functionality

Task = asyncio.Task
timing = {}
counter = 0
__create_task = asyncio.create_task

class Coro:
    def __init__(self, c) -> None:
        self.name = str(c)
        self.c = c

    def send(self, *args, **kwargs):
        t_name = self.name
        t_start = ticks_ms()
        try:
            ret = self.c.send(*args, **kwargs)
        except AttributeError:
            print(self, self.c)
            raise
        finally:
            if t_name not in timing:
                timing[t_name] = [0, 0, 0, 0]

            t = timing[t_name]
            taken = ticks_diff(ticks_ms(), t_start)
            global counter
            
            # columns of data
            t[0] += 1  # run count
            t[1] += taken  # time taken for this run
            t[2] = max(taken, t[2])  # max time ever taken by this function
            t[3] = counter  # global cycle count (can show order that functions are run in)
            
            counter += 1
        return ret

    def __getattr__(self, name: str):
        return getattr(self.c, name)


def create_task(coro):
    if not isinstance(coro, Coro):
        coro = Coro(coro)
    return __create_task(coro)
