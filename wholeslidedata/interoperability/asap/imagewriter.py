import abc
from pathlib import Path

import multiresolutionimageinterface as mir
import numpy as np
from multiresolutionimageinterface import MultiResolutionImageWriter
from shapely import geometry
from warnings import warn

from wholeslidedata.samplers.patchlabelsampler import \
    SegmentationPatchLabelSampler


class TileShapeError(Exception):
    pass


class CoordinateError(Exception):
    pass


class InvalidWriterError(Exception):
    pass


class Writer(abc.ABC):
    def __init__(self):
        self._path = None
        self._spacing = None
        self._dimensions = None
        self._tile_shape = None

class WholeSlideImageWriterBase(Writer, MultiResolutionImageWriter):
    def __init__(self):
        Writer.__init__(self)
        MultiResolutionImageWriter.__init__(self)

    def write_tile(self, tile, coordinates=None):
        self._write_tile_to_image(tile, coordinates)

    def _write_tile_to_image(self, tile, coordinates):
        if tile.shape != self._tile_shape:
            raise TileShapeError(f"Tile shape of input {tile.shape} is not the same as configured tile shape {self._tile_shape}")

        if coordinates:
            col, row = self._get_col_row(coordinates)
            if col is not None and row is not None:
                self.writeBaseImagePartToLocation(
                    tile.flatten().astype("uint8"), col, row
                )
        else:
            self.writeBaseImagePart(tile.flatten().astype("uint8"))

    def _get_col_row(self, coordinates):
        x, y = coordinates
        if x < self._dimensions[0] and x >= 0 and y < self._dimensions[1] and y >= 0:
            return x, y
        return None, None

    def save(self):
        self.finishImage()


class WholeSlideMaskWriter(WholeSlideImageWriterBase):
    def __init__(self, suffix=".tif"):
        super().__init__()
        self._suffix = suffix

    def write(self, path, spacing, dimensions, tile_shape):
        self._path = str(path).replace(Path(path).suffix, self._suffix)
        self._spacing = spacing
        self._dimensions = dimensions
        self._tile_shape = tile_shape

        print(f"Creating: {self._path}....")
        print(f"Spacing: {self._spacing}")
        print(f"Dimensions: {self._dimensions}")
        print(f"Tile_shape: {self._tile_shape}")

        self.openFile(self._path)
        self.setTileSize(self._tile_shape[0])

        try:
            self.setCompression(mir.Compression_LZW)
            self.setDataType(mir.DataType_UChar)
            self.setInterpolation(mir.Interpolation_NearestNeighbor)
            self.setColorType(mir.ColorType_Monochrome)
        except:
            self.setCompression(mir.LZW)
            self.setDataType(mir.UChar)
            self.setInterpolation(mir.NearestNeighbor)
            self.setColorType(mir.Monochrome)

        # set writing spacing
        pixel_size_vec = mir.vector_double()
        pixel_size_vec.push_back(self._spacing)
        pixel_size_vec.push_back(self._spacing)
        self.setSpacing(pixel_size_vec)
        self.writeImageInformation(self._dimensions[0], self._dimensions[1])

class WholeSlideIndexedMaskWriter(WholeSlideImageWriterBase):
    def __init__(self, suffix=".tif"):
        super().__init__()
        self._suffix = suffix

    def _set_indexed_channels(self, dimensions):
        if len(dimensions) > 2:
            return len(dimensions)
        elif len(dimensions) == 2:
            return 1
        else:
            raise Exception("Invalid dimensions")

    def write(self, path, spacing, dimensions, tile_shape):
        self._path = str(path).replace(Path(path).suffix, self._suffix)
        self._spacing = spacing
        self._dimensions = dimensions
        self._tile_shape = tile_shape
        self._channels = self._set_indexed_channels(dimensions)

        print(f"Creating: {self._path}....")
        print(f"Spacing: {self._spacing}")
        print(f"Dimensions: {self._dimensions}")
        print(f"Tile_shape: {self._tile_shape}")
        print(f"Indexed channels: {self._channels}")

        self.openFile(self._path)
        self.setTileSize(self._tile_shape[0])

        try:
            self.setCompression(mir.Compression_LZW)
            self.setDataType(mir.DataType_UChar)
            self.setInterpolation(mir.Interpolation_NearestNeighbor)
            self.setColorType(mir.ColorType_Indexed)
            self.setNumberOfIndexedColors(self._channels)
        except:
            self.setCompression(mir.LZW)
            self.setDataType(mir.UChar)
            self.setInterpolation(mir.NearestNeighbor)
            self.setColorType(mir.Indexed)
            self.setNumberOfIndexedColors(self._channels)

        # set writing spacing
        pixel_size_vec = mir.vector_double()
        pixel_size_vec.push_back(self._spacing)
        pixel_size_vec.push_back(self._spacing)
        self.setSpacing(pixel_size_vec)
        self.writeImageInformation(self._dimensions[0], self._dimensions[1])

