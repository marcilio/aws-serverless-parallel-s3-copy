
from utils.s3_utils import get_s3_file_size, s3_copy_if_not_in_destination, s3_move_if_not_in_destination
import pytest
import boto3
import uuid

# TODO: read this from a test config file
s3_src_bucket = 's3-serverless-parallel-copy-source'
s3_trg_bucket = 's3-serverless-parallel-copy-target'
file_content = b'1234567890'
invalid_file = 'invalid-file.txt'

@pytest.fixture(scope="session")
def s3_client():
    return boto3.client('s3')

@pytest.fixture(scope="session")
def src_s3_key():
    return '{}/{}.txt'.format(str(uuid.uuid4()), str(uuid.uuid4()))

@pytest.fixture(scope="session")
def trg_s3_key():
    return '{}/{}.txt'.format(str(uuid.uuid4()), str(uuid.uuid4()))

def test_file_size_is_correct(s3_client, src_s3_key):

    # setup
    s3_client.put_object(Bucket=s3_src_bucket, Key=src_s3_key, ContentType='text/plain', Body=file_content)

    # test
    size = get_s3_file_size({'bucket': s3_src_bucket, 'key': src_s3_key})
    assert size == len(file_content)

    # teardown
    s3_client.delete_object(Bucket=s3_src_bucket, Key=src_s3_key)
    
def test_file_size_file_does_not_exist(src_s3_key):

    # test
    size = get_s3_file_size({'bucket': src_s3_key, 'key': invalid_file})
    assert size == -1

def test_s3_copy_if_not_in_destination_file_successfully_copied(s3_client, src_s3_key, trg_s3_key):

    # setup
    s3_client.put_object(Bucket=s3_src_bucket, Key=src_s3_key, ContentType='text/plain', Body=file_content)

    # test
    copied_file = s3_copy_if_not_in_destination(
        {'bucket': s3_src_bucket, 'key': src_s3_key},
        {'bucket': s3_trg_bucket, 'key': trg_s3_key}
    )
    assert copied_file == True

    # tear down
    s3_client.delete_object(Bucket=s3_src_bucket, Key=src_s3_key)


def test_s3_copy_if_not_in_destination_file_already_in_destination(s3_client, src_s3_key, trg_s3_key):

    # setup
    s3_client.put_object(Bucket=s3_src_bucket, Key=src_s3_key, ContentType='text/plain', Body=file_content)
    s3_client.put_object(Bucket=s3_trg_bucket, Key=trg_s3_key, ContentType='text/plain', Body=file_content)

    # test
    copied_file = s3_copy_if_not_in_destination(
        {'bucket': s3_src_bucket, 'key': src_s3_key},
        {'bucket': s3_trg_bucket, 'key': trg_s3_key}
    )
    assert copied_file == False

    # tear down
    s3_client.delete_object(Bucket=s3_src_bucket, Key=src_s3_key)
    s3_client.delete_object(Bucket=s3_trg_bucket, Key=trg_s3_key)

def test_s3_move_if_not_in_destination_file_successfully_moved(s3_client, src_s3_key, trg_s3_key):

    # setup
    s3_client.put_object(Bucket=s3_src_bucket, Key=src_s3_key, ContentType='text/plain', Body=file_content)

    moved_file = s3_move_if_not_in_destination(
        {'bucket': s3_src_bucket, 'key': src_s3_key},
        {'bucket': s3_trg_bucket, 'key': trg_s3_key}
    )
    assert moved_file == True

    # tear down
    s3_client.delete_object(Bucket=s3_src_bucket, Key=src_s3_key)

def test_s3_move_if_not_in_destination_file_already_in_source_and_destination_must_be_deleted_from_source(s3_client, src_s3_key, trg_s3_key):

    # setup
    s3_client.put_object(Bucket=s3_src_bucket, Key=src_s3_key, ContentType='text/plain', Body=file_content)
    s3_client.put_object(Bucket=s3_trg_bucket, Key=trg_s3_key, ContentType='text/plain', Body=file_content)

    moved_file = s3_move_if_not_in_destination(
        {'bucket': s3_src_bucket, 'key': src_s3_key},
        {'bucket': s3_trg_bucket, 'key': trg_s3_key}
    )
    assert moved_file == False
    assert  get_s3_file_size({'bucket': s3_src_bucket, 'key': src_s3_key}) == -1

    # tear down
    s3_client.delete_object(Bucket=s3_src_bucket, Key=src_s3_key)
    s3_client.delete_object(Bucket=s3_trg_bucket, Key=trg_s3_key)

def test_s3_move_if_not_in_destination_file_already_in_destination_but_not_in_source_must_be_deleted_from_source(s3_client, src_s3_key, trg_s3_key):

    # setup
    s3_client.put_object(Bucket=s3_trg_bucket, Key=trg_s3_key, ContentType='text/plain', Body=file_content)

    moved_file = s3_move_if_not_in_destination(
        {'bucket': s3_src_bucket, 'key': src_s3_key},
        {'bucket': s3_trg_bucket, 'key': trg_s3_key}
    )
    assert moved_file == False
    assert  get_s3_file_size({'bucket': s3_src_bucket, 'key': src_s3_key}) == -1

    # tear down
    s3_client.delete_object(Bucket=s3_trg_bucket, Key=trg_s3_key)

def test_s3_move_if_not_in_destination_file_does_not_exist_raises_exception(src_s3_key, trg_s3_key):

    with pytest.raises(Exception):
        s3_move_if_not_in_destination(
            {'bucket': s3_src_bucket, 'key': invalid_file},
            {'bucket': s3_trg_bucket, 'key': invalid_file}
        )

