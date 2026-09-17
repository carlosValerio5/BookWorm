from pathlib import Path

import structlog
import yaml

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

ARGS_YAML_NAME = "args.yaml"
TRAINING_PARAM_KEYS = ("model", "data", "epochs", "batch", "imgsz", "optimizer", "lr0")


def read_training_params(run_dir: Path) -> dict[str, str | int | float]:
    args_path = run_dir / ARGS_YAML_NAME
    if not args_path.is_file():
        return {}
    with log_call(logger, "read_training_params", args_path=str(args_path)):
        args = yaml.safe_load(args_path.read_text(encoding="utf-8")) or {}
        return {key: args[key] for key in TRAINING_PARAM_KEYS if key in args}