class WholeSlideImageWriter(WholeSlideImageWriterBase):
    def __init__(self, suffix=".tif"):
        super().__init__()
        self._suffix = suffix

    def write(self, path, spacing, dimensions, tile_shape, jpeg_quality=80, interpolation='nearest'):
        self._path = str(path).replace(Path(path).suffix, self._suffix)
        self._spacing = spacing
        self._dimensions = dimensions
        self._tile_shape = tile_shape

        print(f"Creating: {self._path}....")
        print(f"Spacing: {self._spacing}")
        print(f"Dimensions: {self._dimensions}")
        print(f"Tile_shape: {self._tile_shape}")

        self.openFile(self._path)
        self.setTileSize(self._tile_shape[0])


        try:
            if interpolation=='nearest':
                self.setInterpolation(mir.Interpolation_NearestNeighbor)
            else:
                self.setInterpolation(mir.Interpolation_Linear)
            self.setDataType(mir.DataType_UChar)
            self.setColorType(mir.ColorType_RGB)
            self.setCompression(mir.Compression_JPEG)
        except:
            if interpolation=='nearest':
                self.setInterpolation(mir.NearestNeighbor)
            else:
                self.setInterpolation(mir.Linear)
            self.setDataType(mir.UChar)
            self.setColorType(mir.RGB)
            self.setCompression(mir.JPEG)

        self.setJPEGQuality(jpeg_quality)

        # set writing spacing
        pixel_size_vec = mir.vector_double()
        pixel_size_vec.push_back(self._spacing)
        pixel_size_vec.push_back(self._spacing)
        self.setSpacing(pixel_size_vec)
        self.writeImageInformation(self._dimensions[0], self._dimensions[1])


def write_mask(
    wsi, wsa, spacing, tile_size=1024, output_folder=None, suffix="_gt_mask.tif"
):

    if len(wsa.annotations) == 0:
        ValueError(f"Annotations are empty for wsa: {wsa.path}")

    written = False

    shape = wsi.shapes[wsi.get_level_from_spacing(spacing)]
    ratio = wsi.get_downsampling_from_spacing(spacing)
    write_spacing = wsi.get_real_spacing(spacing)

    if output_folder is None:
        mask_output_path = Path(str(wsa.path).replace(".xml", suffix))
    else:
        mask_output_path = output_folder / (wsa.path.stem + suffix)

    if mask_output_path.exists():
        warning_text = f"Mask output path already exist: {mask_output_path}"
        warn(warning_text, UserWarning)
        return

    wsm_writer = WholeSlideMaskWriter()
    wsm_writer.write(
        path=mask_output_path,
        spacing=write_spacing,
        dimensions=(shape[0], shape[1]),
        tile_shape=(tile_size, tile_size),
    )

    label_sampler = SegmentationPatchLabelSampler()
    for y_pos in range(0, shape[1], tile_size):
        for x_pos in range(0, shape[0], tile_size):
            mask = label_sampler.sample(
                wsa,
                (
                    (x_pos + tile_size // 2) * ratio,
                    (y_pos + tile_size // 2) * ratio,
                ),
                (tile_size, tile_size),
                ratio,
            )
            if np.any(mask):
                written = True
                wsm_writer.write_tile(tile=mask, coordinates=(int(x_pos), int(y_pos)))

    if not written:
        raise ValueError(f"No values have been written to {mask_output_path}")

    print("closing...")
    wsm_writer.save()
    print("done")
