from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import assets, characters, projects
from .repositories.errors import ConflictError, NotFoundError, RepositoryError
from .routers import app_router, workflow_router
from .services.errors import (
    AssetFileMissingError,
    ServiceValidationError,
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)

# Load environment variables from .env file
# The .env file is located in the server/ directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Circus Portraits API", version="1.0.0")

app.include_router(workflow_router.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(app_router.router, prefix="/api/app", tags=["app"])
app.include_router(projects.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(assets.router, prefix="/api")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
async def not_found_handler(_request: Request, error: NotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(error)},
    )


@app.exception_handler(ConflictError)
async def conflict_handler(_request: Request, error: ConflictError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(error)},
    )


@app.exception_handler(ServiceValidationError)
async def service_validation_handler(
    _request: Request, error: ServiceValidationError
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(error)},
    )


@app.exception_handler(RepositoryError)
async def repository_error_handler(_request: Request, _error: RepositoryError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Les donnees locales n'ont pas pu etre lues."},
    )


@app.exception_handler(UnsupportedMediaTypeError)
async def unsupported_media_handler(
    _request: Request, error: UnsupportedMediaTypeError
):
    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content={"detail": str(error)},
    )


@app.exception_handler(UploadTooLargeError)
async def upload_too_large_handler(_request: Request, error: UploadTooLargeError):
    return JSONResponse(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        content={"detail": str(error)},
    )


@app.exception_handler(AssetFileMissingError)
async def asset_file_missing_handler(
    _request: Request, error: AssetFileMissingError
):
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "code": "asset_file_missing",
            "detail": str(error),
            "asset_id": str(error.asset_id),
            "variant": error.variant,
        },
    )


@app.get("/")
async def root():
    return {"message": "Welcome to Workflow API"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
