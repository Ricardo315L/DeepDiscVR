import json
from pathlib import Path
import glob
from astropy.io import fits
import os
import cv2
import numpy as np
from detectron2.structures import BoxMode
from astropy.visualization import make_lupton_rgb


class DataLoader:
    """A base data loader class"""
    def __init__(self):
        self.dataset_dicts = None

    def read_fits(self, img_dir):
        """Read metadata from a fits file, generates a top-level dictionary"""

        # It's weird to call this img_dir
        set_dirs = sorted(glob.glob("%s/set_*" % img_dir))

        dataset_dicts = []

        # Loop through each set
        for idx, set_dir in enumerate(set_dirs):
            record = {}

            mask_dir = os.path.join(img_dir, set_dir, "masks.fits")
            filename = os.path.join(img_dir, set_dir, "img")

            # Open each FITS image
            with fits.open(mask_dir, memmap=False, lazy_load_hdus=False) as hdul:
                sources = len(hdul)
                height, width = hdul[0].data.shape
                data = [hdu.data / np.max(hdu.data) for hdu in hdul]
                category_ids = [hdu.header["CLASS_ID"] for hdu in hdul]

            record["file_name"] = filename
            record["image_id"] = idx
            record["height"] = height
            record["width"] = width
            objs = []

            # Mask value thresholds per category_id
            thresh = [0.005 if i == 1 else 0.08 for i in category_ids]

            # Generate segmentation masks
            for i in range(sources):
                image = data[i]
                mask = np.zeros([height, width], dtype=np.uint8)
                # Create mask from threshold
                mask[:, :][image > thresh[i]] = 1
                # Smooth mask
                mask[:, :] = cv2.GaussianBlur(mask[:, :], (9, 9), 2)

                # https://github.com/facebookresearch/Detectron/issues/100
                contours, hierarchy = cv2.findContours(
                    (mask).astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
                )
                segmentation = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    contour = contour.flatten().tolist()
                    # segmentation.append(contour)
                    if len(contour) > 4:
                        segmentation.append(contour)
                # No valid countors
                if len(segmentation) == 0:
                    continue

                # Add to dict
                obj = {
                    "bbox": [x, y, w, h],
                    "area": w * h,
                    "bbox_mode": BoxMode.XYWH_ABS,
                    "segmentation": segmentation,
                    "category_id": category_ids[i] - 1,
                }
                objs.append(obj)

            record["annotations"] = objs
            dataset_dicts.append(record)

        self.dataset_dicts = dataset_dicts
        return self


    def to_coco_format(self):
        """transforms"""
        pass

    def custom_loader(self, loader_func, **kwargs):
        """passes along a custom loader"""
        self.datadict = loader_func(**kwargs)
        return self

    def load_coco_json_file(self, file):
        """Open a JSON text file, and return encoded data as dictionary.

        Assumes JSON data is in the COCO format.

        Parameters
        ----------
        file : str
            pointer to file

        Returns
        -------
            dictionary of encoded data
        """
        # Opening JSON file
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

def get_data_from_json(filename):
    """Open a JSON text file, and return encoded data as dictionary.

    Parameters
    ----------
    filename : str
        The name of the file to load.

    Returns
    -------
        dictionary of encoded data

    Raises
    ------
    FileNotFoundError if the file cannot be found.
    """
    if not Path(filename).exists():
        raise FileNotFoundError(f"Unable to load file {filename}")

    # Opening JSON file
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


class ImageReader:
    """Class that will read images on the fly for the training/testing dataloaders"""

    def __init__(self, reader, norm="raw", **scalekwargs):
        """
        Parameters
        ----------
        reader : function
            This function should take a single key and return a single image as a numpy array
            ex) give a filename or an index in an array
        norm : str
            A contrast scaling to apply before data augmentation, i.e. luptonizing or z-score scaling
            Default = raw
        **scalekwargs : key word args
            Key word args for the contrast scaling function
        """
        self.reader = reader
        self.scalekwargs = scalekwargs
        self.scaling = ImageReader.norm_dict[norm]

    def __call__(self, key):
        """Read the image and apply scaling.

        Parameters
        ----------
        key : str or int
            The key indicating the image to read.

        Returns
        -------
        im : numpy array
            The image.
        """
        im = self.reader(key)
        im_scale = self.scaling(im, **self.scalekwargs)
        return im_scale

    def raw(im):
        """Apply raw image scaling (no scaling done).

        Parameters
        ----------
        im : numpy array
            The image.

        Returns
        -------
        numpy array
            The image with pixels as float32.
        """
        return im.astype(np.float32)

    def lupton(im, bandlist=[2, 1, 0], stretch=0.5, Q=10, m=0):
        """Apply Lupton scaling to the image and return the scaled image.

        Parameters
        ----------
        im : np array
            The image being scaled
        bandlist : list[int]
            Which bands to use for lupton scaling (must be 3)
        stretch : float
            lupton stretch parameter
        Q : float
            lupton Q parameter
        m: float
            lupton minimum parameter

        Returns
        -------
        image : numpy array
            The 3-channel image after lupton scaling using astropy make_lupton_rgb
        """
        assert np.array(im.shape).argmin() == 2 and len(bandlist) == 3
        b1 = im[:, :, bandlist[0]]
        b2 = im[:, :, bandlist[1]]
        b3 = im[:, :, bandlist[2]]

        image = make_lupton_rgb(b1, b2, b3, minimum=m, stretch=stretch, Q=Q)
        return image

    def zscore(im, A=1):
        """Apply z-score scaling to the image and return the scaled image.

        Parameters
        ----------
        im : np array
            The image being scaled
        A : float
            A multiplicative scaling factor applied to each band

        Returns
        -------
        image : numpy array
            The image after z-score scaling (subtract mean and divide by std deviation)
        """
        I = np.mean(im, axis=-1)
        Imean = np.nanmean(I)
        Isigma = np.nanstd(I)

        for i in range(im.shape[-1]):
            image[:, :, i] = A * (im[:, :, i] - Imean - m) / Isigma

        return image

    #This dict is created to map an input string to a scaling function
    norm_dict = {"raw": raw, "lupton": lupton}

    @classmethod
    def add_scaling(cls, name, func):
        """Add a custom contrast scaling function

        ex)
        def sqrt(image):
            image[:,:,0] = np.sqrt(image[:,:,0])
            image[:,:,1] = np.sqrt(image[:,:,1])
            image[:,:,2] = np.sqrt(image[:,:,2])
            return image

        ImageReader.add_scaling('sqrt',sqrt)
        """
        cls.norm_dict[name] = func
