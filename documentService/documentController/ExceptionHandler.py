from django.http import JsonResponse
from documentController.constants import *


def returnExceptionResult(exception, logger):
    logger.error(exception)
    response_data = {RESULT: FAILURE, MESSAGE: ERROR_MESSAGE}
    return JsonResponse(response_data, status=500)