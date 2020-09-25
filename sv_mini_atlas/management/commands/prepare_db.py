import concurrent.futures
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from contexttimer import Timer

from scaife_viewer.atlas import importers, tokenizers
from scaife_viewer.atlas.conf import settings


WORKER_COUNT = settings.SCAIFE_VIEWER_ATLAS_INGESTION_CONCURRENCY


class Command(BaseCommand):
    """
    Prepares the database
    """

    help = "Prepares the database"

    def do_stage(self, stage):
        exceptions = False
        with Timer() as t:
            fs = {}
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=WORKER_COUNT
            ) as executor:
                for msg, callback in stage["callbacks"]:
                    print(f"--[{msg}]--")
                    fs[executor.submit(callback)] = msg
            for f in concurrent.futures.as_completed(fs):
                msg = fs[f]
                try:
                    f.result()
                except Exception as exc:
                    exceptions = True
                    print("{} generated an exception: {}".format(msg, exc))
        print(f"{stage['name']} {t.elapsed}")

        if exceptions:
            raise AssertionError(
                f"Exceptions were encountered in running {stage['name']}"
            )

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

        stage_1 = {
            "name": "stage 1",
            "callbacks": [
                ("Loading alignments", importers.alignments.import_alignments),
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
            ],
        }
        self.do_stage(stage_1)

        with Timer() as t:
            self.stdout.write("--[Tokenizing versions/exemplars]--")
            tokenizers.tokenize_all_text_parts(reset=True)
        print(f"tokenizers ran {t.elapsed}")

        stage_2 = {
            "name": "stage 2",
            "callbacks": [
                (
                    "Loading token annotations",
                    importers.token_annotations.apply_token_annotations,
                ),
                (
                    "Loading named entity annotations",
                    importers.named_entities.apply_named_entities,
                ),
            ],
        }
        self.do_stage(stage_2)
