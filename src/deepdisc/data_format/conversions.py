import os

import astropy.io.fits as fits
import h5py
import numpy as np
import scarlet
import json


def fitsim_to_numpy(img_files, outdir):
    """Converts a list of single-band FITS images to multi-band numpy arrays

    Parameters
    ----------
    img_files: list[str]
        A nested list of the FITS image files.
        The first index is the image and the second index is the filter
    outdir: str
        The directory to output the numpy arrays


    """

    for images in img_files:
        full_im = []
        for img in images:
            with fits.open(img, memmap=False, lazy_load_hdus=False) as hdul:
                data = hdul[0].data
                full_im.append(data)

        full_im = np.array(full_im)
        bn = os.path.basename(img)
        tract = int(bn.split("_")[1])
        patch = (int(bn.split("_")[2].split("_")[0][0]), int(bn.split("_")[2].split("_")[0][-1]))
        sp = int(bn.split("_")[3])

        np.save(os.path.join(outdir, f"{tract}_{patch[0]},{patch[1]}_{sp}_images.npy"), full_im)

    return


def fitsim_to_hdf5(img_files, outname, dset="train"):
    """Converts a list of single-band FITS images to flattened multi-band images in an hdf5 file

    Parameters
    ----------
    img_files: list[str]
        A nested list of the FITS image files.
        The first index is the image and the second index is the filter
    outname: str
        The name of the output file
    

    """
    all_images = []
    for images in img_files:
        full_im = []
        for img in images:
            with fits.open(img, memmap=False, lazy_load_hdus=False) as hdul:
                data = hdul[0].data
                full_im.append(data)

        full_im = np.array(full_im)
        all_images.append(full_im.flatten())
    all_images = np.array(all_images)

    with h5py.File(outname, "w") as f:
        data = f.create_dataset("images", data=all_images)

    return


def ddict_to_hdf5(dataset_dicts, outname):
    """Converts a list of dataset dictionaries to an hdf5 file (for RAIL usage)

    Parameters
    ----------
    dataset_dicts: list[dict]
        The dataset dicts
    outname: str
        The name of the output file
    """
    
    with h5py.File(outname, 'w') as file:
        data = [json.dumps(this_dict) for this_dict in dataset_dicts]
        dt = h5py.special_dtype(vlen=str)
        dataset = file.create_dataset('metadata_dicts', data=data, dtype=dt)
        
    return


def numpyim_to_hdf5(img_files, outname):
    """Converts a list of single-band FITS images to flattened multi-band images in an hdf5 file

    Parameters
    ----------
    img_files: list[str]
        A nested list of the FITS image files.
        The first index is the image and the second index is the filter
    outname: str
        The name of the output file
    

    """
    all_images = []
    for img_file in img_files:
        full_im = np.load(img_file)
        all_images.append(full_im.flatten())
    all_images = np.array(all_images)

    with h5py.File(outname, "w") as f:
        data = f.create_dataset("images", data=all_images)

    return