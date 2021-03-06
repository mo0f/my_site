from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf

# Modified from:
# https://github.com/tensorflow/models/blob/master/official/mnist/mnist.py
# https://github.com/tensorflow/tensorflow/blob/r1.1/tensorflow/examples/tutorials/layers/cnn_mnist.py
tf.logging.set_verbosity(tf.logging.INFO)

"""
Model function for CNN.
"""
def cnn_model_fn(features, labels, mode):
  # Input Layer
  input_layer = tf.reshape(features["x"], [-1, 28, 28, 1])

  # Convolutional Layer #1
  conv1 = tf.layers.conv2d(
      inputs=input_layer,
      filters=32,
      kernel_size=[5, 5],
      padding="same", #  This means to pad with 0, and keep output tensor 28x28
      activation=tf.nn.relu) # output size is batch x28x28x32

  # Pooling Layer #1, reduce height, width by 50%
  # Outputs batchx14x14x32
  pool1 = tf.layers.max_pooling2d(inputs=conv1, pool_size=[2, 2], strides=2) 

  # Convolutional Layer #2 and Pooling Layer #2
  conv2 = tf.layers.conv2d(
      inputs=pool1,
      filters=64,
      kernel_size=[5, 5],
      padding="same", # Output size is batchx14x14x64
      activation=tf.nn.relu) 
  pool2 = tf.layers.max_pooling2d(inputs=conv2, pool_size=[2, 2], strides=2) # Output = batchx7x7x64

    
  # Dense Layer
  pool2_flat = tf.reshape(pool2, [-1, 7 * 7 * 64]) # Flatten to batchx7x7x64 (one image + channels)
  dense = tf.layers.dense(inputs=pool2_flat, units=1024, activation=tf.nn.relu) # FC layer of batch x 1024 nodes
  dropout = tf.layers.dropout(
      inputs=dense, rate=0.4, training=mode == tf.estimator.ModeKeys.TRAIN) # 40% dropout on FC. Only done in train mode

  # Logits Layer
  logits = tf.layers.dense(inputs=dropout, units=10) # Node size 10 for all possible outputs. batch x 10 output.

  predictions = {
      # Generate predictions (for PREDICT and EVAL mode)
      "classes": tf.argmax(input=logits, axis=1),
      # Add `softmax_tensor` to the graph. It is used for PREDICT and by the `logging_hook`.
      "probabilities": tf.nn.softmax(logits, name="softmax_tensor")
  }

  export_outputs = {
    'prediction': tf.estimator.export.PredictOutput(predictions)
  }

  if mode == tf.estimator.ModeKeys.PREDICT:
    return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions,export_outputs=export_outputs)

  # Calculate Loss (for both TRAIN and EVAL modes)
  loss = tf.losses.sparse_softmax_cross_entropy(labels=labels, logits=logits)

  # Configure the Training Op (for TRAIN mode)
  if mode == tf.estimator.ModeKeys.TRAIN:
    optimizer = tf.train.GradientDescentOptimizer(learning_rate=0.001)
    train_op = optimizer.minimize(
        loss=loss,
        global_step=tf.train.get_global_step())
    return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op)

  # Add evaluation metrics (for EVAL mode)
  eval_metric_ops = {
      "accuracy": tf.metrics.accuracy(
          labels=labels, predictions=predictions["classes"])}
  return tf.estimator.EstimatorSpec(
      mode=mode, loss=loss, eval_metric_ops=eval_metric_ops)

def main(unused_argv):
  # Load training and eval data
  mnist = tf.contrib.learn.datasets.load_dataset("mnist")
  train_data = mnist.train.images  # Returns np.array
  train_labels = np.asarray(mnist.train.labels, dtype=np.int32)
  eval_data = mnist.test.images  # Returns np.array
  eval_labels = np.asarray(mnist.test.labels, dtype=np.int32)

  # Create the Estimator
  mnist_classifier = tf.estimator.Estimator(
      model_fn=cnn_model_fn, model_dir="mnist_convnet_model")

  # Set up logging for predictions
  # Log the values in the "Softmax" tensor with label "probabilities"
  tensors_to_log = {"probabilities": "softmax_tensor"}
  logging_hook = tf.train.LoggingTensorHook(
      tensors=tensors_to_log, every_n_iter=50)

  # Train the model
  train_input_fn = tf.estimator.inputs.numpy_input_fn(
      x={"x": train_data},
      y=train_labels,
      batch_size=100,
      num_epochs=None,
      shuffle=True)

  mnist_classifier.train(
      input_fn=train_input_fn,
      steps=20000,
      hooks=[logging_hook])

  # Evaluate the model and print results
  eval_input_fn = tf.estimator.inputs.numpy_input_fn(
      x={"x": eval_data},
      y=eval_labels,
      num_epochs=1,
      shuffle=False)
  eval_results = mnist_classifier.evaluate(input_fn=eval_input_fn)
  print(eval_results)

  # Export the model
  # https://stackoverflow.com/questions/44460362/how-to-save-estimator-in-tensorflow-for-later-use
  image = tf.placeholder(tf.float32, [None, 28, 28])
  serve_input_fn = tf.estimator.export.build_raw_serving_input_receiver_fn({
      'x': image,
  })
  mnist_classifier.export_savedmodel("mnist-saved-model", serve_input_fn)

if __name__ == "__main__":
  tf.app.run()

