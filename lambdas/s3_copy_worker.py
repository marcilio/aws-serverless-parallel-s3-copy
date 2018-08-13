# ------------------------------------------------------------------------------
# This Lambda function copies a list of files (payload) from a source to a target
# S3 bucket. Multiple payloads can be handled but only one per execution to prevent
# timeouts. Upon completing the processing of a payload the Lambda function will 
# update the last processed payload index and return as JSON result. 
# This Lambda function is called by a AWS Step Functions state machine.
# ------------------------------------------------------------------------------

import boto3
import logging
import json
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.client('s3')

# def copy(index, source_s3_location, target_s3_location):
#     target_key = '{}.{}'.format(target_s3_location['key'], index)
#     copy_source = {
#         'Bucket': source_s3_location['bucket'],
#         'Key': source_s3_location['key']
#     }
#     # log('{}: Copying S3 file s3://{}/{} into s3://{}/{}'.format(index, source_s3_location['bucket'],
#     #                                                             source_s3_location['key'], target_s3_location['bucket'], target_key))
#     start_time = time.time()
#     s3.meta.client.copy(
#         copy_source, target_s3_location['bucket'], target_key)
#     log('{}, {}'.format(
#         index, (time.time() - start_time)))

# {
#   "s3_copy_config": {
#     "source_s3_config": {
#       "s3_bucket": "aws-s3-serverless-parallel-copy",
#       "s3_path": "source/"
#     },
#     "target_s3_config": [
#       {
#         "file_types": [
#           "zip",
#           "jpg",
#           "mp4"
#         ],
#         "s3_bucket": "aws-s3-serverless-parallel-copy",
#         "s3_path": "target/"
#       }
#     ]
#   }
# }
def handler(event, context):
    try:
        print(event)
        return event
    except Exception as e:
        logger.error(str(e))
        raise e
