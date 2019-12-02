from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import collections
from datetime import datetime
import hashlib
import os.path
import random
import re
import sys
# import tarfile
import csv
import time

import numpy as np
# from six.moves import urllib
import tensorflow as tf

FLAGS = None

# These are all parameters that are tied to the particular model architecture
# we're using for Inception v3. These include things like tensor names and their
# sizes. If you want to adapt this script to work with another model, you will
# need to update these to reflect the values in the network you're using.
MAX_NUM_IMAGES_PER_CLASS = (2 ** 27 - 1)  # ~134M


def create_image_lists(image_dir, testing_percentage, validation_percentage):
    if not tf.compat.v1.gfile.Exists(image_dir):
        tf.compat.v1.logging.error(
            "Image directory '" + image_dir + "' not found.")
        return None
    result = collections.OrderedDict()
    sub_dirs = [
        os.path.join(image_dir, item)
        for item in tf.compat.v1.gfile.ListDirectory(image_dir)]
    sub_dirs = sorted(item for item in sub_dirs
                      if tf.compat.v1.gfile.IsDirectory(item))
    for sub_dir in sub_dirs:
        extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp']
        file_list = []
        dir_name = os.path.basename(sub_dir)
        if dir_name == image_dir:
            continue
        tf.compat.v1.logging.info("Looking for images in '" + dir_name + "'")
        for extension in extensions:
            file_glob = os.path.join(image_dir, dir_name, '*.' + extension)
            file_list.extend(tf.compat.v1.gfile.Glob(file_glob))
        if not file_list:
            tf.compat.v1.logging.warning('No files found')
            continue
        if len(file_list) < 20:
            tf.compat.v1.logging.warning(
                'WARNING: Folder has less than 20 images, which may cause issues.')
        elif len(file_list) > MAX_NUM_IMAGES_PER_CLASS:
            tf.compat.v1.logging.warning(
                'WARNING: Folder {} has more than {} images. Some images will '
                'never be selected.'.format(dir_name, MAX_NUM_IMAGES_PER_CLASS))
        label_name = re.sub(r'[^a-z0-9]+', ' ', dir_name.lower())
        training_images = []
        testing_images = []
        validation_images = []
        for file_name in file_list:
            base_name = os.path.basename(file_name)
            hash_name = re.sub(r'_nohash_.*$', '', file_name)
            hash_name_hashed = hashlib.sha1(
                tf.compat.as_bytes(hash_name)).hexdigest()
            percentage_hash = ((int(hash_name_hashed, 16) %
                                (MAX_NUM_IMAGES_PER_CLASS + 1)) *
                               (100.0 / MAX_NUM_IMAGES_PER_CLASS))
            if percentage_hash < validation_percentage:
                validation_images.append(base_name)
            elif percentage_hash < (testing_percentage + validation_percentage):
                testing_images.append(base_name)
            else:
                training_images.append(base_name)
        result[label_name] = {
            'dir': dir_name,
            'training': training_images,
            'testing': testing_images,
            'validation': validation_images,
        }
    return result


def get_image_path(image_lists, label_name, index, image_dir, category):
    if label_name not in image_lists:
        tf.compat.v1.logging.fatal('Label does not exist %s.', label_name)
    label_lists = image_lists[label_name]
    if category not in label_lists:
        tf.compat.v1.logging.fatal('Category does not exist %s.', category)
    category_list = label_lists[category]
    if not category_list:
        tf.compat.v1.logging.fatal('Label %s has no images in the category %s.',
                                   label_name, category)
    mod_index = index % len(category_list)
    base_name = category_list[mod_index]
    sub_dir = label_lists['dir']
    full_path = os.path.join(image_dir, sub_dir, base_name)
    return full_path


def get_bottleneck_path(image_lists, label_name, index, bottleneck_dir,
                        category, architecture):
    return get_image_path(image_lists, label_name, index, bottleneck_dir,
                          category) + '_' + architecture + '.txt'


def create_model_graph(model_info):
    with tf.compat.v1.Graph().as_default() as graph:
        model_path = os.path.join(
            FLAGS.model_dir, model_info['model_file_name'])
        with tf.compat.v1.gfile.GFile(model_path, 'rb') as f:
            graph_def = tf.compat.v1.GraphDef()
            graph_def.ParseFromString(f.read())
            bottleneck_tensor, resized_input_tensor = (tf.compat.v1.import_graph_def(
                graph_def,
                name='',
                return_elements=[
                    model_info['bottleneck_tensor_name'],
                    model_info['resized_input_tensor_name'],
                ]))
    return graph, bottleneck_tensor, resized_input_tensor


def run_bottleneck_on_image(sess, image_data, image_data_tensor,
                            decoded_image_tensor, resized_input_tensor,
                            bottleneck_tensor):
    # First decode the JPEG image, resize it, and rescale the pixel values.
    resized_input_values = sess.run(decoded_image_tensor,
                                    {image_data_tensor: image_data})
    # Then run it through the recognition network.
    bottleneck_values = sess.run(bottleneck_tensor,
                                 {resized_input_tensor: resized_input_values})
    bottleneck_values = np.squeeze(bottleneck_values)
    return bottleneck_values


