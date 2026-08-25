from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.content.api.dependencies import get_content_service
from app.content.api.schemas import (
    ContentBodyPayload,
    ContentPageResponse,
    ContentResponse,
    CreateContentRequest,
    UpdateContentRequest,
)
from app.content.application.errors import ContentNotFoundError
from app.content.application.services import ContentService
from app.content.domain.body import (
    ContentBody,
    ContentBodyNotPublishableError,
    InvalidContentBodyError,
)
from app.content.domain.models import ContentImmutableError
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity

router = APIRouter(prefix="/api/v1/contents", tags=["contents"])
CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
Contents = Annotated[ContentService, Depends(get_content_service)]


def not_found(error: ContentNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Content not found")


@router.post(
    "",
    response_model=ContentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_content(
    payload: CreateContentRequest, identity: CurrentIdentity, service: Contents
) -> ContentResponse:
    return ContentResponse.from_content(service.create(identity.id, payload.type, payload.title))


@router.get("", response_model=ContentPageResponse)
def list_contents(
    identity: CurrentIdentity,
    service: Contents,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ContentPageResponse:
    result = service.list_owned(identity.id, page=page, page_size=page_size)
    return ContentPageResponse(
        items=[ContentResponse.from_content(item) for item in result.items],
        page=page,
        page_size=page_size,
        has_next=result.has_next,
    )


@router.get("/{content_id}", response_model=ContentResponse)
def get_content(content_id: UUID, identity: CurrentIdentity, service: Contents) -> ContentResponse:
    try:
        content = service.get_owned(content_id, identity.id)
    except ContentNotFoundError as error:
        raise not_found(error) from error
    return ContentResponse.from_content(content)


@router.patch(
    "/{content_id}",
    response_model=ContentResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_content(
    content_id: UUID,
    payload: UpdateContentRequest,
    identity: CurrentIdentity,
    service: Contents,
) -> ContentResponse:
    try:
        content = service.rename(content_id, identity.id, payload.title)
    except ContentNotFoundError as error:
        raise not_found(error) from error
    except ContentImmutableError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Published Content is read-only") from error
    return ContentResponse.from_content(content)


@router.post(
    "/{content_id}/publish",
    response_model=ContentResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def publish_content(
    content_id: UUID, identity: CurrentIdentity, service: Contents
) -> ContentResponse:
    try:
        content = service.publish(content_id, identity.id)
    except ContentNotFoundError as error:
        raise not_found(error) from error
    except ContentBodyNotPublishableError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Content body is not publishable") from error
    return ContentResponse.from_content(content)


@router.delete(
    "/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
def delete_content(content_id: UUID, identity: CurrentIdentity, service: Contents) -> Response:
    try:
        service.delete(content_id, identity.id)
    except ContentNotFoundError as error:
        raise not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{content_id}/body", response_model=ContentBodyPayload)
def get_content_body(
    content_id: UUID, identity: CurrentIdentity, service: Contents
) -> ContentBodyPayload:
    try:
        body = service.get_owned_body(content_id, identity.id)
    except ContentNotFoundError as error:
        raise not_found(error) from error
    return ContentBodyPayload.model_validate(body.to_dict())


@router.put(
    "/{content_id}/body",
    response_model=ContentBodyPayload,
    dependencies=[Depends(require_trusted_origin)],
)
def replace_content_body(
    content_id: UUID,
    payload: ContentBodyPayload,
    identity: CurrentIdentity,
    service: Contents,
) -> ContentBodyPayload:
    try:
        body = service.replace_owned_body(
            content_id,
            identity.id,
            ContentBody.from_dict(payload.to_dict()),
        )
    except ContentNotFoundError as error:
        raise not_found(error) from error
    except ContentImmutableError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Published Content is read-only") from error
    except InvalidContentBodyError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid Content body") from error
    return ContentBodyPayload.model_validate(body.to_dict())
