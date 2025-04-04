""" This is a demo "solo config" file for use in solo_test_run_transformers.py.

This uses template configs cascade_mask_rcnn_swin_b_in21k_50ep and yaml_style_defaults."""

from omegaconf import OmegaConf
import numpy as np
import os
# ---------------------------------------------------------------------------- #
# Local variables and metadata
# ---------------------------------------------------------------------------- #
epoch=2
bs=2
metadata = OmegaConf.create() 
metadata.classes = ["object"]

numclasses = len(metadata.classes)

# ---------------------------------------------------------------------------- #
# Standard config (this has always been the LazyConfig/.py-style config)
# ---------------------------------------------------------------------------- #
# Get values from templates
from ..COCO.cascade_mask_rcnn_swin_b_in21k_50ep import dataloader, model, train, lr_multiplier, optimizer
import deepdisc.model.loaders as loaders
from deepdisc.data_format.augment_image import dc2_train_augs, dc2_train_augs_full
from deepdisc.data_format.image_readers import DC2ImageReader

# Overrides
dataloader.augs = dc2_train_augs
dataloader.train.total_batch_size = bs

model.proposal_generator.anchor_generator.sizes = [[8], [16], [32], [64], [128]]
model.roi_heads.num_classes = numclasses
model.roi_heads.batch_size_per_image = 512

model.roi_heads.num_classes = numclasses
model.roi_heads.batch_size_per_image = 512


# ---------------------------------------------------------------------------- #
#Change for different data sets

#This is the number of color channels in the images
model.backbone.bottom_up.in_chans = 6         

#Take the averaged mean and standard deviations of each color channel in the test set
model.pixel_mean = [
        0.05381286,
        0.04986344,
        0.07526361,
        0.10420945,
        0.14229655,
        0.21245764,
]
model.pixel_std = [
        2.9318833,
        1.8443471,
        2.581817,
        3.5950038,
        4.5809164,
        7.302009,
]

# ---------------------------------------------------------------------------- #
model.proposal_generator.nms_thresh = 0.3

for box_predictor in model.roi_heads.box_predictors:
    box_predictor.test_topk_per_image = 2000
    box_predictor.test_score_thresh = 0.5
    box_predictor.test_nms_thresh = 0.3

#The ImageNet1k pretrained weights file.  Update to your own path
train.init_checkpoint = "/home/shared/hsc/detectron2/projects/ViTDet/model_final_246a82.pkl"

optimizer.lr = 0.001
dataloader.test.mapper = loaders.DictMapper
dataloader.train.mapper = loaders.DictMapper
dataloader.epoch=epoch

# ---------------------------------------------------------------------------- #
#Change for different data sets
reader = DC2ImageReader()
dataloader.imagereader = reader

# Key_mapper will take a metadatadict and return the key that the imagereader will use to read in the corresponding image
# Implemented so that if you move images on the disk or save as a different format, you don't have to change filepaths in the metadata
# Mostly, one can just have it return the filename key in the dictionary
def key_mapper(dataset_dict):
    '''
    args
        dataset_dict: [dict]
            A dictionary of metadata
    
    returns
        fn: str
            The filepath to the corresponding image
    
    '''
    filename = dataset_dict["filename"]
    base = os.path.basename(filename)
    dirpath = "../tests/deepdisc/test_data/dc2/"
    fn = os.path.join(dirpath, base)
    return fn


dataloader.key_mapper = key_mapper

# ---------------------------------------------------------------------------- #





# ---------------------------------------------------------------------------- #
# Yaml-style config (was formerly saved as a .yaml file, loaded to cfg_loader)
# ---------------------------------------------------------------------------- #
# Get values from template
from .yacs_style_defaults import MISC, DATALOADER, DATASETS, GLOBAL, INPUT, MODEL, SOLVER, TEST

# Overrides
SOLVER.IMS_PER_BATCH = bs

DATASETS.TRAIN = "astro_train"
DATASETS.TEST = "astro_val"

SOLVER.BASE_LR = 0.001
SOLVER.CLIP_GRADIENTS.ENABLED = True
# Type of gradient clipping, currently 2 values are supported:
# - "value": the absolute values of elements of each gradients are clipped
# - "norm": the norm of the gradient for each parameter is clipped thus
#   affecting all elements in the parameter
SOLVER.CLIP_GRADIENTS.CLIP_TYPE = "norm"
# Maximum absolute value used for clipping gradients
# Floating point number p for L-p norm to be used with the "norm"
# gradient clipping type; for L-inf, please specify .inf
SOLVER.CLIP_GRADIENTS.NORM_TYPE = 5.0


e1 = epoch * 15
e2 = epoch * 25
e3 = epoch * 30
efinal = epoch * 50

SOLVER.STEPS = [e1,e2,e3]  # do not decay learning rate for retraining
SOLVER.LR_SCHEDULER_NAME = "WarmupMultiStepLR"
SOLVER.WARMUP_ITERS = 0
SOLVER.MAX_ITER = efinal  # for DefaultTrainer
