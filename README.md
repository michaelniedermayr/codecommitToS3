# codecommitToS3

###Update
If the environmental variable 'branch' is defined, all files of that branch are uploaded to the S3 bucket
every time a new commit is pushed.

If 'branch' is **NOT** set, HEAD is used to define which files will be uploaded. It will be stored as an 
[SSM parameter](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html) 
afterwards. This way only modified or new files will be uploaded to the S3 bucket the next time. 

**IMPORTANT**: The Lambda function requires the execution role 'AmazonSSMFullAccess' to access SSM parameters.

Thx to [handk85](https://github.com/handk85) for this improvement.

###Tutorial
Code hosted on AWS CodeCommit Git-repo is deployed to AWS S3-bucket by an AWS Lambda function.

Find more information here: https://medium.com/@michael.niedermayr/using-aws-codecommit-and-lambda-for-automatic-code-deployment-to-s3-bucket-b35aa83d029b
