"""
Face Detection Module (ONNX-Direct)
====================================
Uses RetinaFace ONNX model directly via onnxruntime, without the
insightface Python package. Downloads models automatically on first run.
"""

import cv2
import numpy as np
import yaml
import os
import urllib.request
import zipfile
from pathlib import Path


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "configs" / "default.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def apply_clahe(image: np.ndarray, clip_limit: float = 2.0,
                grid_size: tuple = (8, 8)) -> np.ndarray:
    """Apply CLAHE on the luminance channel to normalize uneven lighting."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    l_channel = clahe.apply(l_channel)
    lab = cv2.merge([l_channel, a_channel, b_channel])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def preprocess_image(image: np.ndarray, config: dict) -> tuple:
    """Preprocess the classroom image: CLAHE + resize if needed."""
    prep_cfg = config.get("preprocessing", {})

    if prep_cfg.get("apply_clahe", True):
        image = apply_clahe(
            image,
            clip_limit=prep_cfg.get("clahe_clip_limit", 2.0),
            grid_size=tuple(prep_cfg.get("clahe_grid_size", [8, 8]))
        )

    max_dim = prep_cfg.get("max_image_dim", 1920)
    h, w = image.shape[:2]
    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    return image, scale


def _download_models(model_dir: Path):
    """Download the InsightFace buffalo_l model pack if not present."""
    model_dir.mkdir(parents=True, exist_ok=True)
    det_path = model_dir / "det_10g.onnx"
    rec_path = model_dir / "w600k_r50.onnx"

    if det_path.exists() and rec_path.exists():
        return str(det_path), str(rec_path)

    print("[INFO] Downloading face detection & recognition models (first run only)...")
    zip_url = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
    zip_path = model_dir / "buffalo_l.zip"

    try:
        urllib.request.urlretrieve(zip_url, str(zip_path))
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            zf.extractall(str(model_dir))
        if zip_path.exists():
            os.remove(str(zip_path))
        print("[INFO] Models downloaded successfully.")
    except Exception as e:
        print(f"[WARN] Auto-download failed: {e}")
        print(f"Please manually download models and place them in: {model_dir}")
        print(f"  Detection model: {det_path}")
        print(f"  Recognition model: {rec_path}")
        print(f"  Download from: {zip_url}")
        raise FileNotFoundError(
            f"Models not found at {model_dir}. See instructions above."
        )

    return str(det_path), str(rec_path)


def _nms(dets: np.ndarray, threshold: float) -> list:
    """Non-maximum suppression on detection boxes."""
    if len(dets) == 0:
        return []

    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(iou <= threshold)[0]
        order = order[inds + 1]

    return keep


def _distance2bbox(points, distance):
    x1 = points[:, 0] - distance[:, 0]
    y1 = points[:, 1] - distance[:, 1]
    x2 = points[:, 0] + distance[:, 2]
    y2 = points[:, 1] + distance[:, 3]
    return np.stack([x1, y1, x2, y2], axis=-1)


def _distance2kps(points, distance):
    num_points = distance.shape[1] // 2
    result = []
    for i in range(num_points):
        px = points[:, 0] + distance[:, 2 * i]
        py = points[:, 1] + distance[:, 2 * i + 1]
        result.append(px)
        result.append(py)
    return np.stack(result, axis=-1)


class FaceDetector:
    """Face detector using RetinaFace ONNX model via onnxruntime.

    Also includes the ArcFace recognition model for embedding extraction.
    Both models are loaded from ONNX files directly.
    """

    def __init__(self, config: dict = None):
        if config is None:
            config = load_config()
        self.config = config
        self.det_cfg = config.get("detection", {})
        self._det_session = None
        self._rec_session = None
        self._det_input_size = tuple(self.det_cfg.get("input_size", [640, 640]))

        # Model paths
        model_dir = Path(__file__).parent.parent / "models" / "buffalo_l"
        self._model_dir = model_dir
        self._det_path = None
        self._rec_path = None

    def _load_models(self):
        """Load ONNX models."""
        import onnxruntime as ort

        self._det_path, self._rec_path = _download_models(self._model_dir)

        providers = ['CPUExecutionProvider']
        try:
            available = ort.get_available_providers()
            if 'CUDAExecutionProvider' in available:
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        except:
            pass

        self._det_session = ort.InferenceSession(self._det_path, providers=providers)
        self._rec_session = ort.InferenceSession(self._rec_path, providers=providers)
        print(f"[INFO] Models loaded (providers: {providers})")

    @property
    def det_session(self):
        if self._det_session is None:
            self._load_models()
        return self._det_session

    @property
    def rec_session(self):
        if self._rec_session is None:
            self._load_models()
        return self._rec_session

    def _preprocess_det(self, image: np.ndarray):
        """Preprocess image for detection model."""
        input_h, input_w = self._det_input_size
        img_h, img_w = image.shape[:2]

        # Compute scale to fit within input_size maintaining aspect ratio
        scale = min(input_w / img_w, input_h / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        resized = cv2.resize(image, (new_w, new_h))

        # Pad to input_size
        padded = np.zeros((input_h, input_w, 3), dtype=np.uint8)
        padded[:new_h, :new_w, :] = resized

        # Normalize: (img - 127.5) / 128.0
        blob = (padded.astype(np.float32) - 127.5) / 128.0
        blob = blob.transpose(2, 0, 1)  # HWC -> CHW
        blob = np.expand_dims(blob, axis=0)  # Add batch dim

        return blob, scale

    def _decode_detections(self, outputs, scale: float, img_shape: tuple):
        """Decode detection model outputs to bboxes + landmarks."""
        fmc = 3  # feature map count
        feat_stride_fpn = [8, 16, 32]
        num_anchors = 2
        det_thresh = self.det_cfg.get("det_thresh", 0.5)
        nms_thresh = self.det_cfg.get("nms_thresh", 0.4)

        input_h, input_w = self._det_input_size
        all_dets = []
        all_kpss = []

        for idx, stride in enumerate(feat_stride_fpn):
            # Output order: scores, bboxes, kps for each stride
            scores = outputs[idx]          # (1, num_anchors*h*w, 1)
            bbox_deltas = outputs[idx + fmc]  # (1, num_anchors*h*w, 4)
            kps_deltas = outputs[idx + fmc * 2]  # (1, num_anchors*h*w, 10)

            scores = scores.reshape(-1)
            bbox_deltas = bbox_deltas.reshape(-1, 4)
            kps_deltas = kps_deltas.reshape(-1, 10)

            height = input_h // stride
            width = input_w // stride

            # Generate anchor centers
            y, x = np.mgrid[:height, :width]
            anchor_centers = np.stack([x, y], axis=-1).reshape(-1, 2)
            anchor_centers = (anchor_centers * stride).astype(np.float32)

            if num_anchors > 1:
                anchor_centers = np.stack([anchor_centers] * num_anchors, axis=1).reshape(-1, 2)

            # Filter by score
            pos_inds = np.where(scores >= det_thresh)[0]
            if len(pos_inds) == 0:
                continue

            scores_filt = scores[pos_inds]
            bbox_deltas_filt = bbox_deltas[pos_inds] * stride
            kps_deltas_filt = kps_deltas[pos_inds] * stride
            anchor_centers_filt = anchor_centers[pos_inds]

            bboxes = _distance2bbox(anchor_centers_filt, bbox_deltas_filt)
            kpss = _distance2kps(anchor_centers_filt, kps_deltas_filt)
            kpss = kpss.reshape(-1, 5, 2)

            # Scale back to original image
            bboxes /= scale
            kpss /= scale

            dets = np.hstack([bboxes, scores_filt.reshape(-1, 1)])
            all_dets.append(dets)
            all_kpss.append(kpss)

        if not all_dets:
            return [], []

        all_dets = np.concatenate(all_dets, axis=0)
        all_kpss = np.concatenate(all_kpss, axis=0)

        # NMS
        keep = _nms(all_dets, nms_thresh)
        all_dets = all_dets[keep]
        all_kpss = all_kpss[keep]

        return all_dets, all_kpss

    def _get_embedding(self, aligned_face: np.ndarray) -> np.ndarray:
        """Get face embedding from aligned 112x112 face chip."""
        # Preprocess for recognition model
        blob = (aligned_face.astype(np.float32) - 127.5) / 127.5
        blob = blob.transpose(2, 0, 1)  # HWC -> CHW
        blob = np.expand_dims(blob, axis=0)

        input_name = self.rec_session.get_inputs()[0].name
        output = self.rec_session.run(None, {input_name: blob})
        embedding = output[0].flatten()

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 1e-10:
            embedding = embedding / norm
        return embedding

    def _align_face(self, image: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        """Align face using 5-point landmarks to 112x112."""
        from .alignment import align_face
        return align_face(image, landmarks, output_size=(112, 112))

    def detect(self, image: np.ndarray) -> list:
        """Detect all faces and extract embeddings.

        Returns:
            List of detection dicts with bbox, confidence, landmarks, and embedding.
        """
        blob, scale = self._preprocess_det(image)

        input_name = self.det_session.get_inputs()[0].name
        outputs = self.det_session.run(None, {input_name: blob})

        all_dets, all_kpss = self._decode_detections(outputs, scale, image.shape)

        min_face = self.det_cfg.get("min_face_size", 20)
        detections = []

        for i in range(len(all_dets)):
            bbox = all_dets[i, :4].astype(int).tolist()
            confidence = float(all_dets[i, 4])
            landmarks = all_kpss[i] if len(all_kpss) > 0 else None

            face_width = bbox[2] - bbox[0]
            face_height = bbox[3] - bbox[1]
            if face_width < min_face or face_height < min_face:
                continue

            # Get embedding via alignment + recognition model
            embedding = None
            if landmarks is not None:
                aligned = self._align_face(image, landmarks)
                if aligned is not None:
                    embedding = self._get_embedding(aligned)

            det = {
                "bbox": bbox,
                "confidence": confidence,
                "landmarks": landmarks.tolist() if landmarks is not None else None,
                "face_size": face_width,
                "embedding": embedding,
            }
            detections.append(det)

        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections

    def detect_with_preprocessing(self, image: np.ndarray) -> tuple:
        """Full detection pipeline: preprocess + detect.

        Returns:
            (detections, preprocessed_image, scale_factor)
        """
        preprocessed, scale = preprocess_image(image, self.config)
        detections = self.detect(preprocessed)

        # Scale coordinates back to original if the preprocessor resized
        if scale != 1.0:
            inv_scale = 1.0 / scale
            for det in detections:
                det["bbox"] = [int(c * inv_scale) for c in det["bbox"]]
                det["face_size"] = int(det["face_size"] * inv_scale)
                if det["landmarks"] is not None:
                    det["landmarks"] = [
                        [p[0] * inv_scale, p[1] * inv_scale]
                        for p in det["landmarks"]
                    ]

        return detections, preprocessed, scale
