import os

from django.conf import settings
from django.http import FileResponse, Http404

TOC_DATA_PATH = os.path.join(settings.PROJECT_ROOT, "data", "tocs")


def serve_toc(request, filename):
    path = os.path.join(TOC_DATA_PATH, filename)
    if not os.path.exists(path):
        raise Http404
    return FileResponse(open(path, "rb"))
