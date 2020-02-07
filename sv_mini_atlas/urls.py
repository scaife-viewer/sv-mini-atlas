from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from django.contrib import admin

from graphene_django.views import GraphQLView

from .tocs.views import serve_toc


urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path("tocs/<filename>", serve_toc)
]
