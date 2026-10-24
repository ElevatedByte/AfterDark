"""MediaPipe adapter. The rest of the app never imports MediaPipe."""

import cv2
from app.tracking.models import map_landmarks


class MediaPipePoseTracker:
    def __init__(self, config, max_people=None):
        if not config.model_path.is_file():
            raise FileNotFoundError(
                f"Pose model missing: {config.model_path}. Run ./run.sh --setup or scripts/download_model.py while online."
            )
        import mediapipe as mp

        self.mp = mp
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(config.model_path),
                delegate=mp.tasks.BaseOptions.Delegate.CPU,
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=max_people or config.max_people,
            min_pose_detection_confidence=config.pose_confidence,
            min_pose_presence_confidence=config.pose_confidence,
            min_tracking_confidence=config.pose_confidence,
            output_segmentation_masks=config.segmentation,
        )
        self.model = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.timestamp = -1

    def detect(self, bgr, timestamp_ms):
        self.timestamp = max(self.timestamp + 1, timestamp_ms)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        result = self.model.detect_for_video(
            self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb),
            self.timestamp,
        )
        people = []
        for i, landmarks in enumerate(result.pose_landmarks):
            mask = (
                result.segmentation_masks[i].numpy_view().copy()
                if result.segmentation_masks
                else None
            )
            p = map_landmarks(landmarks, mask)
            if p is not None:
                people.append(p)
        return people

    def close(self):
        self.model.close()
