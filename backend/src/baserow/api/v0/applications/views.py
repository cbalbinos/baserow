from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes

from baserow.api.v0.decorators import validate_body, map_exceptions
from baserow.api.v0.errors import ERROR_USER_NOT_IN_GROUP
from baserow.api.v0.schemas import get_error_schema
from baserow.api.v0.utils import PolymorphicMappingSerializer
from baserow.core.models import Group, Application
from baserow.core.handler import CoreHandler
from baserow.core.exceptions import UserNotInGroupError
from baserow.core.registries import application_type_registry

from .serializers import (
    ApplicationCreateSerializer, ApplicationUpdateSerializer, get_application_serializer
)


application_type_serializers = {
    application_type.type: application_type.instance_serializer_class
    for application_type in application_type_registry.registry.values()
}


class AllApplicationsView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=['Applications'],
        operation_id='list_all_applications',
        description=(
            'Lists all the applications that the authorized user has access to. The '
            'properties that belong to the application can differ per type. An '
            'application always belongs to a single group. All the applications of the '
            'groups that the user has access to are going to be listed here.'
        ),
        responses={
            200: PolymorphicMappingSerializer(
                'Applications',
                application_type_serializers,
                many=True
            ),
            400: get_error_schema(['ERROR_USER_NOT_IN_GROUP'])
        }
    )
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def get(self, request):
        """
        Responds with a list of serialized applications that belong to the user. If a
        group id is provided only the applications of that group are going to be
        returned.
        """

        applications = Application.objects.select_related(
            'content_type', 'group'
        ).filter(
            group__users__in=[request.user]
        )

        data = [
            get_application_serializer(application).data
            for application in applications
        ]
        return Response(data)


class ApplicationsView(APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get_group(request, group_id):
        group = get_object_or_404(
            Group,
            id=group_id
        )

        if not group.has_user(request.user):
            raise UserNotInGroupError(request.user, group)

        return group

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='group_id',
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description='Returns only applications that are in the group related '
                            'to the provided value.'
            )
        ],
        tags=['Applications'],
        operation_id='list_applications',
        description=(
            'Lists all the applications of the group related to the provided '
            '`group_id` parameter if the authorized user is in that group. The '
            'properties that belong to the application can differ per type. An '
            'application always belongs to a single group.'
        ),
        responses={
            200: PolymorphicMappingSerializer(
                'Applications',
                application_type_serializers,
                many=True
            ),
            400: get_error_schema(['ERROR_USER_NOT_IN_GROUP'])
        }
    )
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def get(self, request, group_id):
        """
        Responds with a list of serialized applications that belong to the user. If a
        group id is provided only the applications of that group are going to be
        returned.
        """

        applications = Application.objects.select_related('content_type', 'group')
        group = self.get_group(request, group_id)
        applications = applications.filter(group=group)

        data = [
            get_application_serializer(application).data
            for application in applications
        ]
        return Response(data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='group_id',
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description='Creates an application for the group related to the '
                            'provided value.'
            )
        ],
        tags=['Applications'],
        operation_id='create_application',
        description=(
            'Creates a new application based on the provided type. The newly created '
            'application is going to be added to the group related to the provided '
            '`group_id` parameter. If the authorized user does not belong to the group '
            'an error will be returned.'
        ),
        request=ApplicationCreateSerializer,
        responses={
            200: PolymorphicMappingSerializer(
                'Applications',
                application_type_serializers
            ),
            400: get_error_schema([
                'ERROR_USER_NOT_IN_GROUP', 'ERROR_REQUEST_BODY_VALIDATION'
            ])
        },
    )
    @transaction.atomic
    @validate_body(ApplicationCreateSerializer)
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def post(self, request, data, group_id):
        """Creates a new application for a user."""

        group = self.get_group(request, group_id)
        application = CoreHandler().create_application(
            request.user, group, data['type'], name=data['name'])

        return Response(get_application_serializer(application).data)


class ApplicationView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='application_id',
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description='Returns the application related to the provided value.'
            )
        ],
        tags=['Applications'],
        operation_id='get_application',
        description=(
            'Returns the requested application if the authorized user is in the '
            'application\'s group. The properties that belong to the application can '
            'differ per type.'
        ),
        request=ApplicationCreateSerializer,
        responses={
            200: PolymorphicMappingSerializer(
                'Applications',
                application_type_serializers
            ),
            400: get_error_schema([
                'ERROR_USER_NOT_IN_GROUP', 'ERROR_REQUEST_BODY_VALIDATION'
            ])
        },
    )
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def get(self, request, application_id):
        """Selects a single application and responds with a serialized version."""

        application = get_object_or_404(
            Application.objects.select_related('content_type', 'group'),
            pk=application_id
        )

        if not application.group.has_user(request.user):
            raise UserNotInGroupError(request.user, application.group)

        return Response(get_application_serializer(application).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='application_id',
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description='Updates the application related to the provided value.'
            )
        ],
        tags=['Applications'],
        operation_id='update_application',
        description=(
            'Updates the existing application related to the provided '
            '`application_id` param if the authorized user is in the application\'s '
            'group. It is not possible to change the type, but properties like the '
            'name can be changed.'
        ),
        request=ApplicationUpdateSerializer,
        responses={
            200: PolymorphicMappingSerializer(
                'Applications',
                application_type_serializers
            ),
            400: get_error_schema([
                'ERROR_USER_NOT_IN_GROUP', 'ERROR_REQUEST_BODY_VALIDATION'
            ])
        },
    )
    @transaction.atomic
    @validate_body(ApplicationUpdateSerializer)
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def patch(self, request, data, application_id):
        """Updates the application if the user belongs to the group."""

        application = get_object_or_404(
            Application.objects.select_related('group').select_for_update(),
            pk=application_id
        )
        application = CoreHandler().update_application(
            request.user, application, name=data['name'])

        return Response(get_application_serializer(application).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='application_id',
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description='Deletes the application related to the provided value.'
            )
        ],
        tags=['Applications'],
        operation_id='delete_application',
        description=(
            'Deletes an application if the authorized user is in the application\'s '
            'group. All the related children are also going to be deleted. For example '
            'in case of a database application all the underlying tables, fields, '
            'views and rows are going to be deleted.'
        ),
        responses={
            204: None,
            400: get_error_schema(['ERROR_USER_NOT_IN_GROUP'])
        },
    )
    @transaction.atomic
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def delete(self, request, application_id):
        """Deletes an existing application if the user belongs to the group."""

        application = get_object_or_404(
            Application.objects.select_related('group'),
            pk=application_id
        )
        CoreHandler().delete_application(request.user, application)

        return Response(status=204)
