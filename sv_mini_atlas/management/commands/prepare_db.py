import os
from concurrent.futures import ProcessPoolExecutor as PreferredExecutor

from django.core.management import call_command
from django.core.management.base import BaseCommand

from contexttimer import Timer

from scaife_viewer.atlas import importers, tokenizers
# @@@ parallel ingestion
# from scaife_viewer.atlas.conf import settings


# @@@ better way to alias this from our conf module?
# WORKER_COUNT = settings.SCAIFE_VIEWER_ATLAS_INGESTION_CONCURRENCY
WORKER_COUNT = None


class Command(BaseCommand):
    """
    Prepares the database
    """

    help = "Prepares the database"

    def handle(self, *args, **options):
        if os.path.exists("db.sqlite3"):
            os.remove("db.sqlite3")
            self.stdout.write("--[Removed existing database]--")

        with Timer() as t:
            self.stdout.write("--[Creating database]--")
            call_command("migrate")
        print(t.elapsed)

        with Timer() as t:
            self.stdout.write("--[Loading versions]--")
            importers.versions.import_versions(reset=True)
        print(f"{t.elapsed}")

        async_stages_1 = [
            # ("Loading alignments", importers.alignments.import_alignments),
            (
                "Loading text annotations",
                importers.text_annotations.import_text_annotations,
            ),
            (
                "Loading metrical annotations",
                importers.metrical_annotations.import_metrical_annotations,
            ),
            (
                "Loading image annotations",
                importers.image_annotations.import_image_annotations,
            ),
            (
                "Loading audio annotations",
                importers.audio_annotations.import_audio_annotations,
            ),
        ]
        with Timer() as t:
            with PreferredExecutor(max_workers=WORKER_COUNT) as executor:
                for msg, stage in async_stages_1:
                    print(f"--[{msg}]--")
                    executor.submit(stage)
        print(f"async_stages_1 {t.elapsed}")

        with Timer() as t:
            self.stdout.write("--[Tokenizing versions/exemplars]--")
            tokenizers.tokenize_all_text_parts(reset=True)
        print(f"tokenizers ran {t.elapsed}")

        async_stages_2 = [
            (
                "Loading token annotations",
                importers.token_annotations.apply_token_annotations,
            ),
            (
                "Loading named entity annotations",
                importers.named_entities.apply_named_entities,
            ),
        ]
        with Timer() as t:
            with PreferredExecutor(max_workers=WORKER_COUNT) as executor:
                for msg, stage in async_stages_2:
                    print(f"--[{msg}]--")
                    executor.submit(stage)
        print(f"stage2 {t.elapsed}")

        # @@@
        importers.alignments.process_alignments(reset=True)
