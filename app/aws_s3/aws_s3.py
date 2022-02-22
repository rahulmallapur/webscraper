import logging
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(format='%(asctime)s %(levelname)s %(process)d --- %(name)s %(funcName)20s() : %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

def upload_object(object: bytes, bucket: str, key: str, content_type: str, grant_read: str = None, metadata={}) -> bool:
    if grant_read is None:
        grant_read = 'uri="http://acs.amazonaws.com/groups/global/AllUsers"'
    s3_client = boto3.client('s3')
    try:
        s3_client.put_object(Body=object, Bucket=bucket, GrantRead=grant_read, ContentType=content_type, Key=key, Metadata=metadata)
        logging.info(f"Successfully uploaded object to '{bucket}' as '{key}'.")
    except ClientError as e:
        logging.error(e)
        return False
    return True
