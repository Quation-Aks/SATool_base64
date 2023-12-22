# -*- coding: utf-8 -*-
"""
Created on Mon Nov 20 15:33:21 2023

@author: Quation
"""

import os
import boto3
from flask import Flask, jsonify, request, send_file
import botocore
import csv
import base64
import io
import zipfile
#from decouple import config

app = Flask(__name__)

# Retrieve environment variables with default values
#aws_access_key_id = config('AWS_ACCESS_KEY_ID')
#aws_secret_access_key = config('AWS_SECRET_ACCESS_KEY')
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_region = os.environ.get('AWS_REGION')
aws_s3_bucket = os.environ.get('AWS_S3_BUCKET', 'twixorapi-bucket')

# Initialize the S3 client
s3 = boto3.client('s3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

# S3 resource for downloading files
s3_resource = boto3.resource('s3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

# CSV Processor
def process_csv_data(csv_text, start_row, end_row):
    processed_data = []
    try:
        # Process CSV data
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        for i, row in enumerate(csv_reader):
            if start_row <= i < end_row:
                processed_data.append(row)
            elif i >= end_row:
                break

        return processed_data

    except Exception as e:
        return None

# Data Endpoint for CSV files
@app.route('/api/data/<file_name>', methods=['GET'])
def get_data(file_name):
    try:
        # Retrieve start and end row parameters from the query string
        start_row = int(request.args.get('start_row', 0))
        end_row = int(request.args.get('end_row', 100))  # Default end_row value

        try:
            # Check if the file exists in the bucket
            s3_object = s3.get_object(Bucket=aws_s3_bucket, Key=f'data/{file_name}')
            file_extension = file_name.split('.')[-1]

            if file_extension == 'csv':
                # Process CSV data
                data_body = s3_object['Body'].read().decode('utf-8')
                processed_data = process_csv_data(data_body, start_row, end_row)

                if processed_data is not None:
                    return jsonify({"data": processed_data})
                else:
                    return jsonify({"error": "Failed to process data from the file"}), 500  # Return a 500 Internal Server Error status code

        except botocore.exceptions.ClientError as e:
            return jsonify({"error": "S3 operation failed", "details": str(e)}), 500  # Handle S3-related errors

        return jsonify({"error": "Unsupported file type"}), 400  # Return a 400 Bad Request for unsupported file types

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500  # Handle other unexpected errors

# Image Endpoint
@app.route('/api/images', methods=['GET'])
def get_images():
    try:
        base64_images = {}

        # List all objects in the 'images' folder
        s3_objects = s3.list_objects(Bucket=aws_s3_bucket, Prefix='images/')

        if 'Contents' in s3_objects:
            for obj in s3_objects['Contents']:
                # Extract image name from the object key
                image_name = obj['Key'].replace('images/', '').replace('.jpg', '')

                # Fetch the image data
                obj = s3.get_object(Bucket=aws_s3_bucket, Key=obj['Key'])
                image_data = obj['Body'].read()

                # Convert the image to base64
                base64_data = base64.b64encode(image_data).decode('utf-8')

                base64_images[image_name] = base64_data

        # Return the base64-encoded images as a JSON response
        return jsonify({"base64_images": base64_images})
    except botocore.exceptions.ClientError as e:
        # Handle S3-related errors
        return jsonify({"error": "S3 operation failed", "details": str(e)}), 500
    except Exception as e:
        # Handle other unexpected errors
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

# List Files Endpoint
@app.route('/api/list_files', methods=['GET'])
def list_files():
    try:
        s3 = boto3.client('s3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

        # List files in the specified S3 bucket
        s3_objects = s3.list_objects(Bucket=aws_s3_bucket)

        # Extract file names from S3 objects
        file_list = [obj['Key'] for obj in s3_objects['Contents']]

        return jsonify({"files": file_list})
    except botocore.exceptions.ClientError as e:
        return jsonify({"error": "S3 operation failed", "details": str(e)}), 500  # Handle S3-related errors
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500  # Handle other unexpected errors

if __name__ == '__main__':
    app.run(debug=True)
