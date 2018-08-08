#!/bin/bash

#======================================================================
# Deploys Media Processing Pipeline (Step Functions state machines )
# and related Lambda functions
#======================================================================

# Sample invoke:
# ./deploy.sh uat

set -e

function error() {
    echo "Error: $1"
    exit -1
}
[[ -n "$1" ]] || error "Missing environment name (eg, dev, qa, prod)"
env_type=$1

. "./scripts/${env_type}-env.sh"

stack_name="${env_type}-${app_name}-state-machine"
pack_root_dir="/tmp/${app_name}"
pack_dist_dir="${pack_root_dir}/dist"

(cd $pack_dist_dir \
&& aws cloudformation deploy \
    --template-file $gen_cfn_template \
    --stack-name $stack_name \
    --parameter-overrides \
        ProjectName="$app_name" \
        EnvType="$env_type" \
        SourceS3Bucket="$source_s3_bucket" \
        TargetS3Bucket="$target_s3_bucket" \
        NumCopyLambdaWorkers="$num_copy_lambda_workers" \
        MaxPayloadSizePerLambdaExecutionInMB="$max_payload_size_per_lambda_execution_in_mb" \
    --capabilities \
        CAPABILITY_IAM
)
