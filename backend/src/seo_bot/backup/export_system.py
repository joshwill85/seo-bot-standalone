"""
Data Export and Backup System
Handles automated backups, data exports, and disaster recovery
"""

import asyncio
import json
import csv
import zipfile
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import logging
import boto3
from google.cloud import storage as gcs
import schedule
import sqlite3
import pandas as pd

@dataclass
class BackupConfig:
    """Configuration for backup operations"""
    frequency: str  # daily, weekly, monthly
    retention_days: int
    storage_provider: str  # local, s3, gcs, azure
    compression: bool
    encryption: bool
    incremental: bool
    exclude_tables: List[str]
    include_files: List[str]

@dataclass
class ExportConfig:
    """Configuration for data exports"""
    format: str  # json, csv, excel, sql, parquet
    date_range: Optional[Dict[str, str]]
    filters: Optional[Dict[str, Any]]
    include_metadata: bool
    compress: bool

class DataExporter:
    """Handles data export in multiple formats"""
    
    def __init__(self):
        self.supported_formats = ['json', 'csv', 'excel', 'sql', 'parquet', 'xml']
        
    async def export_data(
        self, 
        data: Union[List[Dict], pd.DataFrame], 
        config: ExportConfig,
        output_path: str
    ) -> str:
        """Export data in specified format"""
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
            
        # Apply filters if specified
        if config.filters:
            df = self._apply_filters(df, config.filters)
            
        # Apply date range if specified
        if config.date_range:
            df = self._apply_date_range(df, config.date_range)
            
        # Export based on format
        export_path = await self._export_by_format(df, config, output_path)
        
        # Add metadata if requested
        if config.include_metadata:
            await self._add_metadata(export_path, config, df)
            
        # Compress if requested
        if config.compress:
            export_path = await self._compress_export(export_path)
            
        return export_path
    
    async def _export_by_format(
        self, 
        df: pd.DataFrame, 
        config: ExportConfig, 
        output_path: str
    ) -> str:
        """Export data based on format"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if config.format == 'json':
            export_file = f"{output_path}/export_{timestamp}.json"
            df.to_json(export_file, orient='records', indent=2)
            
        elif config.format == 'csv':
            export_file = f"{output_path}/export_{timestamp}.csv"
            df.to_csv(export_file, index=False)
            
        elif config.format == 'excel':
            export_file = f"{output_path}/export_{timestamp}.xlsx"
            with pd.ExcelWriter(export_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                # Add summary sheet
                summary_df = self._create_summary(df)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
        elif config.format == 'sql':
            export_file = f"{output_path}/export_{timestamp}.sql"
            await self._export_sql(df, export_file)
            
        elif config.format == 'parquet':
            export_file = f"{output_path}/export_{timestamp}.parquet"
            df.to_parquet(export_file, index=False)
            
        elif config.format == 'xml':
            export_file = f"{output_path}/export_{timestamp}.xml"
            df.to_xml(export_file, index=False)
            
        else:
            raise ValueError(f"Unsupported format: {config.format}")
            
        return export_file
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply filters to dataframe"""
        filtered_df = df.copy()
        
        for column, condition in filters.items():
            if isinstance(condition, dict):
                if 'gt' in condition:
                    filtered_df = filtered_df[filtered_df[column] > condition['gt']]
                if 'lt' in condition:
                    filtered_df = filtered_df[filtered_df[column] < condition['lt']]
                if 'eq' in condition:
                    filtered_df = filtered_df[filtered_df[column] == condition['eq']]
                if 'in' in condition:
                    filtered_df = filtered_df[filtered_df[column].isin(condition['in'])]
            else:
                filtered_df = filtered_df[filtered_df[column] == condition]
                
        return filtered_df
    
    def _apply_date_range(self, df: pd.DataFrame, date_range: Dict[str, str]) -> pd.DataFrame:
        """Apply date range filter"""
        date_column = date_range.get('column', 'created_at')
        start_date = date_range.get('start')
        end_date = date_range.get('end')
        
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            
            if start_date:
                df = df[df[date_column] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df[date_column] <= pd.to_datetime(end_date)]
                
        return df
    
    async def _export_sql(self, df: pd.DataFrame, export_file: str):
        """Export as SQL INSERT statements"""
        with open(export_file, 'w') as f:
            # Write table creation statement
            f.write(self._generate_create_table_sql(df))
            f.write('\n\n')
            
            # Write INSERT statements
            for _, row in df.iterrows():
                values = ', '.join([f"'{str(val)}'" if pd.notna(val) else 'NULL' for val in row])
                f.write(f"INSERT INTO exported_data VALUES ({values});\n")
    
    def _generate_create_table_sql(self, df: pd.DataFrame) -> str:
        """Generate CREATE TABLE statement"""
        columns = []
        for col in df.columns:
            dtype = df[col].dtype
            
            if dtype == 'object':
                sql_type = 'TEXT'
            elif dtype in ['int64', 'int32']:
                sql_type = 'INTEGER'
            elif dtype in ['float64', 'float32']:
                sql_type = 'REAL'
            elif dtype == 'datetime64[ns]':
                sql_type = 'TIMESTAMP'
            else:
                sql_type = 'TEXT'
                
            columns.append(f"{col} {sql_type}")
        
        return f"CREATE TABLE exported_data (\n  {',\n  '.join(columns)}\n);"
    
    def _create_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create summary statistics"""
        summary_data = []
        
        # Basic info
        summary_data.append(['Total Rows', len(df)])
        summary_data.append(['Total Columns', len(df.columns)])
        summary_data.append(['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        
        # Column types
        for col in df.columns:
            summary_data.append([f'Column: {col}', str(df[col].dtype)])
            
        return pd.DataFrame(summary_data, columns=['Metric', 'Value'])
    
    async def _add_metadata(self, export_path: str, config: ExportConfig, df: pd.DataFrame):
        """Add metadata file to export"""
        metadata = {
            'export_timestamp': datetime.now().isoformat(),
            'format': config.format,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': list(df.columns),
            'filters_applied': config.filters or {},
            'date_range_applied': config.date_range or {},
            'file_size_bytes': os.path.getsize(export_path)
        }
        
        metadata_path = export_path.replace(Path(export_path).suffix, '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def _compress_export(self, export_path: str) -> str:
        """Compress export file"""
        compressed_path = f"{export_path}.zip"
        
        with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(export_path, Path(export_path).name)
            
            # Include metadata if exists
            metadata_path = export_path.replace(Path(export_path).suffix, '_metadata.json')
            if os.path.exists(metadata_path):
                zipf.write(metadata_path, Path(metadata_path).name)
        
        # Remove original files
        os.remove(export_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            
        return compressed_path

class BackupManager:
    """Manages automated backups and disaster recovery"""
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.storage_providers = {
            'local': LocalStorage(),
            's3': S3Storage(),
            'gcs': GCSStorage(),
            'azure': AzureStorage()
        }
        
    async def create_backup(self, source_data: Dict[str, Any]) -> str:
        """Create a complete backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"seo_bot_backup_{timestamp}"
        
        # Create backup directory
        backup_dir = Path(f"backups/{backup_name}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup database data
        await self._backup_database(backup_dir, source_data)
        
        # Backup configuration files
        await self._backup_config(backup_dir)
        
        # Backup user files
        await self._backup_files(backup_dir)
        
        # Create backup manifest
        manifest = await self._create_manifest(backup_dir)
        
        # Compress if enabled
        if self.config.compression:
            backup_path = await self._compress_backup(backup_dir)
        else:
            backup_path = str(backup_dir)
        
        # Encrypt if enabled
        if self.config.encryption:
            backup_path = await self._encrypt_backup(backup_path)
        
        # Upload to cloud storage
        if self.config.storage_provider != 'local':
            backup_path = await self._upload_backup(backup_path)
        
        # Clean up old backups
        await self._cleanup_old_backups()
        
        logging.info(f"Backup created successfully: {backup_path}")
        return backup_path
    
    async def _backup_database(self, backup_dir: Path, source_data: Dict[str, Any]):
        """Backup database tables"""
        db_dir = backup_dir / "database"
        db_dir.mkdir(exist_ok=True)
        
        for table_name, data in source_data.items():
            if table_name in self.config.exclude_tables:
                continue
                
            # Export as JSON
            table_file = db_dir / f"{table_name}.json"
            with open(table_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        # Create SQL dump
        sql_file = db_dir / "full_dump.sql"
        await self._create_sql_dump(sql_file, source_data)
    
    async def _backup_config(self, backup_dir: Path):
        """Backup configuration files"""
        config_dir = backup_dir / "config"
        config_dir.mkdir(exist_ok=True)
        
        config_files = [
            "pyproject.toml",
            "requirements.txt",
            "package.json",
            ".env.example"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                shutil.copy2(config_file, config_dir / config_file)
    
    async def _backup_files(self, backup_dir: Path):
        """Backup user files and directories"""
        files_dir = backup_dir / "files"
        files_dir.mkdir(exist_ok=True)
        
        for file_path in self.config.include_files:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.copytree(file_path, files_dir / Path(file_path).name)
                else:
                    shutil.copy2(file_path, files_dir / Path(file_path).name)
    
    async def _create_manifest(self, backup_dir: Path) -> Dict[str, Any]:
        """Create backup manifest"""
        manifest = {
            'backup_timestamp': datetime.now().isoformat(),
            'backup_type': 'incremental' if self.config.incremental else 'full',
            'version': '1.0',
            'files': [],
            'checksums': {},
            'total_size_bytes': 0
        }
        
        # Calculate file sizes and checksums
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(backup_dir)
                
                file_size = file_path.stat().st_size
                manifest['files'].append(str(relative_path))
                manifest['total_size_bytes'] += file_size
                
                # Calculate checksum
                import hashlib
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    manifest['checksums'][str(relative_path)] = file_hash
        
        # Save manifest
        manifest_file = backup_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
    
    async def _create_sql_dump(self, sql_file: Path, source_data: Dict[str, Any]):
        """Create SQL dump of all data"""
        with open(sql_file, 'w') as f:
            f.write("-- SEO Bot Database Backup\n")
            f.write(f"-- Created: {datetime.now().isoformat()}\n\n")
            
            for table_name, data in source_data.items():
                if table_name in self.config.exclude_tables:
                    continue
                    
                if isinstance(data, list) and data:
                    # Create table structure from first record
                    first_record = data[0]
                    columns = list(first_record.keys())
                    
                    f.write(f"DROP TABLE IF EXISTS {table_name};\n")
                    f.write(f"CREATE TABLE {table_name} (\n")
                    
                    column_defs = []
                    for col in columns:
                        column_defs.append(f"  {col} TEXT")
                    
                    f.write(",\n".join(column_defs))
                    f.write("\n);\n\n")
                    
                    # Insert data
                    for record in data:
                        values = []
                        for col in columns:
                            value = record.get(col)
                            if value is None:
                                values.append('NULL')
                            else:
                                values.append(f"'{str(value).replace(\"'\", \"''\")}'")
                        
                        f.write(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                    
                    f.write("\n")
    
    async def _compress_backup(self, backup_dir: Path) -> str:
        """Compress backup directory"""
        compressed_file = f"{backup_dir}.tar.gz"
        
        import tarfile
        with tarfile.open(compressed_file, 'w:gz') as tar:
            tar.add(backup_dir, arcname=backup_dir.name)
        
        # Remove original directory
        shutil.rmtree(backup_dir)
        
        return compressed_file
    
    async def _encrypt_backup(self, backup_path: str) -> str:
        """Encrypt backup file"""
        # Simplified encryption (in production, use proper encryption)
        encrypted_path = f"{backup_path}.encrypted"
        
        try:
            from cryptography.fernet import Fernet
            
            # Generate key (in production, use proper key management)
            key = Fernet.generate_key()
            fernet = Fernet(key)
            
            with open(backup_path, 'rb') as f:
                original_data = f.read()
            
            encrypted_data = fernet.encrypt(original_data)
            
            with open(encrypted_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Save key securely (this is simplified)
            key_file = f"{backup_path}.key"
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Remove original
            os.remove(backup_path)
            
            return encrypted_path
            
        except ImportError:
            logging.warning("Cryptography package not installed, skipping encryption")
            return backup_path
    
    async def _upload_backup(self, backup_path: str) -> str:
        """Upload backup to cloud storage"""
        storage = self.storage_providers[self.config.storage_provider]
        
        remote_path = await storage.upload(backup_path)
        
        # Remove local backup if upload successful
        if remote_path and self.config.storage_provider != 'local':
            os.remove(backup_path)
            
            # Also remove key file if exists
            key_file = f"{backup_path}.key"
            if os.path.exists(key_file):
                await storage.upload(key_file)
                os.remove(key_file)
        
        return remote_path or backup_path
    
    async def _cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        
        # Local cleanup
        backup_dir = Path("backups")
        if backup_dir.exists():
            for backup_file in backup_dir.iterdir():
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    if backup_file.is_dir():
                        shutil.rmtree(backup_file)
                    else:
                        backup_file.unlink()
        
        # Cloud cleanup
        if self.config.storage_provider != 'local':
            storage = self.storage_providers[self.config.storage_provider]
            await storage.cleanup_old_files(cutoff_date)

class StorageProvider:
    """Base class for storage providers"""
    
    async def upload(self, file_path: str) -> str:
        raise NotImplementedError
    
    async def download(self, remote_path: str, local_path: str) -> bool:
        raise NotImplementedError
    
    async def cleanup_old_files(self, cutoff_date: datetime):
        raise NotImplementedError

class LocalStorage(StorageProvider):
    """Local file system storage"""
    
    async def upload(self, file_path: str) -> str:
        return file_path
    
    async def download(self, remote_path: str, local_path: str) -> bool:
        shutil.copy2(remote_path, local_path)
        return True
    
    async def cleanup_old_files(self, cutoff_date: datetime):
        pass  # Already handled in backup manager

class S3Storage(StorageProvider):
    """AWS S3 storage provider"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('S3_BACKUP_BUCKET', 'seo-bot-backups')
    
    async def upload(self, file_path: str) -> str:
        try:
            file_name = Path(file_path).name
            remote_path = f"backups/{datetime.now().strftime('%Y/%m')}/{file_name}"
            
            self.s3_client.upload_file(file_path, self.bucket_name, remote_path)
            
            return f"s3://{self.bucket_name}/{remote_path}"
            
        except Exception as e:
            logging.error(f"S3 upload failed: {e}")
            return None
    
    async def download(self, remote_path: str, local_path: str) -> bool:
        try:
            # Extract bucket and key from S3 URL
            s3_path = remote_path.replace('s3://', '').split('/', 1)
            bucket = s3_path[0]
            key = s3_path[1]
            
            self.s3_client.download_file(bucket, key, local_path)
            return True
            
        except Exception as e:
            logging.error(f"S3 download failed: {e}")
            return False
    
    async def cleanup_old_files(self, cutoff_date: datetime):
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='backups/'
            )
            
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
        except Exception as e:
            logging.error(f"S3 cleanup failed: {e}")

class GCSStorage(StorageProvider):
    """Google Cloud Storage provider"""
    
    def __init__(self):
        try:
            self.client = gcs.Client()
            self.bucket_name = os.getenv('GCS_BACKUP_BUCKET', 'seo-bot-backups')
            self.bucket = self.client.bucket(self.bucket_name)
        except Exception as e:
            logging.error(f"GCS initialization failed: {e}")
            self.client = None
    
    async def upload(self, file_path: str) -> str:
        if not self.client:
            return None
            
        try:
            file_name = Path(file_path).name
            blob_name = f"backups/{datetime.now().strftime('%Y/%m')}/{file_name}"
            
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(file_path)
            
            return f"gcs://{self.bucket_name}/{blob_name}"
            
        except Exception as e:
            logging.error(f"GCS upload failed: {e}")
            return None
    
    async def download(self, remote_path: str, local_path: str) -> bool:
        if not self.client:
            return False
            
        try:
            # Extract blob name from GCS URL
            blob_name = remote_path.replace(f'gcs://{self.bucket_name}/', '')
            
            blob = self.bucket.blob(blob_name)
            blob.download_to_filename(local_path)
            
            return True
            
        except Exception as e:
            logging.error(f"GCS download failed: {e}")
            return False
    
    async def cleanup_old_files(self, cutoff_date: datetime):
        if not self.client:
            return
            
        try:
            blobs = self.bucket.list_blobs(prefix='backups/')
            
            for blob in blobs:
                if blob.time_created.replace(tzinfo=None) < cutoff_date:
                    blob.delete()
                    
        except Exception as e:
            logging.error(f"GCS cleanup failed: {e}")

class AzureStorage(StorageProvider):
    """Azure Blob Storage provider"""
    
    def __init__(self):
        # Placeholder for Azure implementation
        self.client = None
    
    async def upload(self, file_path: str) -> str:
        # Implement Azure upload
        return None
    
    async def download(self, remote_path: str, local_path: str) -> bool:
        # Implement Azure download
        return False
    
    async def cleanup_old_files(self, cutoff_date: datetime):
        # Implement Azure cleanup
        pass

class ScheduledBackups:
    """Handles scheduled backup operations"""
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.scheduler_running = False
    
    def setup_schedules(self):
        """Setup backup schedules based on configuration"""
        frequency = self.backup_manager.config.frequency
        
        if frequency == 'daily':
            schedule.every().day.at("02:00").do(self._run_backup)
        elif frequency == 'weekly':
            schedule.every().sunday.at("01:00").do(self._run_backup)
        elif frequency == 'monthly':
            schedule.every().month.do(self._run_backup)
    
    def _run_backup(self):
        """Run backup operation"""
        asyncio.create_task(self._async_backup())
    
    async def _async_backup(self):
        """Async backup operation"""
        try:
            # Collect data from all sources
            source_data = await self._collect_source_data()
            
            # Create backup
            backup_path = await self.backup_manager.create_backup(source_data)
            
            logging.info(f"Scheduled backup completed: {backup_path}")
            
        except Exception as e:
            logging.error(f"Scheduled backup failed: {e}")
    
    async def _collect_source_data(self) -> Dict[str, Any]:
        """Collect data from all sources for backup"""
        # This would integrate with your actual data sources
        return {
            'keywords': [],
            'campaigns': [],
            'reports': [],
            'users': [],
            'businesses': []
        }
    
    def start_scheduler(self):
        """Start the backup scheduler"""
        self.scheduler_running = True
        
        def run_scheduler():
            while self.scheduler_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        import threading
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the backup scheduler"""
        self.scheduler_running = False

# Example usage and CLI interface
if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) < 2:
            print("Usage: python export_system.py [export|backup|schedule]")
            return
        
        command = sys.argv[1]
        
        if command == "export":
            # Example data export
            exporter = DataExporter()
            
            sample_data = [
                {'id': 1, 'keyword': 'seo tools', 'volume': 1000, 'difficulty': 45},
                {'id': 2, 'keyword': 'seo software', 'volume': 800, 'difficulty': 55},
                {'id': 3, 'keyword': 'keyword research', 'volume': 1200, 'difficulty': 40}
            ]
            
            config = ExportConfig(
                format='excel',
                include_metadata=True,
                compress=True,
                filters={'volume': {'gt': 500}},
                date_range=None
            )
            
            export_path = await exporter.export_data(sample_data, config, "exports")
            print(f"Data exported to: {export_path}")
        
        elif command == "backup":
            # Example backup
            backup_config = BackupConfig(
                frequency='daily',
                retention_days=30,
                storage_provider='local',
                compression=True,
                encryption=True,
                incremental=False,
                exclude_tables=['temp_data', 'logs'],
                include_files=['config/', 'templates/']
            )
            
            backup_manager = BackupManager(backup_config)
            
            source_data = {
                'keywords': [{'id': 1, 'keyword': 'test'}],
                'campaigns': [{'id': 1, 'name': 'Test Campaign'}]
            }
            
            backup_path = await backup_manager.create_backup(source_data)
            print(f"Backup created: {backup_path}")
        
        elif command == "schedule":
            # Setup scheduled backups
            backup_config = BackupConfig(
                frequency='daily',
                retention_days=30,
                storage_provider='local',
                compression=True,
                encryption=False,
                incremental=True,
                exclude_tables=[],
                include_files=[]
            )
            
            backup_manager = BackupManager(backup_config)
            scheduler = ScheduledBackups(backup_manager)
            
            scheduler.setup_schedules()
            scheduler.start_scheduler()
            
            print("Scheduled backups started. Press Ctrl+C to stop.")
            
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                scheduler.stop_scheduler()
                print("Scheduler stopped.")
    
    asyncio.run(main())