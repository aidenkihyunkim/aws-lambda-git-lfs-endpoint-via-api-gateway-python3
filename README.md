# AWS Lambda function for Git-LFS endpoint via API Gateway

The lambda function implements for **Git-LFS Endpoint**.
This function uses AWS API Gateway as a front end and use S3 bucket as a storage.

See the [Git LFS API](https://github.com/git-lfs/git-lfs/blob/master/docs/api/README.md) and [Git LFS Batch API](https://github.com/git-lfs/git-lfs/blob/master/docs/api/batch.md) doc for get the specification.

## Features
- Serverless, Works only on the AWS layer without any OS / runtime manipulation.
- Use affordable S3 as a file storage.
- Supports multiple Git repositories with a single Lambda function.
- Multiple Git repositories can be run in a S3 bucket. ([Common bucket mode](#S3-bucket-modes))
- Use HTTP Basic Authentication when connecting to LFS Endpoint.
- A new Git repository can use LFS simply by adding S3 tags without modifying the source or AWS configuration.

## How to use this?

1. Please deploy this **Lambda** function and specify threshold.
2. [Prepare a **S3 bucket** for LFS storage then adds tags for **authentication**.](#Create-S3-Bucket)
3. [Create API on the **API Gateway** and integrate with the Lambda function.](#Setup-API-Gateway)
4. [Apply a **Git-LFS config** to your git project then use Git-LFS.](#Git-LFS-config)

## Create S3 Bucket

This function(API) use [HTTP basic authentication](https://en.wikipedia.org/wiki/Basic_access_authentication) for authentication.
The authentication information is stored in the tag of the S3 bucket.
Please create a bucket and add below tags. ([Single bucket mode](#S3-bucket-modes))
- **LFS_USERNAME** : Tag for user name
- **LFS_PASSWORD** : Tag for password

## Setup API Gateway

- Add Resources as below. ([Single bucket mode](#S3-bucket-modes))
    ```
    /single/{bucket}/{proxy+}
    ```
- `{proxy+}` is the [Proxy Resource for Proxy Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-set-up-simple-proxy.html). Assign this Lambda function to `ANY` method of `{proxy+}`.
- Add a stage named `lfs`.
    - Disable API cache of the stage.

## Git-LFS config

- Add a `.lfsconfig` file to your git project directory. ([Single bucket mode](#S3-bucket-modes))
    ```ini
    [lfs]
    url = https://<USERNAME>:<PASSWORD>@00000000.execute-api.region.amazonaws.com/lfs/single/<S3_BUCKET_NAME>
    ```
    - **&lt;USERNAME&gt;** : Authentication user name what written on LFS_USERNAME tag of S3 bucket.
    - **&lt;PASSWORD&gt;** : Authentication password what written on LFS_PASSWORD tag of S3 bucket.
    - **00000000.execute-api.region.amazonaws.com/lfs** : URL of API Gateway stage.
    - **<S3_BUCKET_NAME>** : The S3 bucket name.

## Execution IAM policy
This Lambda function require a IAM policy like below.
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketTagging",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::<S3_BUCKET_NAME>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::<S3_BUCKET_NAME>/*"
      ]
    }
  ]
}
```

## S3 Bucket Modes

This function can be used in two modes depending on the type of S3 bucket being used.
- **Single bucket mode**
    - Use separate buckets for each repository.
    - The above descriptions are for Single bucket mode.
- **Common bucket mode**
    - Use same bucket for multiple repositories.
    - Data will separate by directories of repository name
    - S3 Bucket tags
        - `LFS_USERNAME-<REPOSITORY_NAME>` : Tag for user name, Replace `<REPOSITORY_NAME>` with yours repository name.
        - `LFS_PASSWORD-<REPOSITORY_NAME>` : Tag for password, Replace `<REPOSITORY_NAME>` with yours repository name.
        - Add above tags as many as the number of repositories to use.
    - API Gateway
        - Add Resources as below.
            ```
            /common/{bucket}/{repository}/{proxy+}
            ```
        - Add a stage named `lfs`.
    - Git-LFS config
        - Add a `.lfsconfig` file to your git project directory.
            ```ini
            [lfs]
            url = https://<USERNAME>:<PASSWORD>@00000000.execute-api.region.amazonaws.com/lfs/common/<S3_BUCKET_NAME>/<REPOSITORY_NAME>
            ```
            - **<REPOSITORY_NAME>** : Yours repository name.

## Example of API Gateway configuration

Resources | Stages
----------|--------
![Resources](/README/API-Gateway-Resources.png) | ![Stages](/README/API-Gateway-Stages.png)


## License

MIT License (MIT)
