# Intro

This project illustrates how to build a Serverless solution to copy a large number of files from an S3 location to another. The project leverages AWS Step Function state machines to parallelize work (multiple workers = state machine tasks) while serializing the copy of large payloads per Lambda execution to avoid reaching the Lambda timeout limit of 5 min execution while copying data. 

The solution is ideal to copy a very large amount of relatively large files (up to 10-15GB if within same AWS region) from one S3 location to another. It is not ideal to copy very large individual files (eg, > 20GB) though.

# Requirements

# Deploy the Solution
