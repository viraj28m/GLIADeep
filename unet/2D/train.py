#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2019 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: EPL-2.0
#

"""
This module loads the data from data.py, creates a TensorFlow/Keras model
from model.py, trains the model on the data, and then saves the
best model.
"""

import datetime
import os

import tensorflow as tf  # conda install -c anaconda tensorflow
import settings   # Use the custom settings.py file for default parameters

from data import load_data

import numpy as np

from argparser import args

"""
For best CPU speed set the number of intra and inter threads
to take advantage of multi-core systems.
See https://github.com/intel/mkl-dnn
"""
#CONFIG = tf.ConfigProto(intra_op_parallelism_threads=args.num_threads,
#                        inter_op_parallelism_threads=args.num_inter_threads)

#SESS = tf.Session(config=CONFIG)
SESS = tf.Session()
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # Get rid of the AVX, SSE warnings
os.environ["OMP_NUM_THREADS"] = str(args.num_threads)
os.environ["KMP_BLOCKTIME"] = "1"

# If hyperthreading is enabled, then use
os.environ["KMP_AFFINITY"] = "granularity=thread,compact,1,0"

# If hyperthreading is NOT enabled, then use
#os.environ["KMP_AFFINITY"] = "granularity=thread,compact"

if args.keras_api:
    import keras as K
else:
    from tensorflow import keras as K

print("TensorFlow version: {}".format(tf.__version__))
print("Intel MKL-DNN is enabled = {}".format(tf.pywrap_tensorflow.IsMklEnabled()))

print("Keras API version: {}".format(K.__version__))

if args.channels_first:
    K.backend.set_image_data_format("channels_first")

K.backend.set_session(SESS)

def train_and_predict(data_path, data_filename, batch_size, n_epoch):
    """
    Create a model, load the data, and train it.
    """

    """
    Step 1: Load the data
    """
    hdf5_filename = os.path.join(data_path, data_filename)
    print("-" * 30)
    print("Loading the data from HDF5 file ...")
    print("-" * 30)
    print('hdf5_filename')
    print(hdf5_filename)
    imgs_train, msks_train, imgs_validation, msks_validation, \
        imgs_testing, msks_testing = \
        load_data(hdf5_filename, args.batch_size,
                  [args.crop_dim, args.crop_dim],
                  args.channels_first, args.seed)


    print("-" * 30)
    print("Creating and compiling model ...")
    print("-" * 30)

    """
    Step 2: Define the model
    """
    if args.use_pconv:
        from model_pconv import unet
    else:
        from model import unet

    unet_model = unet()
    model = unet_model.create_model(imgs_train.shape, msks_train.shape)

    model_filename, model_callbacks = unet_model.get_callbacks()

    # If there is a current saved file, then load weights and start from
    # there.
    saved_model = os.path.join(args.output_path, args.inference_filename)
    if os.path.isfile(saved_model):
        model.load_weights(saved_model)

    """
    Step 3: Train the model on the data
    """
    print("-" * 30)
    print("Fitting model with training data ...")
    print("-" * 30)

    model.fit(imgs_train, msks_train,
              batch_size=batch_size,
              epochs=n_epoch,
              validation_data=(imgs_validation, msks_validation),
              verbose=1, shuffle="batch",
              callbacks=model_callbacks)

    """
    Step 4: Evaluate the best model
    """
    print("-" * 30)
    print("Loading the best trained model ...")
    print("-" * 30)

    unet_model.evaluate_model(model_filename, imgs_testing, msks_testing)

    """
    Step 5: Save frozen TensorFlow version of model
    This can be convert into OpenVINO format with model optimizer.
    """
    print("-" * 30)
    print("Freezing model and saved to a TensorFlow protobuf ...")
    print("-" * 30)
    unet_model.save_frozen_model(model_filename, imgs_testing.shape)

if __name__ == "__main__":

    # os.system("lscpu")

    START_TIME = datetime.datetime.now()
    print("Started script on {}".format(START_TIME))

    print("args = {}".format(args))
    #os.system("uname -a")
    print("TensorFlow version: {}".format(tf.__version__))

    train_and_predict(args.data_path, args.data_filename,
                      args.batch_size, args.epochs)

    print(
        "Total time elapsed for program = {} seconds".format(
            datetime.datetime.now() -
            START_TIME))
    print("Stopped script on {}".format(datetime.datetime.now()))
