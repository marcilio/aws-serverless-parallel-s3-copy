#!/bin/bash

#======================================================================
# Package Lambda Function for AWS Serverless Repository
# - Make sure AWS_PROFILE env variable is set properly
#======================================================================

# ./package.sh dev

set -e

function error() {
    echo "Error: $1"
    echo "Example: ./package.sh qa"
    exit -1
}

[[ -n "$1" ]] || error "Missing environment name (eg, dev, uat, prod)"
env_type=$1

. "./scripts/${env_type}-env.sh"

if [ -z "$virtual_env_location" ]; then
    virtual_env_location=`pipenv --venv`
fi

pack_root_dir="/tmp/${app_name}"
pack_dist_dir="${pack_root_dir}/dist"

rm -rf "$pack_root_dir"
mkdir -p $pack_dist_dir
cp -R . $pack_dist_dir/
cp -R "${virtual_env_location}/lib/python3.6/site-packages/" "${pack_dist_dir}/lambdas"

# resolve jinja2 template into sam cfn template
( export cfn_template_dir="${pack_dist_dir}/cloudformation/" &&
  export input_jinja2_file="cfn_template.jinja2" &&
  export output_cfn_template="${pack_dist_dir}/cloudformation/${cfn_template}" &&
  python scripts/gen_cfn_template.py )

echo "Creating Lambda package under '${pack_dist_dir}' and uploading it to s3://${lambda_package_s3_bucket}"
(cd $pack_dist_dir \
 && aws cloudformation package \
    --template-file "cloudformation/${cfn_template}" \
    --s3-bucket $lambda_package_s3_bucket \
    --output-template-file $gen_cfn_template \
 && cat $gen_cfn_template)

