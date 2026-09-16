from pathlib import Path

import structlog
from ultralytics import YOLO

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

DEFAULT_BASE_WEIGHTS = Path("models/yolo26n.pt")
DEFAULT_EPOCHS = 50
DEFAULT_IMAGE_SIZE = 640


def run_yolo_fine_tune(
    dataset_yaml: Path,
    base_weights: Path = DEFAULT_BASE_WEIGHTS,
    epochs: int = DEFAULT_EPOCHS,
    image_size: int = DEFAULT_IMAGE_SIZE,
) -> Path:
    """Fine-tune base_weights on dataset_yaml and return the path to the best checkpoint."""
    with log_call(
        logger, "run_yolo_fine_tune", dataset_yaml=str(dataset_yaml), base_weights=str(base_weights), epochs=epochs, image_size=image_size
    ):
        model = YOLO(base_weights)
        results = model.train(data=str(dataset_yaml), epochs=epochs, imgsz=image_size)
        best_weights_path = Path(results.save_dir) / "weights" / "best.pt"
        logger.info("yolo_fine_tune_finished", best_weights=str(best_weights_path))
    return best_weights_path
