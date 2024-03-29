#!/usr/bin/env python3

from datetime import datetime
import random
import time
import json
import sys
if sys.version_info >= (3, 11): from datetime import UTC
else: import datetime as datetime_fix; UTC=datetime_fix.timezone.utc

def get_name():
    return "AWS Transcribe"

def get_id():
    return "aws-transcribe"

def get_settings():
    return {
        "limit_seconds": 14370, # Limit MP3 files to just shy of the AWS documented 4 hour limit
    }

def get_opts():
    return [
        ("aws_access_key_id", "AWS access key (leave blank to use profile/role)"),
        ("aws_secret_access_key", "Secret key associated with the access key (leave blank to use profile/role)"),
        ("profile_name", "AWS Profile Name (leave blank to use key/role/default profile)"),
        ("region_name", "AWS Region to use (leave blank to use key/role information)"),
        ("s3_bucket", "S3 Bucket to use to store artifacts (must exist)"),
        ("s3_prefix", "Prefix to store data in S3 Bucket (can be blank)"),
    ]

def run_engine(settings, source_fn):
    import boto3

    args = {}
    for key in ["aws_access_key_id", "aws_secret_access_key", "profile_name"]:
        if len(settings.get(key, "")) > 0:
            args[key] = settings[key]
    session = boto3.Session(**args)

    args = {}
    for key in ["region_name"]:
        if len(settings.get(key, "")) > 0:
            args[key] = settings[key]
    transcribe = session.client('transcribe', **args)
    s3 = session.client('s3', **args)

    now = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%d-%H%M%S")
    job_id = "transcribe_" + now + "-" + "".join(chr(ord('a') + random.randint(0, 25)) for _ in range(10))
    s3_key = settings['s3_prefix'] + job_id + ".mp3"

    print(f"Uploading {source_fn} to s3://{settings['s3_bucket']}/{s3_key}")
    s3.upload_file(source_fn, settings['s3_bucket'], s3_key)

    print("Starting transcription")
    transcribe.start_transcription_job(
        LanguageCode='en-US',
        MediaFormat='mp3',
        TranscriptionJobName=job_id,
        Media={'MediaFileUri': f"s3://{settings['s3_bucket']}/{s3_key}"},
        OutputBucketName=settings['s3_bucket'],
        OutputKey=s3_key + ".json",
    )

    while True:
        resp = transcribe.get_transcription_job(TranscriptionJobName=job_id)
        status = resp['TranscriptionJob']['TranscriptionJobStatus']
        if status == "COMPLETED":
            print("Transcription done!")
            break
        print(f"Working, job status is {status.lower().replace('_',' ')}...")
        time.sleep(15)

    print("Download transcription results")
    data = s3.get_object(Bucket=settings['s3_bucket'], Key=s3_key + ".json")['Body'].read()

    print("Cleaning up transcription job")
    transcribe.delete_transcription_job(TranscriptionJobName=job_id)

    print("Remove S3 objects")
    s3.delete_object(Bucket=settings['s3_bucket'], Key=s3_key)
    s3.delete_object(Bucket=settings['s3_bucket'], Key=s3_key + ".json")

    return data

def parse_data(data):
    ret = []
    
    data = json.loads(data)

    # For the case where only one item is transcribed, treat it
    # as a group of one item
    if isinstance(data, dict):
        data = [data]
    
    for cur in data:
        for item in cur['results']['items']:
            word = item['alternatives'][0]['content']
            if 'start_time' in item:
                ret.append([word, float(item['start_time']), float(item['end_time'])])
            else:
                ret[-1][0] += word

    return ret

if __name__ == "__main__":
    print("This module is not meant to be run directly")
