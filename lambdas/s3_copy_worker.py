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
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.resource('s3')

def s3_copy(source_s3_location, target_s3_location):
    copy_source = {
        'Bucket': source_s3_location['bucket'],
        'Key': source_s3_location['key']
    }
    logger.info('Copying S3 file s3://{}/{} into s3://{}/{}'.format(source_s3_location['bucket'],
        source_s3_location['key'], target_s3_location['bucket'], target_s3_location['key']))
    start_time = time.time()
    s3.meta.client.copy(
        copy_source, target_s3_location['bucket'], target_s3_location['key'])
    elapsed_time = time.time() - start_time
    logger.info('It took {} secs to copy S3 file s3://{}/{} into s3://{}/{}'.format(elapsed_time, source_s3_location['bucket'],
        source_s3_location['key'], target_s3_location['bucket'], target_s3_location['key']))

# Sample Lambda Input:
# {
#   "cur_payload": 0,
#   "work_size_in_mb": 1024,
#   "num_payloads": 1,
#   "payloads": [
#     {
#       "payload_size_in_mb": 1024,
#       "payload_files": [
#         {
#           "source_s3_bucket": "aws-s3-serverless-parallel-copy",
#           "source_s3_path": "source/1GB.mp4",
#           "target_s3_bucket": "aws-s3-serverless-parallel-copy",
#           "target_s3_path": "target/1GB.mp4",
#           "file_size_in_mb": 1024
#         }
#       ]
#     }
#   ]
# }
def handler(event, context):
    try:

        # grab input values
        work = event[0]
        payload = work['payloads'][work['cur_payload']]
        logger.info('S3 Copy Worker \'{}\' is processing payload: {}'.format(work['work_id'], payload))

        # Process the next work payload
        start_time = time.time()
        for file in payload['payload_files']:
            s3_copy(
                {'bucket': file['source_s3_bucket'], 'key': file['source_s3_path']},
                {'bucket': file['target_s3_bucket'], 'key': file['target_s3_path']}
            )
        elapsed_time = time.time() - start_time
        logger.info('It took {} secs to process the S3 copy payload: {}'.format(elapsed_time, payload))

        # Update values and generate Lambda output
        payload['copy_time_in_sec'] = elapsed_time
        work['cur_payload'] = work['cur_payload'] + 1
        result = {}
        result[work['work_id']] = work
        result['status'] = 'done' if work['cur_payload'] >= work['num_payloads'] else 'processing'
        return result

    except Exception as e:
        logger.error(str(e))
        raise e
