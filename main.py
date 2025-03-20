from flask import Flask, request, jsonify
import os
import json
from pymongo import MongoClient
import boto3
from Final_parsing import Resume_Parser

app = Flask(__name__)

# S3 Configuration
s3 = boto3.client(
    "s3",
    aws_access_key_id="AKIAXA43P4EWMEAKEK6H",
    aws_secret_access_key="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",
    region_name="ap-south-1"
)

# MongoDB Connection
client = MongoClient("mongodb+srv://olibrtestdev:KKmPJbHWNqJP6qHL@testdev.xwjoi.mongodb.net/test_latest_oct_09_24?retryWrites=true&w=majority")
db = client["resume_database"]
collection = db["Resume"]

# Folder for downloads
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/get-resume', methods=['POST'])
def get_resume():
    try:
        data = request.get_json()

        # Validate input JSON payload
        if not data or 'pdf_key' not in data:
            return jsonify({"error": "Missing 'pdf_key' field"}), 400

        pdf_key = data['pdf_key'].strip()
        local_filename = os.path.basename(pdf_key)
        local_filepath = os.path.join(DOWNLOAD_FOLDER, local_filename)

        try:
            # Step 1: Download file from S3
            s3_response = s3.get_object(Bucket='olibr-new', Key=pdf_key)
            file_data = s3_response['Body'].read()

            with open(local_filepath, 'wb') as f:
                f.write(file_data)

            print(f"✅ File downloaded successfully: {local_filepath}")

        except Exception as e:
            return jsonify({"error": "Failed to download file from S3", "details": str(e)}), 500

        try:
            # Step 2: Parse the resume using Resume_Parser
            print(f"📄 Parsing {local_filename}")
            parsed_data = Resume_Parser(local_filepath)

            if not parsed_data:
                return jsonify({"error": "Error in parsing resume"}), 500

            print(f"✅ Parsing completed for {local_filename}")

        except Exception as e:
            return jsonify({"error": "Failed to execute Resume_Parser", "details": str(e)}), 500

        try:
            # Step 3: Store parsed resume data in MongoDB
            mongo_entry = {
                "resume_filename": local_filename,
                "parsed_resume": parsed_data,
            }
            collection.insert_one(mongo_entry)

        except Exception as e:
            return jsonify({"error": "Failed to save data to MongoDB", "details": str(e)}), 500

        return jsonify({
            "resume_data": parsed_data
        })

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
