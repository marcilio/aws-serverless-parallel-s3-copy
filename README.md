# Intro

This project illustrates how to build a (Serverless solution)[https://aws.amazon.com/serverless/] to copy a large number of files from an S3 location to another. The project leverages (AWS Step Function)[https://aws.amazon.com/step-functions/] state machines to parallelize work while serializing the copy of large payloads per Lambda execution to address Lambda's running time contraints. 

The solution is ideal in a scenario where a very large amount of relatively large files (up to 10-15GB if within same AWS region) from one S3 location to another. It is not ideal to copy very large individual files (eg, > 20GB) though.

# Architecture

The Serverless S3 copy architecture is depicted below.

![Alt text](docs/serverless-parallel-s3-copy.png?raw=true "Serverless Parallel S3 Copy")

The number of workers is configurable as well as the payload size that each worker Lambda can handle per execution. For example, same-region copies (eg, us-east-1 to us-east-1) payloads of up to ~15GB were successfully handled per Lambda execution (us-east-1). For cross-region copies the payload must be lowered, sometimes significantly (eg, 1GB or less) depending on the source and target regions. 

Please, make sure the Lambda functions have proper access to the S3 buckets, especially in cross-region cases.


# Deploying the Solution

## Requirements

## Steps
