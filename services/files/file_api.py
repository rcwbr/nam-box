"""
Generic File Management API

Provides reusable file upload/management endpoints for any file type and directory.
Purely manages the presence of files on the system.

Environment Variables:
- FILE_BASE_DIR: Directory where files are stored (default: /var/lib/files)
- FILE_EXTENSIONS: Comma-separated list of allowed extensions (e.g., ".nam,.wav")
                   If not set, all files are allowed.

Endpoints:
- GET /all - list all files
- POST /upload - upload file
- POST /upload/multiple - upload multiple files
- DELETE /{name} - delete file
- GET /{name} - download file
"""

import os
import tempfile

from pathlib import Path
from typing import Optional, List, Callable

from pydantic import BaseModel
from fastapi import HTTPException, UploadFile, File, APIRouter, FastAPI
from fastapi.responses import FileResponse


# ==================== Generic Pydantic Models ====================

class FileInfo(BaseModel):
    """Information about a managed file."""
    name: str
    size: int
    path: str


class FileList(BaseModel):
    """List of managed files."""
    files: List[FileInfo]


class FileUploadResponse(BaseModel):
    """Response after file upload."""
    status: str
    uploaded: str
    path: str
    action_result: Optional[dict] = None


# ==================== Generic File Manager ====================

class FileManager:
    """
    Generic file management for any directory and file type.

    Provides list, upload, download, and delete operations with
    configurable validation and post-upload actions.

    Configuration via environment variables:
    - FILE_BASE_DIR: Storage directory (default: /var/lib/files)
    - FILE_EXTENSIONS: Comma-separated allowed extensions
    """

    def __init__(
        self,
        post_upload_hook: Optional[Callable[[Path], dict]] = None,
    ):
        """
        Initialize the file manager from environment variables.

        Args:
            post_upload_hook: Optional callable invoked after successful upload
                            Takes the file path, returns a dict for the response
        """
        base_dir_str = os.environ.get('FILE_BASE_DIR', '/var/lib/files')
        self.base_dir = Path(base_dir_str)

        extensions_str = os.environ.get('FILE_EXTENSIONS', '')
        if extensions_str:
            self.extensions = set(
                ext.strip() if ext.strip().startswith('.')
                else f".{ext.strip()}"
                for ext in extensions_str.split(',')
                if ext.strip()
            )
        else:
            self.extensions = None

        self.post_upload_hook = post_upload_hook

        # Ensure directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        if self.extensions is None:
            return True
        return Path(filename).suffix.lower() in self.extensions

    def list_files(self) -> List[FileInfo]:
        """List all managed files in the directory."""
        files = []
        for file_path in self.base_dir.iterdir():
            if file_path.is_file():
                # Filter by extension if configured
                if self.extensions is None or self._validate_extension(file_path.name):
                    files.append(FileInfo(
                        name=file_path.name,
                        size=file_path.stat().st_size,
                        path=str(file_path)
                    ))
        return sorted(files, key=lambda f: f.name)

    def get_file_path(self, filename: str) -> Path:
        """Get full path for a file."""
        return self.base_dir / filename

    def validate_file(self, filename: str) -> Path:
        """Validate that file exists and return its path."""
        file_path = self.get_file_path(filename)
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File '{filename}' not found"
            )
        return file_path

    def upload_file(self, file: UploadFile) -> FileUploadResponse:
        """
        Upload a file to the managed directory.

        Validates extension (if configured) and saves the file.
        """
        if not self._validate_extension(file.filename):
            allowed = ', '.join(sorted(self.extensions)) if self.extensions else 'any'
            raise HTTPException(
                status_code=400,
                detail=f"File must have one of: {allowed}"
            )

        file_path = self.get_file_path(file.filename)

        # Read content - handle both sync and async file objects
        content = file.file.read()
        if hasattr(content, 'read'):
            # If it's still a SpooledTemporaryFile-like object
            content = content.read()

        # Write atomically using a temp file
        _, temp_path_str = tempfile.mkstemp(
            dir=self.base_dir,
            suffix='.tmp'
        )
        try:
            Path(temp_path_str).write_bytes(content)
            Path(temp_path_str).rename(file_path)
        except Exception:
            Path(temp_path_str).unlink(missing_ok=True)
            raise

        # Execute post-upload hook if configured
        action_result = None
        if self.post_upload_hook:
            action_result = self.post_upload_hook(file_path)

        return FileUploadResponse(
            status='uploaded',
            uploaded=file.filename,
            path=str(file_path),
            action_result=action_result
        )

    def delete_file(self, filename: str) -> dict:
        """Delete a file from the managed directory."""
        file_path = self.validate_file(filename)
        file_path.unlink()
        return {'status': 'deleted', 'file': filename}

    def download_file(self, filename: str):
        """Return a FileResponse for download."""
        file_path = self.validate_file(filename)
        return FileResponse(
            path=str(file_path),
            media_type='application/octet-stream',
            filename=filename
        )


# ==================== API Router Factory ====================

def create_file_router() -> APIRouter:
    """
    Create a FastAPI router with file management endpoints.

    Uses a FileManager configured from environment variables.

    Endpoints:
    - GET /all - list all files
    - POST /upload - upload file (with optional hook)
    - POST /upload/multiple - upload multiple files
    - DELETE /{filename} - delete file
    - GET /{filename} - download file

    Returns:
        APIRouter with registered endpoints
    """
    manager = FileManager()

    router = APIRouter(tags=['files'])

    @router.get('/all', response_model=List[FileInfo])
    async def list_files():
        """List all files in the managed directory."""
        return manager.list_files()

    @router.post('/upload', response_model=FileUploadResponse)
    async def upload_file(file: UploadFile = File(...)):
        """Upload a file to the managed directory."""
        return manager.upload_file(file)

    @router.post('/upload/multiple', response_model=FileUploadResponse)
    async def upload_multiple_files(files: List[UploadFile] = File(...)):
        """Upload multiple files to the managed directory."""
        # Upload all files sequentially
        uploaded_names = []
        for file in files:
            result = manager.upload_file(file)
            uploaded_names.append(result.uploaded)

        # Return info about all uploaded files
        return FileUploadResponse(
            status='uploaded',
            uploaded=', '.join(uploaded_names),
            path=str(manager.base_dir),
            action_result=None
        )

    @router.delete('/{filename}')
    async def delete_file(filename: str):
        """Delete a file from the managed directory."""
        return manager.delete_file(filename)

    @router.get('/{filename}')
    async def download_file(filename: str):
        """Download a file from the managed directory."""
        return manager.download_file(filename)

    return router


# ==================== App Export ====================

def get_app():
    """Get the FastAPI app for uvicorn to run."""
    app = FastAPI()
    app.include_router(create_file_router())
    return app


# ==================== Exports ====================

__all__ = [
    'FileManager',
    'create_file_router',
    'get_app',
    'FileInfo',
    'FileList',
    'FileUploadResponse',
]
