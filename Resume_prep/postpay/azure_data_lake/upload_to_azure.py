"""
This script uploads the simulated SAP data from local disk to Azure Data Lake Storage Gen2.
"""

from azure.storage.blob import BlobServiceClient
import os

# === CONFIGURATION (Fill these in) ===
STORAGE_ACCOUNT_NAME = "adlspostpaydev"  # Replace with your storage account name
STORAGE_ACCOUNT_KEY = "YOUR_KEY_HERE"    # Replace with key1 from Azure Portal
CONTAINER_NAME = "bronze"                # The container to upload to

# Local source folder
SOURCE_FOLDER = "sap_system_source"

# === UPLOAD FUNCTION ===
def upload_to_adls(local_folder, container, account_name, account_key):
    # Connect to Azure
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container)
    
    # Upload each file
    for filename in os.listdir(local_folder):
        if filename.endswith('.csv'):
            file_path = os.path.join(local_folder, filename)
            blob_client = container_client.get_blob_client(filename)
            
            print(f"Uploading {filename} to Azure Data Lake...")
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            print(f"✅ Successfully uploaded {filename}")

# === RUN ===
if __name__ == "__main__":
    if "YOUR_KEY_HERE" in STORAGE_ACCOUNT_KEY:
        print("⚠️ ERROR: Please update STORAGE_ACCOUNT_KEY in this script with your actual Azure key.")
        print("Get it from: Azure Portal → Storage Account → Access keys → key1")
        exit(1)
    
    if not os.path.exists(SOURCE_FOLDER):
        print(f"⚠️ ERROR: Source folder '{SOURCE_FOLDER}' not found.")
        print("Run 'python virtual_s4_hana.py' first to generate the SAP data.")
        exit(1)
    
    upload_to_adls(SOURCE_FOLDER, CONTAINER_NAME, STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY)
    print("\n🎉 All files uploaded successfully to Azure Data Lake!")
    print(f"You can verify this in Azure Portal → Storage Account → Containers → {CONTAINER_NAME}")
