import sys
import argparse
from pathlib import Path
from pydantic import ValidationError
from common.user_config import UserConfig


def main(args):
    config_dir = Path(args.config_dir)
    try:
        configs = UserConfig(config_dir=str(config_dir))
        for ingestion_config in configs.ingestion:
            print(f"  ok  {ingestion_config.source_type.value}  {ingestion_config.name}")
        print(f"\n{len(configs.ingestion)} ingestion config(s) valid.")
    except ValidationError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_dir", help="Path to configuration directory")
    main(args=parser.parse_args())
