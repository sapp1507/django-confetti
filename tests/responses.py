from rest_framework.response import Response


def custom_response(*, data=None, code=200, status='success'):
    return Response(
        {
            'status': status,
            'data': {} if data is None else data,
        },
        status=code,
    )
