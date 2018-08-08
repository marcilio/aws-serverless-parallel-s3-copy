# ------------------------------------------------------------------------------
# This Lambda function inspects the s3_file files within an S3 bucket/path and 
# groups them into evenly-sized payloads that can be copied in parallel by 
# multiple Lambda functions. The grouping allows Lambda functions to work on a
# reasonably-sized payload that can be processed within Lambda's max execution time
# of 5 min.
#
# For details on the MPP, please check the link below:
# ->  https://corusent.atlassian.net/wiki/spaces/CVMS/pages/533823515/VMS+Tech+Documents+and+Diagrams
# ------------------------------------------------------------------------------

import boto3
import logging
import json
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.client('s3')
A_MB = 1024 * 1024
A_GB = 1024 * A_MB

class S3FileInfo:

    def __init__(self, source_s3_bucket, source_s3_path, target_s3_bucket, target_s3_path, file_size):
        self.source_s3_bucket = source_s3_bucket
        self.source_s3_path = source_s3_path
        self.target_s3_bucket = target_s3_bucket
        self.target_s3_path = target_s3_path
        self.file_size = file_size

    def __repr__(self):
        return f'S3FileInfo({self.source_s3_bucket!r}, {self.source_s3_path!r}, {self.target_s3_bucket!r}, {self.target_s3_path!r}, {self.file_size!r})'


class S3FilePayload:

    def __init__(self, max_paylod_size_in_mb):
        self.s3_file_list = []
        self.max_paylod_size_in_mb = max_paylod_size_in_mb
        self.cur_payload_size = 0

    def has_capacity(self, s3_file_size):
        return self.cur_payload_size == 0 or self.cur_payload_size + s3_file_size <= self.max_paylod_size_in_mb

    def add_file(self, s3_file_info):
        self.s3_file_list.append(s3_file_info)
        self.cur_payload_size += s3_file_info.file_size

    def __repr__(self):
        return f'S3FilePayload({self.s3_file_list!r})'


class S3CopyWork:

    def __init__(self, name, max_paylod_size_per_work_in_mb):
        self.name = name
        self.cur_payload = S3FilePayload(max_paylod_size_per_work_in_mb)
        self.max_paylod_size_per_work_in_mb = max_paylod_size_per_work_in_mb
        self.work_list = [self.cur_payload]
        self.cur_work_size = 0

    def _new_payload(self):
        self.cur_payload = S3FilePayload(self.max_paylod_size_per_work_in_mb)
        self.work_list.append(self.cur_payload)
        return self

    def add_payload(self, s3_file_info):
        if (not self.cur_payload.has_capacity(s3_file_info.file_size)):
            self._new_payload()
        self.cur_payload.add_file(s3_file_info)
        self.cur_work_size += s3_file_info.file_size
        return self

    def __repr__(self):
        return f'S3CopyWork({self.name!r}, {self.work_list!r})'


class S3CopyOrchestrator:

    def _tune_min_heap(self, works_min_heap):
        heap_size = len(works_min_heap)
        idx = 0
        while True:
            chd1_idx = 2*idx + 1
            chd2_idx = 2*idx + 2
            # search for a child node in the min heap
            if (chd1_idx < heap_size):
                min_chd_idx = chd1_idx
                # find out the min child node
                if (chd2_idx < heap_size and works_min_heap[chd2_idx].cur_payload_size < works_min_heap[chd1_idx].cur_payload_size):
                    min_chd_idx = chd2_idx
                # check if child node needs to be swapped with parent
                if (works_min_heap[min_chd_idx].cur_work_size < works_min_heap[idx].cur_work_size):
                    tmp = works_min_heap[min_chd_idx]
                    works_min_heap[min_chd_idx] = works_min_heap[idx]
                    works_min_heap[idx] = tmp
                    idx = min_chd_idx
                else:
                    break  # no swaps required, min heap is tuned
            else:
                break  # node has no children, min heap is tuned

    def split_work(self, s3_files_list, num_available_works, max_paylod_size_per_work_in_mb):
        assert s3_files_list != None and num_available_works > 0 and max_paylod_size_per_work_in_mb > 0
        works_min_heap = [S3CopyWork('s3-copy-work-{}'.format(index), max_paylod_size_per_work_in_mb)
                            for index in range(1, num_available_works+1)]
        if len(s3_files_list) > 0:
            # distributes payload evenly (greedy) across available works
            sorted_file_list = sorted(
                s3_files_list, key=lambda e: e.file_size, reverse=True)
            for s3_file in sorted_file_list:
                works_min_heap[0].add_payload(s3_file)
                self._tune_min_heap(works_min_heap)
        return works_min_heap

class S3CopyFileTypeInfo:

    def __init__(self, s3_copy_config):
        self.file_types = {}
        for file_type_config in s3_copy_config['target_s3_config']:
            dest_s3_bucket = file_type_config['s3_bucket']
            dest_s3_path = file_type_config['s3_path']
            for file_type in file_type_config['file_types']:
                self.file_types['{}_s3_bucket'.format(file_type)] = dest_s3_bucket
                self.file_types['{}_s3_path'.format(file_type)] = dest_s3_path

    def get_s3_bucket_for_file_type(self, file_format):
        if not self.has_info_for_file_type(file_format):
            raise ValueError('Could not find S3 bucket name for file type: \'{}\''.format(file_format))
        key = '{}_s3_bucket'.format(file_format)
        return self.file_types[key]

    def get_s3_path_for_file_type(self, file_format):
        if not self.has_info_for_file_type(file_format):
            raise ValueError('Could not find S3 file path for file type: \'{}\''.format(file_format))
        key = '{}_s3_path'.format(file_format)
        return self.file_types[key]

    def has_info_for_file_type(self, file_format):
        key = '{}_s3_path'.format(file_format)
        return key in self.file_types

    def __repr__(self):
        return f'S3CopyFileTypeInfo({self.file_types!r})'

