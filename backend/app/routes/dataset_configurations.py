"""HTTP routes for saving, sharing and reusing dataset configurations.

Every endpoint is scoped by team: a configuration saved into a team is
listed and reproducible by anyone acting for that team, and is invisible
from other teams' scope.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dataset_configurations.service import (
    DatasetConfigurationReplayRefused,
    DatasetConfigurationsService,
    InvalidDatasetConfiguration,
)
from app.settings import Settings
from app.storage.repository import DuplicateDatasetConfiguration

SAVED_STATUS_CODE = 201
CONFLICT_STATUS_CODE = 409
NOT_FOUND_STATUS_CODE = 404
UNPROCESSABLE_STATUS_CODE = 422


class SaveDatasetConfigurationRequest(BaseModel):
    """The payload of a save request."""

    name: str = Field(min_length=1)
    count: int = Field(ge=0)
    seed: int
    configuration: dict


def _refusal_as_http(status_code: int, refused: Exception) -> HTTPException:
    """Carry what a domain refusal said into the HTTP response."""

    return HTTPException(status_code=status_code, detail=str(refused))


def build_dataset_configurations_router(settings: Settings) -> APIRouter:
    """Build the router bound to one application's settings."""

    router = APIRouter(prefix="/api")
    the_service = _service_bound_to(settings)

    @router.put(
        "/teams/{team}/dataset-configurations",
        status_code=SAVED_STATUS_CODE,
    )
    def save_configuration(
        team: str,
        request: SaveDatasetConfigurationRequest,
        service: DatasetConfigurationsService = Depends(the_service),
    ) -> dict:
        try:
            service.save(
                team, request.name, request.configuration, request.count, request.seed
            )
        except DuplicateDatasetConfiguration as refused:
            raise _refusal_as_http(CONFLICT_STATUS_CODE, refused) from refused
        except InvalidDatasetConfiguration as refused:
            raise _refusal_as_http(UNPROCESSABLE_STATUS_CODE, refused) from refused
        return {"name": request.name, "team": team}

    @router.get("/teams/{team}/dataset-configurations")
    def list_dataset_configurations(
        team: str,
        service: DatasetConfigurationsService = Depends(the_service),
    ) -> list[dict]:
        return service.list_in_team(team)

    _read_routes_of(router, the_service)
    return router


def _read_routes_of(
    router: APIRouter, the_service
) -> None:
    """Read routes are declared so /reproduce never reads as a name."""

    @router.get("/teams/{team}/dataset-configurations/{name}/reproduce")
    def reproduce_dataset_configuration(
        team: str,
        name: str,
        service: DatasetConfigurationsService = Depends(the_service),
    ) -> dict:
        try:
            return service.reproduce(team, name)
        except LookupError as missing:
            raise _refusal_as_http(NOT_FOUND_STATUS_CODE, missing) from missing
        except DatasetConfigurationReplayRefused as refused:
            raise _refusal_as_http(CONFLICT_STATUS_CODE, refused) from refused

    @router.get("/teams/{team}/dataset-configurations/{name}")
    def read_dataset_configuration(
        team: str,
        name: str,
        service: DatasetConfigurationsService = Depends(the_service),
    ) -> dict:
        try:
            return service.describe(team, name)
        except LookupError as missing:
            raise _refusal_as_http(NOT_FOUND_STATUS_CODE, missing) from missing


def _service_bound_to(settings: Settings):
    """Build the service lazily so configuration problems surface on use."""

    the_service: list[DatasetConfigurationsService | None] = [None]

    def provide_service() -> DatasetConfigurationsService:
        if the_service[0] is None:
            the_service[0] = DatasetConfigurationsService.build_for(settings)
        return the_service[0]

    return provide_service
