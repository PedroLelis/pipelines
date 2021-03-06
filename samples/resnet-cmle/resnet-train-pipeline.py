#!/usr/bin/env python3
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import kfp.dsl as dsl
import kfp.gcp as gcp
import datetime

def resnet_preprocess_op(project_id: 'GcpProject', output: 'GcsUri', train_csv: 'GcsUri[text/csv]',
                         validation_csv: 'GcsUri[text/csv]', labels, step_name='preprocess'):
    return dsl.ContainerOp(
        name = step_name,
        image = 'gcr.io/ml-pipeline/resnet-preprocess:5df2cdc1ed145320204e8bc73b59cdbd7b3da28f',
        arguments = [
            '--project_id', project_id,
            '--output', output,
            '--train_csv', train_csv,
            '--validation_csv', validation_csv,
            '--labels', labels,
        ],
        file_outputs = {'preprocessed': '/output.txt'}
    )

def resnet_train_op(data_dir, output: 'GcsUri', region: 'GcpRegion', depth: int, train_batch_size: int,
                    eval_batch_size: int, steps_per_eval: int, train_steps: int, num_train_images: int,
                    num_eval_images: int, num_label_classes: int, tf_version, step_name='train'):
    return dsl.ContainerOp(
        name = step_name,
        image = 'gcr.io/ml-pipeline/resnet-train:5df2cdc1ed145320204e8bc73b59cdbd7b3da28f',
        arguments = [
            '--data_dir', data_dir,
            '--output', output,
            '--region', region,
            '--depth', depth,
            '--train_batch_size', train_batch_size,
            '--eval_batch_size', eval_batch_size,
            '--steps_per_eval', steps_per_eval,
            '--train_steps', train_steps,
            '--num_train_images', num_train_images,
            '--num_eval_images', num_eval_images,
            '--num_label_classes', num_label_classes,
            '--TFVERSION', tf_version
        ],
        file_outputs = {'trained': '/output.txt'}
    )

def resnet_deploy_op(model_dir, model, version, project_id: 'GcpProject', region: 'GcpRegion',
                     tf_version, step_name='deploy'):
    return dsl.ContainerOp(
        name = step_name,
        image = 'gcr.io/ml-pipeline/resnet-deploy:5df2cdc1ed145320204e8bc73b59cdbd7b3da28f',
        arguments = [
            '--model', model,
            '--version', version,
            '--project_id', project_id,
            '--region', region,
            '--model_dir', model_dir,
            '--TFVERSION', tf_version
        ]
    )


@dsl.pipeline(
  name='ResNet_Train_Pipeline',
  description='Demonstrate the ResNet50 predict.'
)
def resnet_train(
  project_id,
  output,
  region='us-central1',
  model='bolts',
  version='beta1',
  tf_version='1.9',
  train_csv='gs://bolts_image_dataset/bolt_images_train.csv',
  validation_csv='gs://bolts_image_dataset/bolt_images_validate.csv',
  labels='gs://bolts_image_dataset/labels.txt',
  depth=50,
  train_batch_size=1024,
  eval_batch_size=1024,
  steps_per_eval=250,
  train_steps=10000,
  num_train_images=218593,
  num_eval_images=54648,
  num_label_classes=10):

  preprocess = resnet_preprocess_op(project_id, output, train_csv,
      validation_csv, labels).apply(gcp.use_gcp_secret())
  train = resnet_train_op(preprocess.output, output, region, depth, train_batch_size,
      eval_batch_size, steps_per_eval, train_steps, num_train_images, num_eval_images,
      num_label_classes, tf_version).apply(gcp.use_gcp_secret())
  deploy = resnet_deploy_op(train.output, model, version, project_id, region,
      tf_version).apply(gcp.use_gcp_secret())

if __name__ == '__main__':
  import kfp.compiler as compiler
  compiler.Compiler().compile(resnet_train, __file__ + '.tar.gz')
