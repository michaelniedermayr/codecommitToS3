import boto3
import os
import mimetypes

# returns a list of the files in the branch or commit
def get_blob_list(codecommit, repository, afterCommitSpecifier, beforeCommitSpecifier=None):
    args = {'repositoryName': repository, 'afterCommitSpecifier': afterCommitSpecifier}

    if beforeCommitSpecifier:
        args['beforeCommitSpecifier'] = beforeCommitSpecifier

    response = codecommit.get_differences(**args)

    blob_list = [difference['afterBlob'] for difference in response['differences']]

    while 'NextToken' in response:
        args['NextToken'] = response['NextToken']
        response = codecommit.get_differences(**args)
        blob_list += [difference['afterBlob'] for difference in response['differences']]

    return blob_list


def upload_files_to_s3_bucket(bucket, codecommit, repository_name, blob_list):
    # reads each file in the branch and uploads it to the s3 bucket
    for blob in blob_list:
        path = blob['path']
        content = (codecommit.get_blob(repositoryName=repository_name, blobId=blob['blobId']))['content']

        # we have to guess the mime content-type of the files and provide it to S3 since S3 cannot do this on its own.
        content_type = mimetypes.guess_type(path)[0]
        if content_type is not None:
            bucket.put_object(Body=(content), Key=path, ContentType=content_type)
        else:
            bucket.put_object(Body=(content), Key=path)


# lambda-function
# triggered by changes in a codecommit repository
# reads files in the repository and uploads them to s3-bucket
#
# ENVIRONMENT VARIABLES:
#     s3BucketName
#     codecommitRegion
#     repository
#
# TIME OUT: 1 min
#
# EXECUTION ROLE
#     lambda-codecommit-s3-execution-role (permissions: AWSCodeCommitReadOnly, AWSLambdaExecute, AmazonSSMFullAccess)
#
def lambda_handler(event, context):

    # target bucket
    bucket = boto3.resource('s3').Bucket(os.environ['s3BucketName'])

    # source codecommit
    codecommit = boto3.client('codecommit', region_name=os.environ['codecommitRegion'])
    repository_name = os.environ['repository']

    # If the environmental variable 'branch' is defined, all files of that branch are uploaded to the S3 bucket
    # every time a new commit is pushed.
    # If 'branch' is NOT set, HEAD is used to define which files will be uploaded. It will be stored as an
    # SSM parameter afterwards. This way only modified or new files will be uploaded to the S3 bucket the next time.
    if 'branch' in os.environ:
        blob_list = get_blob_list(codecommit, repository_name, os.environ['branch'])
        upload_files_to_s3_bucket(bucket, codecommit, repository_name, blob_list)

    else:
        # Current HEAD SHA-1 id
        head = event['Records'][0]['codecommit']['references'][0]['commit']

        ssm_client = boto3.client('ssm')
        ssm_param_name = repository_name + '_beforeCommitSpecifier'

        # Check if beforeCommitSpecifier is already set. If not, blob_list retrieves a list of all files.
        try:
            # Previous HEAD SHA-1 id (i.e. the commit right before the HEAD when this function is called)
            last_head = ssm_client.get_parameter(Name=ssm_param_name)['Parameter']['Value']

        except ssm_client.exceptions.ParameterNotFound:
            last_head = None

        blob_list = get_blob_list(codecommit, repository_name, head, last_head)

        # upload files to s3 bucket
        upload_files_to_s3_bucket(bucket, codecommit, repository_name, blob_list)

        # store current head as new beforeCommitSpecifier in ssm
        ssm_client.put_parameter(Name=ssm_param_name, Type='String', Value=head,Overwrite=True)
