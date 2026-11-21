"""Retreina a rede agora com as autoavaliações reais: `make retrain` (stack no ar).

O worker também retreina sozinho, de hora em hora (ADR-0012).
"""

import argparse
import asyncio

from developer_myself.composition.mongo import build_mongo_container
from developer_myself.shared.settings import Settings


async def main(force: bool) -> None:

    container = await build_mongo_container(Settings())
    try:
        report = await container.retrain_job.run_once(force=force)
        print(f"status: {report.status} — {report.reason}")
        print(f"revisões rotuladas: {report.labeled_reviews}")
        for key, value in report.metrics.items():
            print(f"  {key}: {value}")
    finally:
        await container.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retreina a rede com os rótulos reais.")
    parser.add_argument("--force", action="store_true", help="retreina mesmo sem rótulos novos")
    asyncio.run(main(parser.parse_args().force))
