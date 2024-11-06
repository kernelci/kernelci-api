# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2024 Collabora Limited
# Author: enys Fedoryshchenko <denys.f@collabora.com>

"""KernelCI API metrics module"""

import threading


class Metrics():
    '''
    Class to store and update various metrics
    '''
    def __init__(self):
        '''
        Initialize metrics dictionary and lock
        '''
        self.metrics = {}
        self.metrics['http_requests_total'] = 0
        self.lock = threading.Lock()

    # Various internal metrics
    def update(self):
        '''
        Update metrics (reserved for future use)
        '''

    def add(self, key, value):
        '''
        Add a value to a metric
        '''
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = 0
            self.metrics[key] += value

    def get(self, key):
        '''
        Get the value of a metric
        '''
        self.update()
        with self.lock:
            return self.metrics.get(key, 0)

    def all(self):
        '''
        Get all the metrics
        '''
        self.update()
        with self.lock:
            return self.metrics
