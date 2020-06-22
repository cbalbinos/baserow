from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema
from drf_spectacular.plumbing import build_array_type
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes

from baserow.api.v0.decorators import validate_body, map_exceptions
from baserow.api.v0.errors import ERROR_USER_NOT_IN_GROUP
from baserow.api.v0.schemas import get_error_schema
from baserow.core.models import Group, GroupUser
from baserow.core.handler import CoreHandler
from baserow.core.exceptions import UserNotInGroupError

from .serializers import GroupSerializer, GroupUserSerializer, OrderGroupsSerializer
from .schemas import group_user_schema


class GroupsView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=['Groups'],
        operation_id='list_groups',
        description=(
            'Lists all the groups of the authorized user. A group can contain '
            'multiple applications like a database. Multiple users can have '
            'access to a group. For example each company could have their own group '
            'containing databases related to that company. The order of the groups '
            'are custom for each user. The order is configurable via the '
            '**order_groups** endpoint.'
        ),
        responses={
            200: build_array_type(group_user_schema)
        }
    )
    def get(self, request):
        """Responds with a list of serialized groups where the user is part of."""

        groups = GroupUser.objects.filter(user=request.user).select_related('group')
        serializer = GroupUserSerializer(groups, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Groups'],
        operation_id='create_group',
        description=(
            'Creates a new group where only the authorized user has access to. No '
            'initial data like database applications are added, they have to be '
            'created via other endpoints.'
        ),
        request=GroupSerializer,
        responses={
            200: group_user_schema
        }
    )
    @transaction.atomic
    @validate_body(GroupSerializer)
    def post(self, request, data):
        """Creates a new group for a user."""

        group_user = CoreHandler().create_group(request.user, name=data['name'])
        return Response(GroupUserSerializer(group_user).data)


class GroupView(APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get_group_user(user, group_id):
        try:
            group_user = GroupUser.objects.select_related('group') \
                .select_for_update().get(group_id=group_id, user=user)
        except GroupUser.DoesNotExist:
            # If the group user doesn't exist we should check if the group exist so we
            # can show a proper error.
            get_object_or_404(Group, id=group_id)
            raise UserNotInGroupError

        return group_user

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='group_id',
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description='Updates the group related to the provided value.'
            )
        ],
        tags=['Groups'],
        operation_id='update_group',
        description=(
            'Updates the existing group related to the provided `group_id` parameter '
            'if the authorized user belongs to the group. It is not yet possible to '
            'add additional users to a group.'
        ),
        request=GroupSerializer,
        responses={
            200: group_user_schema,
            400: get_error_schema([
                'ERROR_USER_NOT_IN_GROUP', 'ERROR_REQUEST_BODY_VALIDATION'
            ])
        }
    )
    @transaction.atomic
    @validate_body(GroupSerializer)
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def patch(self, request, data, group_id):
        """Updates the group if it belongs to a user."""

        group_user = self.get_group_user(request.user, group_id)
        group_user.group = CoreHandler().update_group(
            request.user,  group_user.group, name=data['name'])

        return Response(GroupUserSerializer(group_user).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='group_id',
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description='Deletes the group related to the provided value.'
            )
        ],
        tags=['Groups'],
        operation_id='delete_group',
        description=(
            'Deletes an existing group if the authorized user belongs to the group. '
            'All the applications, databases, tables etc that were in the group are '
            'going to be deleted also.'
        ),
        request=GroupSerializer,
        responses={
            200: group_user_schema,
            400: get_error_schema([
                'ERROR_USER_NOT_IN_GROUP', 'ERROR_REQUEST_BODY_VALIDATION'
            ])
        }
    )
    @transaction.atomic
    @map_exceptions({
        UserNotInGroupError: ERROR_USER_NOT_IN_GROUP
    })
    def delete(self, request, group_id):
        """Deletes an existing group if it belongs to a user."""

        group_user = self.get_group_user(request.user, group_id)
        CoreHandler().delete_group(request.user,  group_user.group)
        return Response(status=204)


class GroupOrderView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=['Groups'],
        operation_id='order_groups',
        description=(
            'Changes the order of the provided group ids to the matching position that '
            'the id has in the list. If the authorized user does not belong to the '
            'group it will be ignored. The order will be custom for each user.'
        ),
        request=OrderGroupsSerializer,
        responses={
            204: None,
        },
    )
    @validate_body(OrderGroupsSerializer)
    def post(self, request, data):
        """Updates to order of some groups for a user."""

        CoreHandler().order_groups(request.user, data['groups'])
        return Response(status=204)