def s3_work_to_json(s3_work_list):
    work_set_dict = {}
    for work_idx, work in enumerate(s3_work_list):
        work_dict = {
            'cur_payload': 0,
            'work_size_in_mb': work.cur_work_size
        }
        work_payloads = []
        for payload in work.work_list:
            payload_files = []
            for file in payload.s3_file_list:
                payload_files.append({
                    'source_s3_bucket': file.source_s3_bucket,
                    'source_s3_path': file.source_s3_path,
                    'target_s3_bucket': file.target_s3_bucket,
                    'target_s3_path': file.target_s3_path,
                    'file_size_in_mb': file.file_size
                })
            payload_dict = {
                'payload_size_in_mb': payload.cur_payload_size,
                'payload_files': payload_files
            }
            work_payloads.append(payload_dict)
        work_dict['num_payloads'] = len(work_payloads)
        work_dict['payloads'] = work_payloads
        work_set_dict['s3-work-'+str(work_idx+1)] = work_dict
    return work_set_dict

# Sample Lambda Input
# { 
#     "s3_copy_config": {
#         "source_s3_config": {
#             "s3_bucket": "aws-s3-serverless-parallel-copy",
#             "s3_path": "source/"
#         },
#         "target_s3_config": [
#             {
#                 "file_types" : ["mp4", "jpg"],
#                 "s3_bucket": "aws-s3-serverless-parallel-copy",
#                 "s3_path": "target/"
#             }
#         ]
#     }
# }
def handler(event, context):
    try:
        # logger.info('{} Lambda triggered by event: {}'.format(context.function_name, event))
        s3_copy_config = event['s3_copy_config']

        s3_destination_info = S3CopyFileTypeInfo(s3_copy_config)

        src_s3_bucket_name = s3_copy_config['source_s3_config']['s3_bucket']
        src_s3_path = s3_copy_config['source_s3_config']['s3_path']
        logger.info('Inspecting s3_file files uploaded to s3://{}/{}...'.format(src_s3_bucket_name, src_s3_path))
        full_list_of_files = []
        # Search all file objects in the S3 bucket for the given payload (prefixed by src_s3_path)
        for s3_object in s3.list_objects(Bucket=src_s3_bucket_name, Prefix=src_s3_path)['Contents']:
            # Skip path objects
            if not s3_object['Key'].endswith('/'):
                s3_file_name = s3_object['Key'].replace(src_s3_path, '', 1)
                src_s3_filename = s3_object['Key']
                src_s3_file_size_in_mb = s3_object['Size']/A_MB
                # If the S3 file object has an extension (eg, mp4, jpg)
                if '.' in src_s3_filename:
                    file_extension = src_s3_filename.rsplit('.', 1)[-1]
                    # If the extension appears in the MRSS file, grab the S3 bucket destination info for it
                    if s3_destination_info.has_info_for_file_type(file_extension):
                        dest_s3_bucket_name = s3_destination_info.get_s3_bucket_for_file_type(file_extension)
                        dest_s3_filename = '{}{}'.format(s3_destination_info.get_s3_path_for_file_type(file_extension), s3_file_name)
                        s3_file = S3FileInfo(src_s3_bucket_name, src_s3_filename, dest_s3_bucket_name, dest_s3_filename, src_s3_file_size_in_mb)
                        full_list_of_files.append(s3_file)
                    # If the extension is not mentioned in MRSS file (and is not the .mrss file itself) log a 'warning'
                    elif file_extension != 'mrss':
                        logger.warning('S3 file: \'{}\' from S3 bucket: \'{}\'is not referenced by the S3 input configuration and is being ignored'.format(src_s3_filename, src_s3_bucket_name))
        # This is the S3 file move orchestrator that will split the move work evently among available workers (Lambda functions)
        num_lambda_workers = os.environ['NumCopyLambdaWorkers'] if 'NumCopyLambdaWorkers' in os.environ != None else 2 # default: 2 workers
        max_payload_size_per_lambda_execution = os.environ['MaxPayloadSizePerLambdaExecutionInMB'] if 'MaxPayloadSizePerLambdaExecutionInMB' in os.environ != None else 1024 # default: 1GB
        s3_file_move_orchestrator = S3CopyOrchestrator()
        s3_work_list = s3_file_move_orchestrator.split_work(full_list_of_files, num_lambda_workers, max_payload_size_per_lambda_execution)
        return s3_work_to_json(s3_work_list)
    except Exception as e:
        logger.error(str(e))
        raise e

if __name__ == '__main__':
    h = handler(
        {
            "s3_copy_config": {
                "source_s3_config": {
                    "s3_bucket": "aws-s3-serverless-parallel-copy",
                    "s3_path": "source/"
                },
                "target_s3_config": [
                    {
                        "file_types" : ["zip", "jpg"],
                        "s3_bucket": "aws-s3-serverless-parallel-copy",
                        "s3_path": "target/"
                    }
                ]
            }
        },
        {
            'function_name', 's3copy_orchestrator'
        }
    )
    print(h)