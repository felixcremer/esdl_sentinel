import glob
import os.path
import time
from abc import ABCMeta, abstractmethod, abstractproperty
from datetime import datetime
from esdl.cube_provider import BaseCubeSourceProvider






class GeoTiffCubeSourceProvider(BaseCubeSourceProvider, metaclass=ABCMeta):
    """
    A BaseCubeSourceProvider that
    * Uses NetCDF source datasets read from a given **dir_path**
    * Performs temporal aggregation first and then spatial resampling

    :param cube_config: Specifies the fixed layout and conventions used for the cube.
    :param name: The provider's registration name.
    :param dir_path: Source directory to read the files from. If relative path,
           it will be resolved against the **cube_sources_root** path of the
           global ESDL configuration (**esdl.util.Config.instance()**).
    :param resampling_order: The order in which resampling is performed. One of 'time_first', 'space_first'.
    """

    def __init__(self, cube_config: CubeConfig, name: str, dir_path: str, resampling_order: str):
        super(GeoTiffCubeSourceProvider, self).__init__(cube_config, name)

        if dir_path is None:
            raise ValueError('dir_path expected')

        valid_resampling_order = ('time_first', 'space_first')
        if resampling_order is None:
            resampling_order = valid_resampling_order[0]
        if resampling_order not in valid_resampling_order:
            raise ValueError('resampling_order must be one of %s' % str(valid_resampling_order))

        if not os.path.isabs(dir_path):
            self._dir_path = Config.instance().get_cube_source_path(dir_path)
        else:
            self._dir_path = dir_path
        self._resampling_order = resampling_order
        self._dataset_cache = NetCDFDatasetCache(name)
        self._old_indices = None

    @property
    def dir_path(self):
        return self._dir_path

    @property
    def dataset_cache(self):
        return self._dataset_cache

    def compute_variable_images_from_sources(self, index_to_weight):

        new_indices = self.close_unused_open_files(index_to_weight)

        var_descriptors = self.variable_descriptors
        target_var_images = dict()
        for var_name, var_attributes in var_descriptors.items():
            source_var_images = [None] * len(new_indices)
            source_weights = [None] * len(new_indices)
            var_image_index = 0
            for i in new_indices:
                print(i)
                file, time_index = self._get_file_and_time_index(i)
                source_name = var_attributes.get('source_name', var_name)
                variable = self._dataset_cache.get_dataset(file).variables[source_name]
                if len(variable.shape) == 3:
                    print(time_index)
                    var_image = variable[time_index, :, :]
                elif len(variable.shape) == 2:
                    var_image = variable[:, :]
                else:
                    raise ValueError("unexpected shape for variable '%s'" % var_name)
                var_image = self.transform_source_image(var_image)
                if self._resampling_order == 'space_first':
                    var_image = gtr.resample_2d(var_image,
                                                self.cube_config.grid_width,
                                                self.cube_config.grid_height,
                                                ds_method=_get_ds_method(var_attributes),
                                                us_method=_get_us_method(var_attributes),
                                                fill_value=var_attributes.get('fill_value', np.nan))
                if var_image.shape[1] / var_image.shape[0] != 2.0:
                    print("Warning: wrong size ratio of image in '%s'. Expected 2, got %f" % (
                        file, var_image.shape[1] / var_image.shape[0]))
                source_var_images[var_image_index] = var_image
                source_weights[var_image_index] = index_to_weight[i]
                var_image_index += 1
            if len(new_indices) > 1:
                # Temporal aggregation
                var_image = aggregate_images(source_var_images, weights=source_weights)
            else:
                # Temporal aggregation not required
                var_image = source_var_images[0]
            # Spatial resampling
            if self._resampling_order == 'time_first':
                var_image = gtr.resample_2d(var_image,
                                            self.cube_config.grid_width,
                                            self.cube_config.grid_height,
                                            ds_method=_get_ds_method(var_attributes),
                                            us_method=_get_us_method(var_attributes),
                                            fill_value=var_attributes.get('fill_value', np.nan))
            target_var_images[var_name] = var_image

        return target_var_images

    def transform_source_image(self, source_image):
        """
        Returns the source image. Override to implement transformations if needed.
        :param source_image: 2D image
        :return: source_image
        """
        return source_image

    def close_unused_open_files(self, index_to_weight):
        """
        Close all datasets that wont be used anymore w.r.t. the given **index_to_weight** dictionary passed to the
        **compute_variable_images_from_sources()** method.

        :param index_to_weight: A dictionary mapping time indexes --> weight values.
        :return: set of time indexes into currently active files w.r.t. the given **index_to_weight** parameter.
        """
        new_indices = set(index_to_weight.keys())
        if self._old_indices:
            unused_indices = self._old_indices - new_indices
            for i in unused_indices:
                file, _ = self._get_file_and_time_index(i)
                self._dataset_cache.close_dataset(file)
        self._old_indices = new_indices
        return new_indices

    def close(self):
        self._dataset_cache.close_all_datasets()
