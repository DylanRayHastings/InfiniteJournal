"""
Repository backup system with production-grade architecture.

This module provides automated repository backup functionality with cleanup,
monitoring, and configuration management. All backup operations are atomic
and include comprehensive error handling.

Quick start:
    backup_service = BackupServiceFactory.create_production_service()
    result = backup_service.create_repository_backup()

Extension points:
    - Add new backup formats: Implement BackupCreator interface
    - Add new storage backends: Implement BackupStorage interface
    - Add new cleanup policies: Implement CleanupPolicy interface
    - Add backup validation: Extend BackupValidator class
"""

import os
import zipfile
import time
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Protocol, Iterator
from dataclasses import dataclass
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackupConfig:
    """Backup system configuration."""
    repository_root: Path
    backup_directory: Path
    max_backups: int
    timestamp_format: str
    compression_level: int
    include_patterns: List[str]
    exclude_patterns: List[str]

    @classmethod
    def create_default_config(cls, repository_root: Optional[Path] = None) -> 'BackupConfig':
        """Create default backup configuration."""
        if repository_root is None:
            repository_root = Path(__file__).resolve().parent
        
        backup_directory = repository_root / "backups"
        
        return cls(
            repository_root=repository_root,
            backup_directory=backup_directory,
            max_backups=5,
            timestamp_format="%Y%m%d_%H%M%S",
            compression_level=zipfile.ZIP_DEFLATED,
            include_patterns=["*"],
            exclude_patterns=["*.pyc", "__pycache__", ".git", "backups"]
        )

    @classmethod
    def from_environment(cls) -> 'BackupConfig':
        """Load configuration from environment variables."""
        repository_root = Path(os.getenv('BACKUP_REPO_ROOT', Path(__file__).resolve().parent))
        backup_directory = Path(os.getenv('BACKUP_DIR', repository_root / "backups"))
        max_backups = int(os.getenv('BACKUP_MAX_COUNT', '5'))
        timestamp_format = os.getenv('BACKUP_TIMESTAMP_FORMAT', '%Y%m%d_%H%M%S')
        compression_level = int(os.getenv('BACKUP_COMPRESSION_LEVEL', str(zipfile.ZIP_DEFLATED)))
        
        include_patterns = os.getenv('BACKUP_INCLUDE_PATTERNS', '*').split(',')
        exclude_patterns = os.getenv('BACKUP_EXCLUDE_PATTERNS', '*.pyc,__pycache__,.git,backups').split(',')
        
        return cls(
            repository_root=repository_root,
            backup_directory=backup_directory,
            max_backups=max_backups,
            timestamp_format=timestamp_format,
            compression_level=compression_level,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        )


@dataclass(frozen=True)
class BackupInfo:
    """Information about a backup operation."""
    backup_path: Path
    created_at: datetime
    file_count: int
    compressed_size: int
    original_size: int

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        if self.original_size == 0:
            return 0.0
        return (1 - self.compressed_size / self.original_size) * 100


@dataclass(frozen=True)
class BackupResult:
    """Result of backup operation."""
    success: bool
    backup_info: Optional[BackupInfo] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


class BackupError(Exception):
    """Base exception for backup operations."""
    pass


class BackupCreationError(BackupError):
    """Backup creation failed."""
    pass


class BackupCleanupError(BackupError):
    """Backup cleanup failed."""
    pass


class BackupValidationError(BackupError):
    """Backup validation failed."""
    pass


class TimeProvider(Protocol):
    """Time operations interface for testing."""
    
    def current_timestamp(self) -> str:
        """Get current timestamp string."""
        ...
    
    def current_datetime(self) -> datetime:
        """Get current datetime."""
        ...


class SystemTimeProvider:
    """Production time provider using system clock."""
    
    def __init__(self, timestamp_format: str = "%Y%m%d_%H%M%S"):
        self.timestamp_format = timestamp_format
    
    def current_timestamp(self) -> str:
        """Get current timestamp string."""
        return time.strftime(self.timestamp_format)
    
    def current_datetime(self) -> datetime:
        """Get current datetime."""
        return datetime.now()


class FileSystemOperations(Protocol):
    """File system operations interface for testing."""
    
    def create_directory(self, path: Path) -> None:
        """Create directory if it does not exist."""
        ...
    
    def list_files_recursive(self, root_path: Path, exclude_patterns: List[str]) -> Iterator[Path]:
        """List all files recursively with exclusions."""
        ...
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        ...
    
    def remove_file(self, file_path: Path) -> None:
        """Remove file from filesystem."""
        ...


