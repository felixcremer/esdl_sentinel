import cablab

import os
from datetime import timedelta

import netCDF4
import numpy
import datetime

from cablab import NetCDFCubeSourceProvider

class ColETProvider(NetCDFCubeSourceProvider):
    def __init__(self, cube_config, name='ET', dir=None, resampling_order=None):
        super(ColETProvider, self).__init__(cube_config, name, dir, resampling_order)
        self.old_indices = None

    @property
    def variable_descriptors(self):
        return {
            'ET': {
                'source_name': 'variable',
                'data_type': numpy.float32,
                'fill_value': numpy.float32(-3.4e38),
                'units': 'none',
                # 'long_name': 'precip - v1.0',
                'scale_factor': 1.0,
                'add_offset': 0.0,
                'comment': 'taken from BGI Datastructure, for internal use only'
            }
        }

    def compute_source_time_ranges(self):
        source_time_ranges = []
        file_names = filter(lambda x: x.endswith('nc'),os.listdir(self.dir_path))

        for file_name in file_names:
            file = os.path.join(self.dir_path, file_name)
            yr=int(file_name[12:15])
            d1=[datetime.datetime(yr,1,1)+datetime.timedelta(days=8*i) for i in range(46)]
            d2=[datetime.datetime(yr,1,9)+datetime.timedelta(days=8*i) for i in range(46)]
            d2[45]=datetime.datetime(yr+1,1,1)
            source_time_ranges += [(d1[i], d2[i], file, i) for i in range(len(d1))]
        return sorted(source_time_ranges, key=lambda item: item[0])
