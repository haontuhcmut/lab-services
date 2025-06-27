from PIL import Image
import uuid
import io
import pandas as pd
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors
from app.config import Config
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.models import YoloOutput, User
from sqlmodel import select

class PreprocessingImageInputService:
    def __init__(self, image: bytes) -> None:
        pass

class YoloServices:
    def __init__(self):
        self.model = YOLO(Config.MODEL_PATH)

    def get_image_from_bytes(self, binary_image: bytes) -> Image:

        input_image = Image.open(io.BytesIO(binary_image)).convert("RGB")
        return input_image

    def get_bytes_from_image(self, image: Image) -> bytes:

        return_image = io.BytesIO()
        image.save(
            return_image, format="JPEG", quality=85
        )  # save the image in JPEG format with quality 85
        return_image.seek(0)  # set the pointer to the beginning of the file
        return return_image

    def transform_predict_to_df(self, results: list, labeles_dict=dict) -> pd.DataFrame:

        # Transform the Tensor to numpy array
        predict_bbox = pd.DataFrame(
            results[0].to("cpu").numpy().boxes.xyxy,
            columns=["xmin", "ymin", "xmax", "ymax"],
        )
        # Add the confidence of the prediction to the DataFrame
        predict_bbox["confidence"] = results[0].to("cpu").numpy().boxes.conf
        # Add the class of the prediction to the DataFrame
        predict_bbox["class"] = (results[0].to("cpu").numpy().boxes.cls).astype(int)
        # Replace the class number with the class name from the labeles_dict
        predict_bbox["name"] = predict_bbox["class"].replace(labeles_dict)
        return predict_bbox

    def get_model_predict(
        self,
        model: YOLO,
        input_image: Image,
        save: bool = False,
        image_size: int = 1248,
        conf: float = 0.5,
        augment: bool = False,
        **kwargs,
    ) -> pd.DataFrame:

        # Make predictions
        predicts = model.predict(
            input_image,
            imgsz=image_size,
            conf=conf,
            save=save,
            augment=augment,
            flipud=0.0,
            fliplr=0.0,
            mosaic=0.0,
            **kwargs,
        )
        # Transform predictions to pandas dataframe
        predictions = self.transform_predict_to_df(predicts, model.names)
        return predictions

    def detect_sample_model(self, input_image: Image) -> pd.DataFrame:

        predict = self.get_model_predict(
            model=self.model,
            input_image=input_image,
            save=False,
            image_size=640,
            augment=True,
            conf=0.5,
        )
        return predict

    def add_bbox_on_img(self, image: Image, predict: pd.DataFrame()) -> Image:

        # Create an annotator object
        annotator = Annotator(np.array(image))

        # sort predict by xmin value
        predict = predict.sort_values(by=["xmin"], ascending=True)

        # iterate over the rows of predict dataframe
        for i, row in predict.iterrows():
            # create the text to be displayed on image
            # text = f"{row['name']}: {int(row['confidence']*100)}%"
            # get the bounding box coordinates
            bbox = [row["xmin"], row["ymin"], row["xmax"], row["ymax"]]
            # add the bounding box and text on the image
            annotator.box_label(
                bbox,
                # text,
                color=colors(row["class"], True),
            )
            # Total obj by Annotator.text()
            count_obj = len(predict)
            annotator.text(
                (30, 100),  # area (x, y)
                f"Total Objects: {count_obj}",  # text
                txt_color=(255, 255, 255),  # text color (white)
            )
        # convert the annotated image to PIL image
        return Image.fromarray(annotator.result())

    async def save_yolo_output(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        total_objects: int,
        sample_name: str,
    ):
        yolo_output = YoloOutput(
            user_id=user_id, total_objects=total_objects, sample_name=sample_name
        )
        session.add(yolo_output)
        await session.commit()
        await session.refresh(yolo_output)
        return yolo_output

    async def get_history_admin(self, session: AsyncSession):
        statement = select(
            User.username,
            User.email,
            YoloOutput.sample_name,
            YoloOutput.total_objects,
            YoloOutput.created_at,
        ).join(User, YoloOutput.user_id == User.uid)

        results = await session.exec(statement)
        data = results.all()
        return data

    async def get_history_user(self, email: str, session: AsyncSession):
        user_statement = select(User).where(User.email == email)
        result_user = await session.exec(user_statement)
        user = result_user.first()

        if not user:
            return None

        statement_main = select(YoloOutput).where(YoloOutput.user_id == user.uid)
        results_main = await session.exec(statement_main)
        data = results_main.all()

        return data
