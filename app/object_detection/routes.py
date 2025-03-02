from typing import Annotated
from fastapi import APIRouter, File, Depends, HTTPException, status
from fastapi.params import Depends
from fastapi.responses import StreamingResponse
from app.object_detection.services import YoloServices
from app.auth.dependencies import AccessTokenBearer, RoleChecker
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.object_detection.schemas import UserHistoryModel, AdminReadData
import json
import uuid
from loguru import logger


yolo_router = APIRouter()
yolo_services = YoloServices()
access_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(["admin", "user"]))
role_checker_admin = Depends(RoleChecker(["admin"]))


@yolo_router.post("/detection", dependencies=[role_checker])
def predict(
    file: bytes = File(...),
    _: dict = Depends(access_token_bearer),
):
    # Step 1: Initialize the result dictionary with None values.
    result = {"detection_objects": None}

    # Step 2: Convert the image file to an image object
    input_image = yolo_services.get_image_from_bytes(file)

    # Step 3: Predict from model
    predict = yolo_services.detect_sample_model(input_image)

    # Step 4: Select detect obj return info
    # here you can choose what data to send to the result
    detect_res = predict[["name", "confidence"]]
    objects = detect_res["name"].values

    result["detect_objects_names"] = ", ".join(objects)
    result["detection_objects"] = json.loads(detect_res.to_json(orient="records"))
    result["total_detected_objects"] = len(predict)
    # Step 5: Logs and return
    logger.info("results: {}", result)
    return result


@yolo_router.post("/img_object_detection_to_img", dependencies=[role_checker])
async def img_object_detection_to_img(
    file: Annotated[bytes, File()],
    sample_name: str,
    _: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
):

    input_image = yolo_services.get_image_from_bytes(file)

    # model predict
    predict = yolo_services.detect_sample_model(input_image)

    total_objects = len(predict)
    user_data = _.get("user", {})
    user_id = uuid.UUID(user_data.get("user_id"))

    new_predict = await yolo_services.save_yolo_output(
        user_id=user_id,
        total_objects=total_objects,
        sample_name=sample_name,
        session=session,
    )

    if new_predict.total_objects == 0:
        raise HTTPException(
            status_code=404,
            detail="No target detected or image out of training scope. Try another image.",
        )

    # add bbox on image
    final_image = yolo_services.add_bbox_on_img(image=input_image, predict=predict)

    # return image in bytes format
    return StreamingResponse(
        content=yolo_services.get_bytes_from_image(final_image), media_type="image/jpeg"
    )


@yolo_router.get(
    "/get_data_admin",
    dependencies=[role_checker_admin],
    response_model=list[AdminReadData],
)
async def read_data_admin(
    session: AsyncSession = Depends(get_session), _: dict = Depends(access_token_bearer)
):
    data = await yolo_services.get_history_admin(session)
    return data


@yolo_router.get(
    "/get_data_user", dependencies=[role_checker], response_model=list[UserHistoryModel]
)
async def read_data_user(
    session: AsyncSession = Depends(get_session), _: dict = Depends(access_token_bearer)
):
    user_data = _.get("user", {})
    email = user_data.get("email")
    data = await yolo_services.get_history_user(email, session)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No data available."
        )
    return data
