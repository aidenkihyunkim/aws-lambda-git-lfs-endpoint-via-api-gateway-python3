#!/usr/bin/python3
##############################################
# Git-LFS Endpoint for API-Gateway
# Author: Aiden Kim
# 2018-02-28
##############################################

import sys
if sys.version_info<(3,4,0):
    sys.stderr.write("You need python 3.4 or later to run this script\n")
    exit(1)

import os, os.path
import datetime
import boto3
import pytz
import json

from pprint import pprint
from datetime import datetime,timedelta
from base64 import b64decode

S3_TAG_NAME_AUTH_USERNAME = 'LFS_USERNAME'
S3_TAG_NAME_AUTH_PASSWORD = 'LFS_PASSWORD'
S3_STORAGE_CLASS = 'STANDARD'
S3_CONTENT_TYPE = 'application/octet-stream'
S3_PRESIGNED_EXPIRE_SECONDS = 3600

tz = pytz.timezone('Asia/Tokyo')
s3 = boto3.client('s3')


def print_out(msg):
    print('[' + tz.localize(datetime.now()).isoformat(' ') + '] ' + msg)


def response(status_code, body='', headers={}):  
    if isinstance(body, str):
        body = {'message':body}
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }


def get_s3_bucket_tags(bucket):
    res = s3.get_bucket_tagging(Bucket=bucket)
    if (res is not None) and ('TagSet' in res) and (len(res['TagSet'])>0):
        return res['TagSet']
    return None


def check_http_auth(event, bucket, repository=None):
    if (not 'headers' in event) or (not 'Authorization' in event['headers']) or (len(event['headers']['Authorization'])==0):
        print_out('"Authorization" header is empty!')
        return False
    authorization_str = b64decode(event['headers']['Authorization'].replace('Basic ','')).decode('ascii')
    
    s3_tag_set = get_s3_bucket_tags(bucket)
    if (s3_tag_set is None) or (len(s3_tag_set)<2):
        print_out('No tags on S3 bucket')
        return False
    if (repository):
        username = next((item['Value'] for item in s3_tag_set if item['Key'] == '{0}-{1}'.format(S3_TAG_NAME_AUTH_USERNAME,repository)), None)
        password = next((item['Value'] for item in s3_tag_set if item['Key'] == '{0}-{1}'.format(S3_TAG_NAME_AUTH_PASSWORD,repository)), None)
    else:
        username = next((item['Value'] for item in s3_tag_set if item['Key'] == S3_TAG_NAME_AUTH_USERNAME), None)
        password = next((item['Value'] for item in s3_tag_set if item['Key'] == S3_TAG_NAME_AUTH_PASSWORD), None)
        
    if (username is None) or (password is None):
        print_out('No auth data on S3 bucket')
        return False
    
    return ('{0}:{1}'.format(username, password) == authorization_str)


def get_s3_download(bucket, name, path=None):
    key = '{0}/{1}'.format(path,name) if path else name
    return s3.generate_presigned_url('get_object', Params={'Bucket':bucket,'Key':key}, ExpiresIn=S3_PRESIGNED_EXPIRE_SECONDS)

    
def get_s3_upload(bucket, name, path=None):
    key = '{0}/{1}'.format(path,name) if path else name
    return s3.generate_presigned_url('put_object', Params={'Bucket':bucket,'Key':key, 'ContentType':S3_CONTENT_TYPE}, ExpiresIn=S3_PRESIGNED_EXPIRE_SECONDS)


def handler_locks(event):
    return response(404, 'Not found')


def handler_objects(event, bucket, repository=None):
    
    # Check http auth
    ret = check_http_auth(event, bucket, repository)
    if (not ret):
        print_out('Authorization failure')
        return response(403, 'Forbidden')
    
    # Check http body
    if (not 'body' in event) or (len(event['body'])==0):
        print_out('Body parameter is empty!')
        return response(400, 'Bad request')
    body = json.loads(event['body'])
    if (not body) \
        or (not 'operation' in body) or (len(body['operation'])==0) \
        or (not 'objects' in body) or (len(body['objects'])==0):
        print_out('Body parameter is empty!')
        return response(400, 'Bad request')
        
    if (body['operation'] == 'upload'):
        
        res_body_obj = { 'transfer':'basic', 'objects':[] }
        for obj in body['objects']:
            url = get_s3_upload(bucket, obj['oid'], repository)
            if (url is None) or (len(url)==0):
                return response(500, 'Internal Error')
            obj['authenticated'] = True
            obj['actions'] = {'upload':{'href': url, 'expires_in': S3_PRESIGNED_EXPIRE_SECONDS}}
            res_body_obj['objects'].append(obj)
        return response(200, res_body_obj, {'Content-Type':'application/vnd.git-lfs+json; charset=utf-8'})
        
    elif (body['operation'] == 'download'):
        
        res_body_obj = { 'transfer':'basic', 'objects':[] }
        for obj in body['objects']:
            url = get_s3_download(bucket, obj['oid'], repository)
            if (url is None) or (len(url)==0):
                return response(500, 'Internal Error')
            obj['authenticated'] = True
            obj['actions'] = {'download':{'href': url, 'expires_in': S3_PRESIGNED_EXPIRE_SECONDS}}
            res_body_obj['objects'].append(obj)
        return response(200, res_body_obj, {'Content-Type':'application/vnd.git-lfs+json; charset=utf-8'})

    return response(400, 'Bad request')


# lambda handler        
def main(event, context):
    
    # Check parameter
    if (not 'resource' in event) or (len(event['resource'])==0) \
        or (not 'pathParameters' in event) \
        or (not 'proxy' in event['pathParameters']) or (len(event['pathParameters']['proxy'])==0) \
        or (not 'bucket' in event['pathParameters']) or (len(event['pathParameters']['bucket'])==0):
        print_out('pathParameters is empty!')
        return response(400, 'Bad request')
    proxy = event['pathParameters']['proxy']
    bucket = event['pathParameters']['bucket']
    repository = None

    # Check single or common bucket mode
    if (event['resource'].split('/',2)[1] == 'common'):
        if (not 'repository' in event['pathParameters']) or (len(event['pathParameters']['repository'])==0):
            print_out('Repository parameter is empty!')
            return response(400, 'Bad request')
        repository = event['pathParameters']['repository']

    # Run handler by methods
    if (proxy == 'locks/verify'):
        return handler_locks(event)
    elif (proxy == 'objects/batch'):
        return handler_objects(event, bucket, repository)
    return response(404, 'Not found')


if __name__ == '__main__':
    main(None,None)
