#!/usr/bin/env python3

import datetime
import time


class Timings:
    def __init__(self):
        self.timings = []

    def start(self, method, url, params):
        self.curr_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.start_time = int(round(1000 * time.time()))
        self.timings.append(
            {
                "method": method,
                "path": url,
                "params": params,
                "start_time": self.start_time,
                "end_time": None,
                "date": self.curr_date,
            }
        )

    def end(self, status_code):
        self.end_time = int(round(1000 * time.time()))

        # get last item
        last = self.timings[-1]
        last["end_time"] = self.end_time
        last["status_code"] = status_code
        last["duration"] = self.end_time - last["start_time"]

        return last

    def export_csv(self, filename):
        with open(filename, "w") as f:
            f.write(
                "method\tpath\tparams\tstart_time\tend_time\tdate\tstatus_code\tduration\tduration_s\n"
            )

            for t in self.timings:
                f.write(
                    "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n"
                    % (
                        t["method"],
                        t["path"],
                        t["params"],
                        t["start_time"],
                        t["end_time"],
                        t["date"],
                        t["status_code"],
                        t["duration"],
                        t["duration"] / 1000,
                    )
                )
