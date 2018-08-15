#!/bin/bash

# Environment name (eg, dev, qa, prod)
export env_type="dev"

# Python virtual environment location for packaging
if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

# Number of Lambda copy workers you want to use to parallelize the S3 
# copy work. You *must* edit the cloudformation template cfn_template.yaml 
# to manually add or remove workers to/from the Step Functions. 
# I know, this is sad. Troposphere to the rescue? 
export num_copy_lambda_workers=2

# Maximum payload size in MB that can be handled by a single Lambda worker 
# execution (think in terms of how much can be copied by Lambda given your 
# use case, eg, same-region, cross-region). 
# For reference: Same-region => ~10-15GB, Cross-region: 1GB?
export max_payload_size_per_lambda_execution_in_mb=1024

# S3 bucket where file will be copied from
export source_s3_bucket="serverless-s3-parallel-copy-source"

# S3 bucket where file will be copied to
export target_s3_bucket="serverless-s3-parallel-copy-target"

# S3 bucket to store packaged Lambdas
export lambda_package_s3_bucket="aws-s3-serverless-parallel-copy"

# You probably don't need to change these values
export app_name="s3servcopy"
export cfn_template="cfn_template.yaml"
export gen_cfn_template="generated-${cfn_template}"
