# src/ocr_engine.py

import boto3
import time
import logging

logger = logging.getLogger(__name__)
client = boto3.client("textract")

def start_text_detection(bucket, document):
    logger.info(f"Starting Textract job on {document}")
    response = client.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": document}}
    )
    return response["JobId"]

def wait_for_job(job_id):
    while True:
        response = client.get_document_text_detection(JobId=job_id)
        status = response["JobStatus"]
        logger.info(f"Textract job status: {status}")
        if status in ["SUCCEEDED", "FAILED"]:
            return status == "SUCCEEDED"
        time.sleep(5)

def get_job_results(job_id):
    pages = []
    response = client.get_document_text_detection(JobId=job_id)
    pages.append(response)

    while "NextToken" in response:
        token = response["NextToken"]
        response = client.get_document_text_detection(JobId=job_id, NextToken=token)
        pages.append(response)

    return pages

def run_s3_ocr(bucket, key):
    job_id = start_text_detection(bucket, key)
    logger.info(f"Started Textract job with ID: {job_id}")

    if wait_for_job(job_id):
        results = get_job_results(job_id)
        for page in results:
            for block in page["Blocks"]:
                if block["BlockType"] == "LINE":
                    print(block["Text"])
    else:
        logger.error("Textract job failed.")
