import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from contexttimer import Timer

from scaife_viewer.atlas import importers, tokenizers


class Command(BaseCommand):
    """
    Prepares the database
    """

    help = "Prepares the database"

    def emit_log(self, func_name, elapsed):
        self.stdout.write(f"Step completed: [func={func_name} elapsed={elapsed:.2f}]")

    def do_step(self, label, callback):
        with Timer() as t:
            self.stdout.write(f"--[{label}]--")
            callback()
        self.emit_log(callback.__name__, t.elapsed)

    def do_stage(self, stage):
        # NOTE: Revisit running stage callbacks in parallel in the future
        for label, callback in stage["callbacks"]:
            self.do_step(label, callback)

    def handle(self, *args, **options):
        if os.path.exists("db.sqlite3"):
            os.remove("db.sqlite3")
            self.stdout.write("--[Removed existing database]--")

        with Timer() as t:
            self.stdout.write("--[Creating database]--")
            call_command("migrate")
        self.emit_log("migrate", t.elapsed)

        self.do_step("Loading versions", importers.versions.import_versions)

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

        # NOTE: Tokenizing should never be ran in parallel, because
        # it is already parallel
        self.do_step(
            "Tokenizing versions/exemplars", tokenizers.tokenize_all_text_parts
        )

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