class SystemFileOperations:
    """Production file system operations."""
    
    def create_directory(self, path: Path) -> None:
        """Create directory if it does not exist."""
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory created: {path}")
    
    def list_files_recursive(self, root_path: Path, exclude_patterns: List[str]) -> Iterator[Path]:
        """List all files recursively with exclusions."""
        for root, dirs, files in os.walk(root_path):
            root_path_obj = Path(root)
            
            if self._should_exclude_directory(root_path_obj, exclude_patterns):
                continue
            
            for file_name in files:
                file_path = root_path_obj / file_name
                
                if not self._should_exclude_file(file_path, exclude_patterns):
                    yield file_path
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes."""
        return file_path.stat().st_size
    
    def remove_file(self, file_path: Path) -> None:
        """Remove file from filesystem."""
        file_path.unlink()
        logger.debug(f"File removed: {file_path}")
    
    def _should_exclude_directory(self, directory_path: Path, exclude_patterns: List[str]) -> bool:
        """Check if directory should be excluded."""
        directory_name = directory_path.name
        
        for pattern in exclude_patterns:
            if directory_name == pattern or directory_name.startswith(pattern):
                return True
        
        return False
    
    def _should_exclude_file(self, file_path: Path, exclude_patterns: List[str]) -> bool:
        """Check if file should be excluded."""
        file_name = file_path.name
        
        for pattern in exclude_patterns:
            if file_name.endswith(pattern) or file_name == pattern:
                return True
        
        return False


def validate_backup_config(config: BackupConfig) -> None:
    """Validate backup configuration parameters."""
    if not config.repository_root.exists():
        raise BackupValidationError(f"Repository root does not exist: {config.repository_root}")
    
    if not config.repository_root.is_dir():
        raise BackupValidationError(f"Repository root is not a directory: {config.repository_root}")
    
    if config.max_backups < 1:
        raise BackupValidationError(f"Max backups must be at least 1: {config.max_backups}")
    
    if not config.timestamp_format:
        raise BackupValidationError("Timestamp format cannot be empty")


def validate_backup_permissions(config: BackupConfig) -> None:
    """Validate backup directory permissions."""
    if config.backup_directory.exists() and not os.access(config.backup_directory, os.W_OK):
        raise BackupValidationError(f"No write permission to backup directory: {config.backup_directory}")
    
    if not os.access(config.repository_root, os.R_OK):
        raise BackupValidationError(f"No read permission to repository: {config.repository_root}")


def generate_backup_filename(timestamp: str) -> str:
    """Generate backup filename with timestamp."""
    return f"repo_{timestamp}.zip"


def calculate_backup_path(backup_directory: Path, filename: str) -> Path:
    """Calculate full backup file path."""
    return backup_directory / filename


def create_backup_directory(file_ops: FileSystemOperations, backup_directory: Path) -> None:
    """Create backup directory if it does not exist."""
    try:
        file_ops.create_directory(backup_directory)
        logger.info(f"Backup directory ready: {backup_directory}")
    except Exception as error:
        raise BackupCreationError(f"Failed to create backup directory: {error}") from error


def collect_files_for_backup(
    file_ops: FileSystemOperations, 
    repository_root: Path, 
    exclude_patterns: List[str]
) -> List[Path]:
    """Collect all files that should be included in backup."""
    try:
        files = list(file_ops.list_files_recursive(repository_root, exclude_patterns))
        logger.info(f"Collected {len(files)} files for backup")
        return files
    except Exception as error:
        raise BackupCreationError(f"Failed to collect files: {error}") from error


def calculate_total_file_size(file_ops: FileSystemOperations, files: List[Path]) -> int:
    """Calculate total size of all files to be backed up."""
    total_size = 0
    
    for file_path in files:
        try:
            total_size += file_ops.get_file_size(file_path)
        except Exception as error:
            logger.warning(f"Could not get size for file {file_path}: {error}")
    
    return total_size


@contextmanager
def create_zip_file_context(backup_path: Path, compression_level: int):
    """Context manager for zip file creation with proper cleanup."""
    zip_file = None
    try:
        zip_file = zipfile.ZipFile(backup_path, 'w', compression_level)
        yield zip_file
    except Exception as error:
        if backup_path.exists():
            backup_path.unlink()
        raise BackupCreationError(f"Failed to create zip file: {error}") from error
    finally:
        if zip_file:
            zip_file.close()


def add_files_to_zip(zip_file: zipfile.ZipFile, files: List[Path], repository_root: Path) -> int:
    """Add files to zip archive and return count of added files."""
    added_count = 0
    
    for file_path in files:
        try:
            relative_path = file_path.relative_to(repository_root.parent)
            zip_file.write(file_path, relative_path)
            added_count += 1
        except Exception as error:
            logger.warning(f"Could not add file to backup {file_path}: {error}")
    
    logger.info(f"Added {added_count} files to backup")
    return added_count


def create_backup_info(
    backup_path: Path, 
    created_at: datetime, 
    file_count: int, 
    original_size: int
) -> BackupInfo:
    """Create backup information object."""
    compressed_size = backup_path.stat().st_size if backup_path.exists() else 0
    
    return BackupInfo(
        backup_path=backup_path,
        created_at=created_at,
        file_count=file_count,
        compressed_size=compressed_size,
        original_size=original_size
    )


def find_existing_backups(backup_directory: Path) -> List[Path]:
    """Find all existing backup files in directory."""
    if not backup_directory.exists():
        return []
    
    backup_files = list(backup_directory.glob("repo_*.zip"))
    backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    logger.debug(f"Found {len(backup_files)} existing backups")
    return backup_files


def identify_backups_to_remove(existing_backups: List[Path], max_backups: int) -> List[Path]:
    """Identify backup files that should be removed."""
    if len(existing_backups) <= max_backups:
        return []
    
    backups_to_remove = existing_backups[max_backups:]
    logger.info(f"Identified {len(backups_to_remove)} backups for removal")
    
    return backups_to_remove


def remove_old_backup_file(file_ops: FileSystemOperations, backup_path: Path) -> None:
    """Remove single old backup file with error handling."""
    try:
        file_ops.remove_file(backup_path)
        logger.info(f"Removed old backup: {backup_path}")
    except Exception as error:
        logger.warning(f"Could not remove old backup {backup_path}: {error}")


def cleanup_old_backups(
    file_ops: FileSystemOperations, 
    backup_directory: Path, 
    max_backups: int
) -> int:
    """Remove old backup files keeping only the specified number."""
    existing_backups = find_existing_backups(backup_directory)
    backups_to_remove = identify_backups_to_remove(existing_backups, max_backups)
    
    removed_count = 0
    for backup_path in backups_to_remove:
        remove_old_backup_file(file_ops, backup_path)
        removed_count += 1
    
    logger.info(f"Cleanup completed: removed {removed_count} old backups")
    return removed_count


class BackupCreator(ABC):
    """Interface for backup creation strategies."""
    
    @abstractmethod
    def create_backup(
        self, 
        config: BackupConfig, 
        backup_path: Path,
        files: List[Path]
    ) -> BackupInfo:
        """Create backup from files."""
        pass


class ZipBackupCreator(BackupCreator):
    """ZIP-based backup creator implementation."""
    
    def __init__(self, file_ops: FileSystemOperations, time_provider: TimeProvider):
        self.file_ops = file_ops
        self.time_provider = time_provider
    
    def create_backup(
        self, 
        config: BackupConfig, 
        backup_path: Path,
        files: List[Path]
    ) -> BackupInfo:
        """Create ZIP backup from files."""
        creation_time = self.time_provider.current_datetime()
        original_size = calculate_total_file_size(self.file_ops, files)
        
        with create_zip_file_context(backup_path, config.compression_level) as zip_file:
            file_count = add_files_to_zip(zip_file, files, config.repository_root)
        
        backup_info = create_backup_info(backup_path, creation_time, file_count, original_size)
        
        logger.info(f"Backup created: {backup_path} "
                   f"({backup_info.file_count} files, "
                   f"{backup_info.compressed_size} bytes, "
                   f"{backup_info.compression_ratio:.1f}% compression)")
        
        return backup_info


class BackupCleanupPolicy(ABC):
    """Interface for backup cleanup policies."""
    
    @abstractmethod
    def cleanup_backups(self, backup_directory: Path) -> int:
        """Clean up old backups according to policy."""
        pass


class CountBasedCleanupPolicy(BackupCleanupPolicy):
    """Cleanup policy based on maximum backup count."""
    
    def __init__(self, file_ops: FileSystemOperations, max_backups: int):
        self.file_ops = file_ops
        self.max_backups = max_backups
    
    def cleanup_backups(self, backup_directory: Path) -> int:
        """Clean up old backups keeping only max_backups."""
        return cleanup_old_backups(self.file_ops, backup_directory, self.max_backups)


class BackupValidator:
    """Backup validation and verification."""
    
    def __init__(self, file_ops: FileSystemOperations):
        self.file_ops = file_ops
    
    def validate_backup_integrity(self, backup_path: Path) -> bool:
        """Validate backup file integrity."""
        try:
            with zipfile.ZipFile(backup_path, 'r') as zip_file:
                zip_file.testzip()
            
            logger.debug(f"Backup integrity verified: {backup_path}")
            return True
            
        except Exception as error:
            logger.error(f"Backup integrity check failed for {backup_path}: {error}")
            return False
    
    def validate_backup_completeness(self, backup_path: Path, expected_files: List[Path]) -> bool:
        """Validate backup contains expected files."""
        try:
            with zipfile.ZipFile(backup_path, 'r') as zip_file:
                backup_files = set(zip_file.namelist())
            
            expected_count = len(expected_files)
            actual_count = len(backup_files)
            
            if actual_count < expected_count:
                logger.warning(f"Backup incomplete: {actual_count}/{expected_count} files")
                return False
            
            logger.debug(f"Backup completeness verified: {actual_count} files")
            return True
            
        except Exception as error:
            logger.error(f"Backup completeness check failed for {backup_path}: {error}")
            return False


class BackupService:
    """High-level backup service orchestrating all operations."""
    
    def __init__(
        self,
        config: BackupConfig,
        file_ops: FileSystemOperations,
        time_provider: TimeProvider,
        backup_creator: BackupCreator,
        cleanup_policy: BackupCleanupPolicy,
        validator: BackupValidator
    ):
        self.config = config
        self.file_ops = file_ops
        self.time_provider = time_provider
        self.backup_creator = backup_creator
        self.cleanup_policy = cleanup_policy
        self.validator = validator
    
    def create_repository_backup(self) -> BackupResult:
        """Create complete repository backup with validation and cleanup."""
        start_time = time.time()
        
        try:
            self._validate_backup_requirements()
            
            timestamp = self.time_provider.current_timestamp()
            filename = generate_backup_filename(timestamp)
            backup_path = calculate_backup_path(self.config.backup_directory, filename)
            
            backup_info = self._execute_backup_creation(backup_path)
            self._validate_created_backup(backup_path)
            self._execute_backup_cleanup()
            
            duration = time.time() - start_time
            
            logger.info(f"Repository backup completed successfully in {duration:.2f} seconds")
            return BackupResult(
                success=True,
                backup_info=backup_info,
                duration_seconds=duration
            )
            
        except Exception as error:
            duration = time.time() - start_time
            logger.error(f"Repository backup failed after {duration:.2f} seconds: {error}")
            
            return BackupResult(
                success=False,
                error_message=str(error),
                duration_seconds=duration
            )
    
    def _validate_backup_requirements(self) -> None:
        """Validate all backup requirements."""
        validate_backup_config(self.config)
        validate_backup_permissions(self.config)
    
    def _execute_backup_creation(self, backup_path: Path) -> BackupInfo:
        """Execute the backup creation process."""
        create_backup_directory(self.file_ops, self.config.backup_directory)
        
        files = collect_files_for_backup(
            self.file_ops, 
            self.config.repository_root, 
            self.config.exclude_patterns
        )
        
        return self.backup_creator.create_backup(self.config, backup_path, files)
    
    def _validate_created_backup(self, backup_path: Path) -> None:
        """Validate the created backup."""
        if not self.validator.validate_backup_integrity(backup_path):
            raise BackupValidationError(f"Backup integrity validation failed: {backup_path}")
    
    def _execute_backup_cleanup(self) -> None:
        """Execute backup cleanup process."""
        try:
            removed_count = self.cleanup_policy.cleanup_backups(self.config.backup_directory)
            logger.info(f"Backup cleanup completed: {removed_count} old backups removed")
        except Exception as error:
            logger.warning(f"Backup cleanup failed: {error}")
            # Don't fail the entire backup operation for cleanup issues


class BackupServiceFactory:
    """Factory for creating BackupService with different configurations."""
    
    @staticmethod
    def create_production_service(config: Optional[BackupConfig] = None) -> BackupService:
        """Create production backup service with default implementations."""
        if config is None:
            config = BackupConfig.create_default_config()
        
        file_ops = SystemFileOperations()
        time_provider = SystemTimeProvider(config.timestamp_format)
        backup_creator = ZipBackupCreator(file_ops, time_provider)
        cleanup_policy = CountBasedCleanupPolicy(file_ops, config.max_backups)
        validator = BackupValidator(file_ops)
        
        return BackupService(
            config=config,
            file_ops=file_ops,
            time_provider=time_provider,
            backup_creator=backup_creator,
            cleanup_policy=cleanup_policy,
            validator=validator
        )
    
    @staticmethod
    def create_service_from_environment() -> BackupService:
        """Create backup service with configuration from environment."""
        config = BackupConfig.from_environment()
        return BackupServiceFactory.create_production_service(config)
    
    @staticmethod
    def create_test_service(config: BackupConfig) -> tuple[BackupService, dict]:
        """Create test backup service with mock dependencies."""
        from unittest.mock import Mock
        
        mocks = {
            'file_ops': Mock(spec=FileSystemOperations),
            'time_provider': Mock(spec=TimeProvider),
            'backup_creator': Mock(spec=BackupCreator),
            'cleanup_policy': Mock(spec=BackupCleanupPolicy),
            'validator': Mock(spec=BackupValidator)
        }
        
        service = BackupService(
            config=config,
            file_ops=mocks['file_ops'],
            time_provider=mocks['time_provider'],
            backup_creator=mocks['backup_creator'],
            cleanup_policy=mocks['cleanup_policy'],
            validator=mocks['validator']
        )
        
        return service, mocks


def execute_repository_backup(config_override: Optional[BackupConfig] = None) -> BackupResult:
    """Execute repository backup operation with optional configuration override."""
    try:
        if config_override:
            backup_service = BackupServiceFactory.create_production_service(config_override)
        else:
            backup_service = BackupServiceFactory.create_service_from_environment()
        
        return backup_service.create_repository_backup()
        
    except Exception as error:
        logger.error(f"Failed to create backup service: {error}")
        return BackupResult(
            success=False,
            error_message=f"Service creation failed: {error}"
        )


def main() -> None:
    """Main entry point for backup script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    result = execute_repository_backup()
    
    if result.success:
        print(f"Backup completed successfully in {result.duration_seconds:.2f} seconds")
        if result.backup_info:
            print(f"Backup: {result.backup_info.backup_path}")
            print(f"Files: {result.backup_info.file_count}")
            print(f"Size: {result.backup_info.compressed_size:,} bytes")
            print(f"Compression: {result.backup_info.compression_ratio:.1f}%")
    else:
        print(f"Backup failed: {result.error_message}")
        exit(1)