def ensure_dir_exists(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


bottleneck_path_2_bottleneck_values = {}


def create_bottleneck_file(bottleneck_path, image_lists, label_name, index,
                           image_dir, category, sess, jpeg_data_tensor,
                           decoded_image_tensor, resized_input_tensor,
                           bottleneck_tensor):
    """Create a single bottleneck file."""
    tf.compat.v1.logging.info('Creating bottleneck at ' + bottleneck_path)
    image_path = get_image_path(image_lists, label_name, index,
                                image_dir, category)
    if not tf.compat.v1.gfile.Exists(image_path):
        tf.compat.v1.logging.fatal('File does not exist %s', image_path)
    image_data = tf.compat.v1.gfile.GFile(image_path, 'rb').read()
    try:
        bottleneck_values = run_bottleneck_on_image(
            sess, image_data, jpeg_data_tensor, decoded_image_tensor,
            resized_input_tensor, bottleneck_tensor)
    except Exception as e:
        raise RuntimeError('Error during processing file %s (%s)' % (image_path,
                                                                     str(e)))
    bottleneck_string = ','.join(str(x) for x in bottleneck_values)
    with open(bottleneck_path, 'w') as bottleneck_file:
        bottleneck_file.write(bottleneck_string)


def get_or_create_bottleneck(sess, image_lists, label_name, index, image_dir,
                             category, bottleneck_dir, jpeg_data_tensor,
                             decoded_image_tensor, resized_input_tensor,
                             bottleneck_tensor, architecture):
    label_lists = image_lists[label_name]
    sub_dir = label_lists['dir']
    sub_dir_path = os.path.join(bottleneck_dir, sub_dir)
    ensure_dir_exists(sub_dir_path)
    bottleneck_path = get_bottleneck_path(image_lists, label_name, index,
                                          bottleneck_dir, category, architecture)
    if not os.path.exists(bottleneck_path):
        create_bottleneck_file(bottleneck_path, image_lists, label_name, index,
                               image_dir, category, sess, jpeg_data_tensor,
                               decoded_image_tensor, resized_input_tensor,
                               bottleneck_tensor)
    with open(bottleneck_path, 'r') as bottleneck_file:
        bottleneck_string = bottleneck_file.read()
    did_hit_error = False
    try:
        bottleneck_values = [float(x) for x in bottleneck_string.split(',')]
    except ValueError:
        tf.compat.v1.logging.warning(
            'Invalid float found, recreating bottleneck')
        did_hit_error = True
    if did_hit_error:
        create_bottleneck_file(bottleneck_path, image_lists, label_name, index,
                               image_dir, category, sess, jpeg_data_tensor,
                               decoded_image_tensor, resized_input_tensor,
                               bottleneck_tensor)
        with open(bottleneck_path, 'r') as bottleneck_file:
            bottleneck_string = bottleneck_file.read()
        # Allow exceptions to propagate here, since they shouldn't happen after a
        # fresh creation
        bottleneck_values = [float(x) for x in bottleneck_string.split(',')]
    return bottleneck_values


def cache_bottlenecks(sess, image_lists, image_dir, bottleneck_dir,
                      jpeg_data_tensor, decoded_image_tensor,
                      resized_input_tensor, bottleneck_tensor, architecture):
    how_many_bottlenecks = 0
    ensure_dir_exists(bottleneck_dir)
    for label_name, label_lists in image_lists.items():
        for category in ['training', 'testing', 'validation']:
            category_list = label_lists[category]
            for index, unused_base_name in enumerate(category_list):
                get_or_create_bottleneck(
                    sess, image_lists, label_name, index, image_dir, category,
                    bottleneck_dir, jpeg_data_tensor, decoded_image_tensor,
                    resized_input_tensor, bottleneck_tensor, architecture)

                how_many_bottlenecks += 1
                if how_many_bottlenecks % 100 == 0:
                    tf.compat.v1.logging.info(
                        str(how_many_bottlenecks) + ' bottleneck files created.')


def get_random_cached_bottlenecks(sess, image_lists, how_many, category,
                                  bottleneck_dir, image_dir, jpeg_data_tensor,
                                  decoded_image_tensor, resized_input_tensor,
                                  bottleneck_tensor, architecture):
    class_count = len(image_lists.keys())
    bottlenecks = []
    ground_truths = []
    filenames = []
    if how_many >= 0:
        # Retrieve a random sample of bottlenecks.
        for unused_i in range(how_many):
            label_index = random.randrange(class_count)
            label_name = list(image_lists.keys())[label_index]
            image_index = random.randrange(MAX_NUM_IMAGES_PER_CLASS + 1)
            image_name = get_image_path(image_lists, label_name, image_index,
                                        image_dir, category)
            bottleneck = get_or_create_bottleneck(
                sess, image_lists, label_name, image_index, image_dir, category,
                bottleneck_dir, jpeg_data_tensor, decoded_image_tensor,
                resized_input_tensor, bottleneck_tensor, architecture)
            ground_truth = np.zeros(class_count, dtype=np.float32)
            ground_truth[label_index] = 1.0
            bottlenecks.append(bottleneck)
            ground_truths.append(ground_truth)
            filenames.append(image_name)
    else:
        # Retrieve all bottlenecks.
        for label_index, label_name in enumerate(image_lists.keys()):
            for image_index, image_name in enumerate(
                    image_lists[label_name][category]):
                image_name = get_image_path(image_lists, label_name, image_index,
                                            image_dir, category)
                bottleneck = get_or_create_bottleneck(
                    sess, image_lists, label_name, image_index, image_dir, category,
                    bottleneck_dir, jpeg_data_tensor, decoded_image_tensor,
                    resized_input_tensor, bottleneck_tensor, architecture)
                ground_truth = np.zeros(class_count, dtype=np.float32)
                ground_truth[label_index] = 1.0
                bottlenecks.append(bottleneck)
                ground_truths.append(ground_truth)
                filenames.append(image_name)
    return bottlenecks, ground_truths, filenames


def get_random_distorted_bottlenecks(
        sess, image_lists, how_many, category, image_dir, input_jpeg_tensor,
        distorted_image, resized_input_tensor, bottleneck_tensor):
    class_count = len(image_lists.keys())
    bottlenecks = []
    ground_truths = []
    for unused_i in range(how_many):
        label_index = random.randrange(class_count)
        label_name = list(image_lists.keys())[label_index]
        image_index = random.randrange(MAX_NUM_IMAGES_PER_CLASS + 1)
        image_path = get_image_path(image_lists, label_name, image_index, image_dir,
                                    category)
        if not tf.compat.v1.gfile.Exists(image_path):
            tf.compat.v1.logging.fatal('File does not exist %s', image_path)
        jpeg_data = tf.compat.v1.gfile.GFile(image_path, 'rb').read()
        # Note that we materialize the distorted_image_data as a numpy array before
        # sending running inference on the image. This involves 2 memory copies and
        # might be optimized in other implementations.
        distorted_image_data = sess.run(distorted_image,
                                        {input_jpeg_tensor: jpeg_data})
        bottleneck_values = sess.run(bottleneck_tensor,
                                     {resized_input_tensor: distorted_image_data})
        bottleneck_values = np.squeeze(bottleneck_values)
        ground_truth = np.zeros(class_count, dtype=np.float32)
        ground_truth[label_index] = 1.0
        bottlenecks.append(bottleneck_values)
        ground_truths.append(ground_truth)
    return bottlenecks, ground_truths


def should_distort_images(flip_left_right, random_crop, random_scale,
                          random_brightness):
    return (flip_left_right or (random_crop != 0) or (random_scale != 0) or
            (random_brightness != 0))


def add_input_distortions(flip_left_right, random_crop, random_scale,
                          random_brightness, input_width, input_height,
                          input_depth, input_mean, input_std):

    jpeg_data = tf.compat.v1.placeholder(
        tf.tf.compat.v1, name='DistortJPGInput')
    decoded_image = tf.compat.v1.image.decode_jpeg(
        jpeg_data, channels=input_depth)
    decoded_image_as_float = tf.compat.v1.cast(
        decoded_image, dtype=tf.compat.v1.float32)
    decoded_image_4d = tf.compat.v1.expand_dims(decoded_image_as_float, 0)
    margin_scale = 1.0 + (random_crop / 100.0)
    resize_scale = 1.0 + (random_scale / 100.0)
    margin_scale_value = tf.compat.v1.constant(margin_scale)
    resize_scale_value = tf.compat.v1.random_uniform(tf.compat.v1.TensorShape([]),
                                                     minval=1.0,
                                                     maxval=resize_scale)
    scale_value = tf.compat.v1.multiply(margin_scale_value, resize_scale_value)
    precrop_width = tf.compat.v1.multiply(scale_value, input_width)
    precrop_height = tf.compat.v1.multiply(scale_value, input_height)
    precrop_shape = tf.compat.v1.stack([precrop_height, precrop_width])
    precrop_shape_as_int = tf.compat.v1.cast(precrop_shape, dtype=tf.int32)
    precropped_image = tf.compat.v1.image.resize_bilinear(decoded_image_4d,
                                                          precrop_shape_as_int)
    precropped_image_3d = tf.compat.v1.squeeze(
        precropped_image, squeeze_dims=[0])
    cropped_image = tf.compat.v1.random_crop(precropped_image_3d,
                                             [input_height, input_width, input_depth])
    if flip_left_right:
        flipped_image = tf.compat.v1.image.random_flip_left_right(
            cropped_image)
    else:
        flipped_image = cropped_image
    brightness_min = 1.0 - (random_brightness / 100.0)
    brightness_max = 1.0 + (random_brightness / 100.0)
    tf.compat.v1.scalar
    brightness_value = tf.compat.v1.random_uniform(tf.compat.v1.TensorShape([]),
                                                   minval=brightness_min,
                                                   maxval=brightness_max)
    brightened_image = tf.compat.v1.multiply(flipped_image, brightness_value)
    offset_image = tf.compat.v1.subtract(brightened_image, input_mean)
    mul_image = tf.compat.v1.multiply(offset_image, 1.0 / input_std)
    distort_result = tf.compat.v1.expand_dims(
        mul_image, 0, name='DistortResult')
    return jpeg_data, distort_result


def variable_summaries(var):
    """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
    with tf.compat.v1.name_scope('summaries'):
        mean = tf.compat.v1.reduce_mean(var)
        tf.compat.v1.summary.scalar('mean', mean)
        with tf.compat.v1.name_scope('stddev'):
            stddev = tf.compat.v1.sqrt(
                tf.compat.v1.reduce_mean(tf.compat.v1.square(var - mean)))
        tf.compat.v1.summary.scalar('stddev', stddev)
        tf.compat.v1.summary.scalar('max', tf.compat.v1.reduce_max(var))
        tf.compat.v1.summary.scalar('min', tf.compat.v1.reduce_min(var))
        tf.compat.v1.summary.histogram('histogram', var)


def add_final_training_ops(class_count, final_tensor_name, bottleneck_tensor,
                           bottleneck_tensor_size, learning_rate):
    with tf.compat.v1.name_scope('input'):
        bottleneck_input = tf.compat.v1.placeholder_with_default(
            bottleneck_tensor,
            shape=[None, bottleneck_tensor_size],
            name='BottleneckInputPlaceholder')

        ground_truth_input = tf.compat.v1.placeholder(tf.compat.v1.float32,
                                                      [None, class_count],
                                                      name='GroundTruthInput')

    # Organizing the following ops as `final_training_ops` so they're easier
    # to see in TensorBoard
    layer_name = 'final_training_ops'
    with tf.compat.v1.name_scope(layer_name):
        with tf.compat.v1.name_scope('weights'):
            initial_value = tf.compat.v1.random.truncated_normal(
                [bottleneck_tensor_size, class_count], stddev=0.001)

            layer_weights = tf.compat.v1.Variable(
                initial_value, name='final_weights')

            variable_summaries(layer_weights)
        with tf.compat.v1.name_scope('biases'):
            layer_biases = tf.compat.v1.Variable(
                tf.compat.v1.zeros([class_count]), name='final_biases')
            variable_summaries(layer_biases)
        with tf.compat.v1.name_scope('Wx_plus_b'):
            logits = tf.compat.v1.matmul(
                bottleneck_input, layer_weights) + layer_biases
            tf.compat.v1.summary.histogram('pre_activations', logits)

    final_tensor = tf.nn.softmax(logits, name=final_tensor_name)
    tf.compat.v1.summary.histogram('activations', final_tensor)

    with tf.compat.v1.name_scope('cross_entropy'):
        cross_entropy = tf.compat.v2.nn.softmax_cross_entropy_with_logits(
            labels=ground_truth_input, logits=logits)
        with tf.compat.v1.name_scope('total'):
            cross_entropy_mean = tf.compat.v1.reduce_mean(cross_entropy)
    tf.compat.v1.summary.scalar('cross_entropy', cross_entropy_mean)

    with tf.compat.v1.name_scope('train'):
        optimizer = tf.compat.v1.train.GradientDescentOptimizer(
            learning_rate)
        train_step = optimizer.minimize(cross_entropy_mean)

    return (train_step, cross_entropy_mean, bottleneck_input, ground_truth_input,
            final_tensor)


def add_evaluation_step(result_tensor, ground_truth_tensor):
    with tf.compat.v1.name_scope('accuracy'):
        with tf.compat.v1.name_scope('correct_prediction'):
            prediction = tf.argmax(result_tensor, 1)
            correct_prediction = tf.compat.v1.equal(
                prediction, tf.compat.v1.argmax(ground_truth_tensor, 1))
        with tf.compat.v1.name_scope('accuracy'):
            evaluation_step = tf.compat.v1.reduce_mean(
                tf.compat.v1.cast(correct_prediction, tf.compat.v1.float32))
    tf.compat.v1.summary.scalar('accuracy', evaluation_step)
    return evaluation_step, prediction


def save_graph_to_file(sess, graph, graph_file_name):
    output_graph_def = tf.compat.v1.graph_util.convert_variables_to_constants(
        sess, graph.as_graph_def(), [FLAGS.final_tensor_name])
    with tf.compat.v1.gfile.GFile(graph_file_name, 'wb') as f:
        f.write(output_graph_def.SerializeToString())
    return


def prepare_file_system(summaries_dir):
    # Setup the directory we'll write summaries to for TensorBoard
    if tf.compat.v1.gfile.Exists(summaries_dir):
        tf.compat.v1.gfile.DeleteRecursively(summaries_dir)
    tf.compat.v1.gfile.MakeDirs(summaries_dir)
    if FLAGS.intermediate_store_frequency > 0:
        ensure_dir_exists(FLAGS.intermediate_output_graphs_dir)
    return


def create_model_info(architecture):
    architecture = architecture.lower()
    if architecture == 'inception_v3':
        data_url = ''
        bottleneck_tensor_name = 'pool_3/_reshape:0'
        bottleneck_tensor_size = 2048
        input_width = 299
        input_height = 299
        input_depth = 3
        resized_input_tensor_name = 'Mul:0'
        model_file_name = 'classify_image_graph_def_inception_v3.pb'
        input_mean = 128
        input_std = 128
    elif architecture.startswith('mobilenet_v1'):
        data_url = ''
        bottleneck_tensor_name = 'MobilenetV1/Predictions/Reshape:0'
        bottleneck_tensor_size = 1001
        input_width = 224
        input_height = 224
        input_depth = 3
        resized_input_tensor_name = 'input:0'
        model_file_name = 'classify_image_graph_def_mobilenet_v1_1.0_224.pb'
        input_mean = 127.5
        input_std = 127.5
    elif architecture.startswith('mobilenet_v2'):
        data_url = ''
        bottleneck_tensor_name = 'MobilenetV2/Predictions/Reshape:0'
        bottleneck_tensor_size = 1001
        input_width = 224
        input_height = 224
        input_depth = 3
        resized_input_tensor_name = 'input:0'
        model_file_name = 'classify_image_graph_def_mobilenet_v2_1.4_224.pb'
        input_mean = 127.5
        input_std = 127.5
    else:
        tf.compat.v1.logging.error(
            "Couldn't understand architecture name '%s'", architecture)
        raise ValueError('Unknown architecture', architecture)

    return {
        'data_url': data_url,
        'bottleneck_tensor_name': bottleneck_tensor_name,
        'bottleneck_tensor_size': bottleneck_tensor_size,
        'input_width': input_width,
        'input_height': input_height,
        'input_depth': input_depth,
        'resized_input_tensor_name': resized_input_tensor_name,
        'model_file_name': model_file_name,
        'input_mean': input_mean,
        'input_std': input_std,
    }


def add_jpeg_decoding(input_width, input_height, input_depth, input_mean,
                      input_std):
    jpeg_data = tf.compat.v1.placeholder(
        tf.compat.v1.string, name='DecodeJPGInput')
    decoded_image = tf.compat.v1.image.decode_jpeg(
        jpeg_data, channels=input_depth)
    decoded_image_as_float = tf.compat.v1.cast(
        decoded_image, dtype=tf.compat.v1.float32)
    decoded_image_4d = tf.compat.v1.expand_dims(decoded_image_as_float, 0)
    resize_shape = tf.compat.v1.stack([input_height, input_width])
    resize_shape_as_int = tf.compat.v1.cast(
        resize_shape, dtype=tf.compat.v1.int32)
    resized_image = tf.compat.v1.image.resize_bilinear(decoded_image_4d,
                                                       resize_shape_as_int)
    offset_image = tf.compat.v1.subtract(resized_image, input_mean)
    mul_image = tf.compat.v1.multiply(offset_image, 1.0 / input_std)
    return jpeg_data, mul_image


def main(_):
    # Needed to make sure the logging output is visible.
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.INFO)

    model_name_list = ['mobilenet_v1_1.0_224',
                       'mobilenet_v2_1.4_224', 'inception_v3']
    # learning_rate_list = [0.0001, 0.0005,
    #                       0.001, 0.005, 0.01, 0.05, 0.1]
    # training_step_list = [100, 200, 300, 400,
    #                       500, 600, 700, 800, 900, 1000]
    # testing_and_validating_percentage_list = [10, 20, 30]
    learning_rate_list = [0.0001]
    training_step_list = [100]
    testing_and_validating_percentage_list = [10]
    NO = 1

    with open("tests.csv", "w", newline="") as f:
        fieldnames = ['NO', 'model name', 'percent test', 'learning rate', 'training step',
                      'train accuracy', 'cross entropy', 'validation accuracy', 'final test accuracy', 'time']
        TheWriter = csv.DictWriter(f, fieldnames=fieldnames)
        TheWriter.writeheader()
        row = {
            'NO': NO,
            'model name': None,
            'percent test': None,
            'learning rate': None,
            'training step': None,
            'train accuracy': None,
            'cross entropy': None,
            'validation accuracy': None,
            'final test accuracy': None,
            'time': None
        }
        for model_name in model_name_list:
            row['model name'] = model_name
            # Gather information about the model architecture we'll be using.
            model_info = create_model_info(model_name)
            if not model_info:
                tf.compat.v1.logging.error(
                    'Did not recognize architecture flag')
                return -1
            for percent_test_validate in testing_and_validating_percentage_list:
                row['percent test'] = percent_test_validate
                # Look at the folder structure, and create lists of all the images.
                image_lists = create_image_lists(FLAGS.image_dir, percent_test_validate,
                                                 percent_test_validate)
                class_count = len(image_lists.keys())
                if class_count == 0:
                    tf.compat.v1.logging.error(
                        'No valid folders of images found at ' + FLAGS.image_dir)
                    return -1
                if class_count == 1:
                    tf.compat.v1.logging.error('Only one valid folder of images found at ' +
                                               FLAGS.image_dir +
                                               ' - multiple classes are needed for classification.')
                    return -1
                    # See if the command-line flags mean we're applying any distortions.
                do_distort_images = should_distort_images(
                    FLAGS.flip_left_right, FLAGS.random_crop, FLAGS.random_scale,
                    FLAGS.random_brightness)

                for learning_rate in learning_rate_list:
                    row['learning rate'] = learning_rate
                    graph, bottleneck_tensor, resized_image_tensor = (
                        create_model_graph(model_info))
                    # tf.compat.v1.reset_default_graph()
                    # _ = tf.compat.v1.Variable(0)
                    with tf.compat.v1.Session(graph=graph) as sess:
                        # Set up the image decoding sub-graph.
                        jpeg_data_tensor, decoded_image_tensor = add_jpeg_decoding(
                            model_info['input_width'], model_info['input_height'],
                            model_info['input_depth'], model_info['input_mean'],
                            model_info['input_std'])
                        if do_distort_images:
                            # We will be applying distortions, so setup the operations we'll need.
                            (distorted_jpeg_data_tensor,
                             distorted_image_tensor) = add_input_distortions(
                                FLAGS.flip_left_right, FLAGS.random_crop, FLAGS.random_scale,
                                FLAGS.random_brightness, model_info['input_width'],
                                model_info['input_height'], model_info['input_depth'],
                                model_info['input_mean'], model_info['input_std'])
                        else:
                            # We'll make sure we've calculated the 'bottleneck' image summaries and
                            # cached them on disk.
                            cache_bottlenecks(sess, image_lists, FLAGS.image_dir,
                                              FLAGS.bottleneck_dir, jpeg_data_tensor,
                                              decoded_image_tensor, resized_image_tensor,
                                              bottleneck_tensor, model_name)

                        # Add the new layer that we'll be training.
                        (train_step, cross_entropy, bottleneck_input, ground_truth_input,
                         final_tensor) = add_final_training_ops(
                            len(image_lists.keys()
                                ), FLAGS.final_tensor_name, bottleneck_tensor,
                            model_info['bottleneck_tensor_size'], learning_rate)

                        # Create the operations we need to evaluate the accuracy of our new layer.
                        evaluation_step, prediction = add_evaluation_step(
                            final_tensor, ground_truth_input)
                        for training_step in training_step_list:
                            row['training step'] = training_step
                            summaries_dir = 'tf/tf_files/training_summaries/{}-PT{}-LR{}-TS{}/'.format(
                                model_name, percent_test_validate, learning_rate, training_step)
                            # Prepare necessary directories  that can be used during training
                            prepare_file_system(summaries_dir)
                            # Merge all the summaries and write them out to the summaries_dir
                            merged = tf.compat.v1.summary.merge_all()
                            train_writer = tf.compat.v1.summary.FileWriter(summaries_dir + '/train',
                                                                           sess.graph)

                            validation_writer = tf.compat.v1.summary.FileWriter(
                                summaries_dir + '/validation')

                            start = time.time()
                            # Set up all our weights to their initial default values.
                            init = tf.compat.v1.global_variables_initializer()
                            sess.run(init)

                            # Run the training for as many cycles as requested on the command line.
                            for i in range(training_step):
                                # Get a batch of input bottleneck values, either calculated fresh every
                                # time with distortions applied, or from the cache stored on disk.
                                if do_distort_images:
                                    (train_bottlenecks,
                                     train_ground_truth) = get_random_distorted_bottlenecks(
                                        sess, image_lists, FLAGS.train_batch_size, 'training',
                                        FLAGS.image_dir, distorted_jpeg_data_tensor,
                                        distorted_image_tensor, resized_image_tensor, bottleneck_tensor)
                                else:
                                    (train_bottlenecks,
                                     train_ground_truth, _) = get_random_cached_bottlenecks(
                                        sess, image_lists, FLAGS.train_batch_size, 'training',
                                        FLAGS.bottleneck_dir, FLAGS.image_dir, jpeg_data_tensor,
                                        decoded_image_tensor, resized_image_tensor, bottleneck_tensor,
                                        model_name)
                                # Feed the bottlenecks and ground truth into the graph, and run a training
                                # step. Capture training summaries for TensorBoard with the `merged` op.
                                train_summary, _ = sess.run(
                                    [merged, train_step],
                                    feed_dict={bottleneck_input: train_bottlenecks,
                                               ground_truth_input: train_ground_truth})
                                train_writer.add_summary(train_summary, i)

                                # Every so often, print out how well the graph is training.
                                is_last_step = (i + 1 == training_step)
                                if (i % FLAGS.eval_step_interval) == 0 or is_last_step:
                                    train_accuracy, cross_entropy_value = sess.run(
                                        [evaluation_step, cross_entropy],
                                        feed_dict={bottleneck_input: train_bottlenecks,
                                                   ground_truth_input: train_ground_truth})
                                    tf.compat.v1.logging.info('%s: Step %d: Train accuracy = %.2f%%' %
                                                              (datetime.now(), i, train_accuracy * 100))
                                    tf.compat.v1.logging.info('%s: Step %d: Cross entropy = %f' %
                                                              (datetime.now(), i, cross_entropy_value))
                                    validation_bottlenecks, validation_ground_truth, _ = (
                                        get_random_cached_bottlenecks(
                                            sess, image_lists, FLAGS.validation_batch_size, 'validation',
                                            FLAGS.bottleneck_dir, FLAGS.image_dir, jpeg_data_tensor,
                                            decoded_image_tensor, resized_image_tensor, bottleneck_tensor,
                                            model_name))
                                    # Run a validation step and capture training summaries for TensorBoard
                                    # with the `merged` op.
                                    validation_summary, validation_accuracy = sess.run(
                                        [merged, evaluation_step],
                                        feed_dict={bottleneck_input: validation_bottlenecks,
                                                   ground_truth_input: validation_ground_truth})
                                    validation_writer.add_summary(
                                        validation_summary, i)
                                    tf.compat.v1.logging.info('%s: Step %d: Validation accuracy = %.1f%% (N=%d)' %
                                                              (datetime.now(), i, validation_accuracy * 100,
                                                               len(validation_bottlenecks)))
                                    row['train accuracy'] = '{:.2f}'.format(
                                        train_accuracy * 100)
                                    row['cross entropy'] = '{:.2f}'.format(
                                        cross_entropy_value)
                                    row['validation accuracy'] = '{:.2f}'.format(
                                        validation_accuracy * 100)
                                # Store intermediate results
                                intermediate_frequency = FLAGS.intermediate_store_frequency

                                if (intermediate_frequency > 0 and (i % intermediate_frequency == 0)
                                        and i > 0):
                                    intermediate_file_name = (FLAGS.intermediate_output_graphs_dir +
                                                              'intermediate_' + str(i) + '.pb')
                                    tf.compat.v1.logging.info('Save intermediate result to : ' +
                                                              intermediate_file_name)
                                    save_graph_to_file(
                                        sess, graph, intermediate_file_name)

                            # We've completed all our training, so run a final test evaluation on
                            # some new images we haven't used before.
                            test_bottlenecks, test_ground_truth, test_filenames = (
                                get_random_cached_bottlenecks(
                                    sess, image_lists, FLAGS.test_batch_size, 'testing',
                                    FLAGS.bottleneck_dir, FLAGS.image_dir, jpeg_data_tensor,
                                    decoded_image_tensor, resized_image_tensor, bottleneck_tensor,
                                    model_name))
                            test_accuracy, predictions = sess.run(
                                [evaluation_step, prediction],
                                feed_dict={bottleneck_input: test_bottlenecks,
                                           ground_truth_input: test_ground_truth})
                            tf.compat.v1.logging.info('Final test accuracy = %.2f%% (N=%d)' %
                                                      (test_accuracy * 100, len(test_bottlenecks)))
                            row['final test accuracy'] = '{:.2f}'.format(
                                test_accuracy * 100)

                            if FLAGS.print_misclassified_test_images:
                                tf.compat.v1.logging.info(
                                    '=== MISCLASSIFIED TEST IMAGES ===')
                                for i, test_filename in enumerate(test_filenames):
                                    if predictions[i] != test_ground_truth[i].argmax():
                                        tf.compat.v1.logging.info('%70s  %s' %
                                                                  (test_filename,
                                                                   list(image_lists.keys())[predictions[i]]))
                            end = time.time()
                            # Write out the trained graph and labels with the weights stored as
                            # constants.
                            output_graph = 'tf/tf_files/retrained_graphs/retrained_graph_{}-PT{}-LR{}-TS{}.pb'.format(
                                model_name, percent_test_validate, learning_rate, training_step)
                            save_graph_to_file(sess, graph, output_graph)
                            row['time'] = round(end - start, 2)
                            row['NO'] = NO
                            TheWriter.writerow(row)
                            NO = NO + 1
                with tf.compat.v1.gfile.GFile(FLAGS.output_labels, 'w') as f:
                    f.write('\n'.join(image_lists.keys()) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--image_dir',
        type=str,
        default='tf/tf_files/dataset',
        help='Path to folders of labeled images.'
    )
    parser.add_argument(
        '--output_graph',
        type=str,
        default='tf/tf_files/retrained_graph.pb',
        help='Where to save the trained graph.'
    )
    parser.add_argument(
        '--intermediate_output_graphs_dir',
        type=str,
        default='tf/tf_files/intermediate_graph/',
        help='Where to save the intermediate graphs.'
    )
    parser.add_argument(
        '--intermediate_store_frequency',
        type=int,
        default=0,
        help="""\
         How many steps to store intermediate graph. If "0" then will not
         store.\
      """
    )
    parser.add_argument(
        '--output_labels',
        type=str,
        default='tf/tf_files/retrained_labels.txt',
        help='Where to save the trained graph\'s labels.'
    )
    parser.add_argument(
        '--summaries_dir',
        type=str,
        default='tf/tf_files/training_summaries/',
        help='Where to save summary logs for TensorBoard.'
    )
    parser.add_argument(
        '--how_many_training_steps',
        type=int,
        default=100,
        help='How many training steps to run before ending.'
    )
    parser.add_argument(
        '--learning_rate',
        type=float,
        default=0.01,
        help='How large a learning rate to use when training.'
    )
    parser.add_argument(
        '--testing_percentage',
        type=int,
        default=10,
        help='What percentage of images to use as a test set.'
    )
    parser.add_argument(
        '--validation_percentage',
        type=int,
        default=10,
        help='What percentage of images to use as a validation set.'
    )
    parser.add_argument(
        '--eval_step_interval',
        type=int,
        default=10,
        help='How often to evaluate the training results.'
    )
    parser.add_argument(
        '--train_batch_size',
        type=int,
        default=100,
        help='How many images to train on at a time.'
    )
    parser.add_argument(
        '--test_batch_size',
        type=int,
        default=-1,
        help="""\
      How many images to test on. This test set is only used once, to evaluate
      the final accuracy of the model after training completes.
      A value of -1 causes the entire test set to be used, which leads to more
      stable results across runs.\
      """
    )
    parser.add_argument(
        '--validation_batch_size',
        type=int,
        default=100,
        help="""\
      How many images to use in an evaluation batch. This validation set is
      used much more often than the test set, and is an early indicator of how
      accurate the model is during training.
      A value of -1 causes the entire validation set to be used, which leads to
      more stable results across training iterations, but may be slower on large
      training sets.\
      """
    )
    parser.add_argument(
        '--print_misclassified_test_images',
        default=False,
        help="""\
      Whether to print out a list of all misclassified test images.\
      """,
        action='store_true'
    )
    parser.add_argument(
        '--model_dir',
        type=str,
        default='tf/tf_files/models',
        help="""\
      Path to classify_image_graph_def.pb,
      imagenet_synset_to_human_label_map.txt, and
      imagenet_2012_challenge_label_map_proto.pbtxt.\
      """
    )
    parser.add_argument(
        '--bottleneck_dir',
        type=str,
        default='tf/tf_files/bottlenecks',
        help='Path to cache bottleneck layer values as files.'
    )
    parser.add_argument(
        '--final_tensor_name',
        type=str,
        default='final_result',
        help="""\
      The name of the output classification layer in the retrained graph.\
      """
    )
    parser.add_argument(
        '--flip_left_right',
        default=False,
        help="""\
      Whether to randomly flip half of the training images horizontally.\
      """,
        action='store_true'
    )
    parser.add_argument(
        '--random_crop',
        type=int,
        default=0,
        help="""\
      A percentage determining how much of a margin to randomly crop off the
      training images.\
      """
    )
    parser.add_argument(
        '--random_scale',
        type=int,
        default=0,
        help="""\
      A percentage determining how much to randomly scale up the size of the
      training images by.\
      """
    )
    parser.add_argument(
        '--random_brightness',
        type=int,
        default=0,
        help="""\
      A percentage determining how much to randomly multiply the training image
      input pixels up or down by.\
      """
    )
    parser.add_argument(
        '--architecture',
        type=str,
        default='inception_v3',
        help="""\
      Which model architecture to use. 'inception_v3' is the most accurate, but
      also the slowest. For faster or smaller models, chose a MobileNet with the
      form 'mobilenet_<parameter size>_<input_size>[_quantized]'. For example,
      'mobilenet_1.0_224' will pick a model that is 17 MB in size and takes 224
      pixel input images, while 'mobilenet_0.25_128_quantized' will choose a much
      less accurate, but smaller and faster network that's 920 KB on disk and
      takes 128x128 images. See https://research.googleblog.com/2017/06/mobilenets-open-source-models-for.html
      for more information on Mobilenet.\
      """)
    FLAGS, unparsed = parser.parse_known_args()
    tf.compat.v1.app.run(main=main, argv=[sys.argv[0]] + unparsed)
