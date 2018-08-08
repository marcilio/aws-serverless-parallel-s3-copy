#!/bin/bash

# Environment name (eg, dev, qa, prod)
export env_type="dev"

# Python virtual environment location for packaging
export virtual_env_location=`pipenv --venv`

export num_copy_lambda_workers=3
export max_payload_size_per_lambda_execution_in_mb=1024

# S3 bucket where file will be copied from
export source_s3_bucket="aws-s3-serverless-parallel-copy"

# S3 bucket where file will be copied to
export target_s3_bucket="aws-s3-serverless-parallel-copy"

# S3 bucket to store packaged Lambdas
export lambda_package_s3_bucket="aws-s3-serverless-parallel-copy"

#### Common to All Environments ####

export app_name="s3servcopy"
export cfn_template="cfn_template.yaml"
export gen_cfn_template="generated-${cfn_template}"