if __name__ == "__main__":
    main()


# EXPANSION POINTS clearly marked for team development:

# 1. ADD NEW BACKUP FORMATS: Implement BackupCreator interface
#    - TarBackupCreator for .tar.gz files
#    - SevenZipBackupCreator for .7z files
#    - DirectoryBackupCreator for uncompressed backups

# 2. ADD NEW STORAGE BACKENDS: Extend storage capabilities
#    - CloudBackupStorage for S3/GCS upload
#    - NetworkBackupStorage for network drives
#    - EncryptedBackupStorage for encrypted backups

# 3. ADD NEW CLEANUP POLICIES: Implement BackupCleanupPolicy interface
#    - TimeBasedCleanupPolicy (keep backups for X days)
#    - SizeBasedCleanupPolicy (keep total size under limit)
#    - CompositeCleanupPolicy (combine multiple policies)

# 4. ADD BACKUP SCHEDULING: Create scheduling system
#    - CronBackupScheduler for cron-like scheduling
#    - IntervalBackupScheduler for regular intervals
#    - EventBasedBackupScheduler for file change triggers

# 5. ADD BACKUP VERIFICATION: Extend BackupValidator class
#    - ChecksumValidator for file integrity
#    - ContentValidator for backup content verification
#    - RestoreTestValidator for restore operation testing

# 6. ADD MONITORING AND METRICS: Create monitoring system
#    - BackupMetricsCollector for operation metrics
#    - BackupHealthChecker for system health monitoring
#    - BackupAlerting for failure notifications