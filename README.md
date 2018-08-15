# Intro

This project illustrates how to build a (Serverless solution)[https://aws.amazon.com/serverless/] to copy a large number of files from an S3 location to another. The project leverages (AWS Step Function)[https://aws.amazon.com/step-functions/] state machines to parallelize work while serializing the copy of large payloads per Lambda execution to address Lambda's running time contraints. 

The solution is ideal in a scenario where a very large amount of relatively large files (up to 10-15GB if within same AWS region) from one S3 location to another. The solution was not designed to copy very large individual files (eg, 100GB) though.

# Architecture

The Serverless S3 copy architecture is depicted below. It shows how an initial set of binary S3 files is broken down into payloads of 10GB max size. The 10GB value is configurable. By definition, a 'payload' is a piece of work that can be processed within a single Lambda function execution (ie, typically <= 5min). 'Work' is a group of payloads. A 'Work' assigned to a Lambda function is processed in sequence, one payload at a time. Multiple Lambdas (workers) can process their 'Work' in parallel. This way, one can control the concurrency level by adding/removing workers to/from the mix as well as configuring the maximum payload that can be handled by a Lambda worker. The beauty of AWS Step Functions come into play by making it super simple to coordinate the parallel ('Work' processing) and sequential ('Payload' processing) execution of the Worker Lambdas. Without Step Functions one would have to code that coordination logic. 

![Alt text](docs/serverless-parallel-s3-copy.png?raw=true "Serverless Parallel S3 Copy")

As mentioned before, the number of Lambda workers is configurable as well as the payload size that each worker Lambda can handle per execution. For example, same-region copies (eg, us-east-1 to us-east-1) payloads of up to ~15GB were successfully handled per Lambda execution (us-east-1). For cross-region copies the payload must be lowered, sometimes significantly (eg, 1GB or less) depending on the source and target regions. 


# Deploying the Solution

Before you deploy the solution make sure you have the requirements.

## Requirements

* (Python 3.6)[https://www.python.org/downloads/]
* (Latest AWS CLI)[https://aws.amazon.com/cli/] if you plan to invoke the state machine via the CLI
* (Pipenv)[https://github.com/pypa/pipenv] not required by probably a good idea (otherwise just use 'pip' and requirements.txt)
* An AWS account where you have permissions to create/configure S3 buckets
* S3 buckets (source and targets) for the copy


## Steps

Edit the provided ```dev-env.sh``` configuration script and update the values for the following variables to reflect your own environment. If you have multiple accounts, just copy/paste this file and rename it, eg, dev-env.sh, uat-env.sh, prod-env.sh.

```bash
# your python virtual environment location
export virtual_env_location=`pipenv --venv`

# Number of Lambda copy workers you want to use to parallelize the S3 copy work. You *must* edit the cloudformation template cfn_template.yaml to manually add or remove workers to/from the Step Functions. I know, this is sad and one can use Troposphere to automate that. Give me time and I'll do it ;)
export num_copy_lambda_workers=2

# Maximum payload size in MB that can be handled by a single Lambda worker execution (think in terms of how much can be copied by Lambda given your use case, eg, same-region, cross-region). For reference: Same-region => ~10-15GB, Cross-region: 1GB?
export max_payload_size_per_lambda_execution_in_mb=800

# S3 bucket where file will be copied from (this is to give Lambdas permission access to the bucket)
export source_s3_bucket="aws-s3-serverless-parallel-copy"

# S3 bucket where file will be copied to (this is to give Lambdas permission access to the bucket - if you plan to use more target buckets, you'll have to add access manually)
export target_s3_bucket="aws-s3-serverless-parallel-copy"

# S3 bucket to store packaged Lambdas
export lambda_package_s3_bucket="aws-s3-serverless-parallel-copy"
```

Package the solution for deployment:

```bash
cd [project-root]
export AWS_PROFILE=[your AWS profile or 'Default']
./scripts/package.sh dev . # this will load the values defined in your dev-env.sh and package the solution artifact in S3
```

Deploy the solution

```bash
./scripts/deploy.sh dev . # this will load the values defined in your dev-env.sh and deploy the solution
```

Take a look in your AWS account and notice the resources created: AWS Step Functions state machine, AWS Lambda functions, IAM roles, etc. 

## Running

Now, it's time to trigger the state machine to copy some files around.

Your state machine is named ```dev-s3servcopy-state-machine``` (for dev environment). Open the AWS Step Functions console, and click ```Start Execution```.

Enter the State Machine input, for example:

```json

  "s3_copy_config": {
    "source_s3_config": {
      "s3_bucket": "my-source-s3-bucket",
      "s3_path": "source/"
    },
    "target_s3_config": [
      {
        "file_types": [
          "mp4"
        ],
        "s3_bucket": "my-target-s3-bucket",
        "s3_path": "mp4/"
      },
      {
        "file_types": [
          "jpg",
          "png",
        ],
        "s3_bucket": "my-target-s3-bucket",
        "s3_path": "images/"
      }      
    ]
  }
}
```

This will copy ```mp4``` files from ```my-source-s3-bucket/source``` into ```my-target-s3-bucket/mp4``` and ```jpg``` and ```png``` files into ```my-target-s3-bucket/images/``` location.

## Limitations

* Solution accepts a single S3 bucket and path as source
* Soluton only supports 'file type' filtering for now. That is, the Lambdas will look for file types and copy them to designated locations.

Cool, eh? Feel free to contribute!
