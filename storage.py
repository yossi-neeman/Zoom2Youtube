#!/usr/bin/env python3
"""
Storage abstraction layer for local filesystem and S3
Automatically detects environment and uses appropriate storage
"""

import os
import json
import boto3
from pathlib import Path
from typing import Optional, List, BinaryIO
import tempfile
import shutil


class StorageBackend:
    """Base class for storage backends"""
    
    def save_file(self, source_path: str, dest_key: str) -> str:
        """Save a file and return its identifier"""
        raise NotImplementedError
    
    def read_file(self, key: str) -> bytes:
        """Read a file and return its contents"""
        raise NotImplementedError
    
    def read_text(self, key: str) -> str:
        """Read a text file"""
        raise NotImplementedError
    
    def write_text(self, key: str, content: str):
        """Write a text file"""
        raise NotImplementedError
    
    def exists(self, key: str) -> bool:
        """Check if a file exists"""
        raise NotImplementedError
    
    def delete(self, key: str):
        """Delete a file"""
        raise NotImplementedError
    
    def delete_directory(self, prefix: str):
        """Delete a directory and all its contents"""
        raise NotImplementedError
    
    def list_files(self, prefix: str) -> List[str]:
        """List files with given prefix"""
        raise NotImplementedError
    
    def get_local_path(self, key: str) -> str:
        """Get a local path to the file (may download from S3)"""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def _get_full_path(self, key: str) -> Path:
        """Get full path for a key"""
        return self.base_path / key
    
    def save_file(self, source_path: str, dest_key: str) -> str:
        dest_path = self._get_full_path(dest_key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if source_path != str(dest_path):
            shutil.copy2(source_path, dest_path)
        
        return str(dest_path)
    
    def read_file(self, key: str) -> bytes:
        with open(self._get_full_path(key), 'rb') as f:
            return f.read()
    
    def read_text(self, key: str) -> str:
        with open(self._get_full_path(key), 'r') as f:
            return f.read()
    
    def write_text(self, key: str, content: str):
        path = self._get_full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
    
    def exists(self, key: str) -> bool:
        return self._get_full_path(key).exists()
    
    def delete(self, key: str):
        path = self._get_full_path(key)
        if path.exists():
            path.unlink()
    
    def delete_directory(self, prefix: str):
        dir_path = self._get_full_path(prefix)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)
    
    def list_files(self, prefix: str) -> List[str]:
        dir_path = self._get_full_path(prefix)
        if not dir_path.exists():
            return []
        
        files = []
        for item in dir_path.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(self.base_path)
                files.append(str(rel_path))
        return files
    
    def get_local_path(self, key: str) -> str:
        return str(self._get_full_path(key))


class S3Storage(StorageBackend):
    """S3 storage backend"""
    
    def __init__(self, bucket_name: str, prefix: str = ""):
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip('/')
        self.s3_client = boto3.client('s3')
        self.temp_dir = Path(tempfile.gettempdir()) / "zoom2youtube"
        self.temp_dir.mkdir(exist_ok=True)
    
    def _get_s3_key(self, key: str) -> str:
        """Get full S3 key with prefix"""
        if self.prefix:
            return f"{self.prefix}/{key.lstrip('/')}"
        return key.lstrip('/')
    
    def save_file(self, source_path: str, dest_key: str) -> str:
        s3_key = self._get_s3_key(dest_key)
        self.s3_client.upload_file(source_path, self.bucket_name, s3_key)
        return f"s3://{self.bucket_name}/{s3_key}"
    
    def read_file(self, key: str) -> bytes:
        s3_key = self._get_s3_key(key)
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
        return response['Body'].read()
    
    def read_text(self, key: str) -> str:
        return self.read_file(key).decode('utf-8')
    
    def write_text(self, key: str, content: str):
        s3_key = self._get_s3_key(key)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=content.encode('utf-8')
        )
    
    def exists(self, key: str) -> bool:
        s3_key = self._get_s3_key(key)
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except:
            return False
    
    def delete(self, key: str):
        s3_key = self._get_s3_key(key)
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
    
    def delete_directory(self, prefix: str):
        s3_prefix = self._get_s3_key(prefix)
        
        # List all objects with this prefix
        paginator = self.s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
        
        objects_to_delete = []
        for page in pages:
            for obj in page.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})
        
        # Delete in batches of 1000 (S3 limit)
        if objects_to_delete:
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': batch}
                )
    
    def list_files(self, prefix: str) -> List[str]:
        s3_prefix = self._get_s3_key(prefix)
        
        paginator = self.s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
        
        files = []
        for page in pages:
            for obj in page.get('Contents', []):
                # Remove the prefix to get relative path
                key = obj['Key']
                if self.prefix and key.startswith(self.prefix + '/'):
                    key = key[len(self.prefix)+1:]
                files.append(key)
        
        return files
    
    def get_local_path(self, key: str) -> str:
        """Download file from S3 to temp directory and return local path"""
        s3_key = self._get_s3_key(key)
        
        # Create a safe local path
        local_path = self.temp_dir / key.replace('/', '_')
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download from S3
        self.s3_client.download_file(self.bucket_name, s3_key, str(local_path))
        
        return str(local_path)


class Storage:
    """
    Unified storage interface that automatically uses local or S3 storage
    based on environment variables
    """
    
    def __init__(self):
        # Determine which backend to use
        use_s3 = os.environ.get('USE_S3_STORAGE', 'false').lower() == 'true'
        
        if use_s3:
            bucket = os.environ.get('S3_BUCKET')
            prefix = os.environ.get('S3_PREFIX', 'zoom2youtube')
            
            if not bucket:
                raise ValueError("S3_BUCKET environment variable required when USE_S3_STORAGE=true")
            
            print(f"🪣 Using S3 storage: s3://{bucket}/{prefix}")
            self.backend = S3Storage(bucket, prefix)
            self.storage_type = 's3'
        else:
            print("💾 Using local filesystem storage")
            self.backend = LocalStorage()
            self.storage_type = 'local'
    
    # Delegate all methods to the backend
    def save_file(self, source_path: str, dest_key: str) -> str:
        return self.backend.save_file(source_path, dest_key)
    
    def read_file(self, key: str) -> bytes:
        return self.backend.read_file(key)
    
    def read_text(self, key: str) -> str:
        return self.backend.read_text(key)
    
    def write_text(self, key: str, content: str):
        return self.backend.write_text(key, content)
    
    def exists(self, key: str) -> bool:
        return self.backend.exists(key)
    
    def delete(self, key: str):
        return self.backend.delete(key)
    
    def delete_directory(self, prefix: str):
        return self.backend.delete_directory(prefix)
    
    def list_files(self, prefix: str) -> List[str]:
        return self.backend.list_files(prefix)
    
    def get_local_path(self, key: str) -> str:
        return self.backend.get_local_path(key)
    
    def is_s3(self) -> bool:
        return self.storage_type == 's3'
    
    def is_local(self) -> bool:
        return self.storage_type == 'local'


# Global storage instance
_storage = None

def get_storage() -> Storage:
    """Get the global storage instance"""
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage
