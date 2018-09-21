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
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.client('s3')
s3_valid_operations = ['move-files', 'copy-files']
default_s3_operation = 'move-files'

def get_file_size(s3_location):
    try:
        response = s3.head_object(Bucket=s3_location['bucket'], Key=s3_location['key'])
        if 'DeleteMarker' in response and response['DeleteMarker']:
            return -1
        return response['ContentLength']
    except:
        return -1

def s3_copy(source_s3_location, target_s3_location):
    copy_source = {
        'Bucket': source_s3_location['bucket'],
        'Key': source_s3_location['key']
    }
    logger.info('Copying S3 file s3://{}/{} into s3://{}/{}'.format(source_s3_location['bucket'],
        source_s3_location['key'], target_s3_location['bucket'], target_s3_location['key']))
    start_time = time.time()
    s3.copy(copy_source, target_s3_location['bucket'], target_s3_location['key'])
    elapsed_time = time.time() - start_time
    logger.info('It took {} secs to copy S3 file s3://{}/{} into s3://{}/{}'.format(elapsed_time, source_s3_location['bucket'],
        source_s3_location['key'], target_s3_location['bucket'], target_s3_location['key']))

# Copy if file not in destination
def s3_copy_if_not_in_destination(source_s3_location, target_s3_location):
    src_file_size = get_file_size(source_s3_location)
    file_copied = False
    # file exists in source
    if src_file_size >= 0:
        trg_file_size = get_file_size(target_s3_location)
        # files differ, trigger the copy
        if src_file_size != trg_file_size:
            s3_copy(source_s3_location, target_s3_location)
            file_copied = True
    else:
        raise Exception('File {}/{} does not exist and cannot be copied to {}/{}'.format(
            source_s3_location['bucket'], source_s3_location['key'], target_s3_location['bucket'], target_s3_location['key']))
    return file_copied

def s3_delete(s3_location):
    logger.info('Deleting S3 file s3://{}/{}'.format(s3_location['bucket'], s3_location['key']))
    start_time = time.time()
    s3.delete_object(Bucket=s3_location['bucket'], Key=s3_location['key'])
    elapsed_time = time.time() - start_time
    logger.info('It took {} secs to delete S3 file s3://{}/{}'.format(elapsed_time, s3_location['bucket'],
        s3_location['key']))

def s3_move_if_not_in_destination(source_s3_location, target_s3_location):
    src_file_size = get_file_size(source_s3_location)
    trg_file_size = get_file_size(target_s3_location)
    file_moved = False
    # file exists in source
    if src_file_size >= 0:
        # file not in target or files differ, trigger the copy
        if src_file_size != trg_file_size:
            s3_copy(source_s3_location, target_s3_location)
            s3_moved = True
        # delete from source in either case
        s3_delete(source_s3_location)
    # trying to move a file that neither exist in the source nor the target
    elif trg_file_size == -1:
        raise Exception('File {}/{} does not exist and cannot be moved to {}/{}'
            .format(
                source_s3_location['bucket'], source_s3_location['key'], 
                target_s3_location['bucket'], target_s3_location['key'])
            )
    return file_moved

def run_s3_operation(s3_operation_type, source_s3_location, target_s3_location):
    if s3_operation_type == 'move-files':
        return s3_move_if_not_in_destination(source_s3_location, target_s3_location)

    if s3_operation_type == 'copy-files':
        return s3_copy_if_not_in_destination(source_s3_location, target_s3_location)
    
    raise ValueError('Invalid S3 operation type: {}. Expecting one of \'move-files\' or \'copy-files\'.')


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
#           "source_s3_bucket": "aws-copy-source",
#           "source_s3_path": "source/1GB.mp4",
#           "target_s3_bucket": "aws-copy-destination",
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
        s3_operation_type = os.environ['S3OperationType'] if 'S3OperationType' in os.environ else default_s3_operation
        if not s3_operation_type in s3_valid_operations:
            raise ValueError('Invalid S3 operation type: {}. Expecting one of {}.'.format(s3_operation_type, s3_valid_operations))
        logger.info('S3 Worker \'{}\' is processing a \'{}\' operation on payload: {}'.format(work['work_id'], s3_operation_type, payload))

        # Process the next work payload
        start_time = time.time()
        for file in payload['payload_files']:
            run_s3_operation(
                s3_operation_type, 
                {'bucket': file['source_s3_bucket'], 'key': file['source_s3_path']},
                {'bucket': 'corus-media-vms', 'key': file['target_s3_path']}
            )
        elapsed_time = time.time() - start_time
        logger.info('It took {} secs to process a \'{}\' operation on S3 payload: {}'.format(elapsed_time, s3_operation_type, payload))

        # Update values and generate Lambda output
        payload['copy_time_in_sec'] = elapsed_time
        work['cur_payload'] = work['cur_payload'] + 1
        result = {}
        result[work['work_id']] = work
        result['status'] = 'done' if work['cur_payload'] >= work['num_payloads'] else 'processing'
        return result

    except Exception as e:
        logger.error(str(e))
        raise
