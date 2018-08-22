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

s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_s3_file_size(s3_location):
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
    src_file_size = get_s3_file_size(source_s3_location)
    file_copied = False
    # file exists in source
    if src_file_size >= 0:
        trg_file_size = get_s3_file_size(target_s3_location)
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
    src_file_size = get_s3_file_size(source_s3_location)
    trg_file_size = get_s3_file_size(target_s3_location)
    file_moved = False
    # file exists in source
    if src_file_size >= 0:
        # file not in target or files differ, trigger the copy
        if src_file_size != trg_file_size:
            s3_copy(source_s3_location, target_s3_location)
            file_moved = True
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