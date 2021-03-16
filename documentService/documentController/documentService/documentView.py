from documentController.documentService.documentSerializer \
    import DocumentSerializer, DocumentRequestSerializer, DocumentPermissionSerializer
from documentController.models import Document, DocUser, DocumentPermissions, DocumentEdits
from django.http import HttpResponse, JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view
import logging
import time
import os
from documentController.constants import *
import mimetypes
from django.db.utils import IntegrityError
from rest_framework.parsers import FileUploadParser
from documentController.ExceptionHandler import returnExceptionResult

logger = logging.getLogger("Document_View_Service")


@api_view([GET, POST])
def document_control(request):
    #
    # """
    # List all users.
    # """
    if request.method == GET:
        try:
            return getDocument()
        except Exception as e:
            return returnExceptionResult(e, logger)

    elif request.method == POST:
        try:
            return createDocument(request)
        except Exception as e:
            return returnExceptionResult(e, logger)


@api_view([GET])
def downloadDocument(request, docId, userId):
    """
    downlaod document specified by @docId for the user with userId @userId
    """
    try:
        try:
            document = Document.objects.get(pk=docId)
        except Document.DoesNotExist:
            response_data = {RESULT: FAILURE, MESSAGE: 'Document not found'}
            return JsonResponse(response_data, status=404)

        # Assuming that permissions are required for downloading: check for permissions
        if userId != document.ownerId.userId and not isDocumentPermissionForUser(document, userId):
            response_data = {RESULT: FAILURE, MESSAGE: 'User not authorised'}
            return JsonResponse(response_data, status=401)

        if request.method == GET:
            # check if owner is updating the document
            if not isOwnerUpdatingDocument(document):
                try:
                    return downloadFile(document.docPath, document.docName, userId == document.ownerId.userId)
                    # response_data = {RESULT: SUCCESS}
                    # return JsonResponse(response_data, status=201)
                except Exception:
                    response_data = {RESULT: FAILURE, MESSAGE: ERROR_MESSAGE}
                    return JsonResponse(response_data, status=500)
            else:
                response_data = {RESULT: FAILURE, MESSAGE: 'Owner is performing edits. Access denied'}
                return JsonResponse(response_data, status=401)
    except Exception as e:
        return returnExceptionResult(e, logger)


@api_view([POST])
def updateDocumentStart(request, docId, userId):
    try:
        doc = Document(documentId=docId)
        user = DocUser(userId=userId)

        if request.method == POST:
            try:
                try:
                    document = Document.objects.get(pk=docId)
                except Document.DoesNotExist:
                    response_data = {RESULT: FAILURE, MESSAGE: 'Document not found'}
                    return JsonResponse(response_data, status=404)
                # Check if document has permissions for edit and if the owner is performing any edits
                if isDocumentPermissionForUser(document, userId) and not isOwnerUpdatingDocument(document):
                    # create a record stating that the user has started editing the file
                    documentEdit = DocumentEdits(userId=user, documentId=doc)
                    documentEdit.save()
                    response_data = {RESULT: SUCCESS}
                    return JsonResponse(response_data, status=201)
                else:
                    # Unauthorize
                    response_data = {RESULT: FAILURE, MESSAGE: 'Access denied'}
                    return JsonResponse(response_data, status=401)

            except IntegrityError:
                logger.error("Error while fetching user and/or documents")
                response_data = {RESULT: FAILURE, MESSAGE: 'Document/User not found'}
                return JsonResponse(response_data, status=404)
    except Exception as e:
        return returnExceptionResult(e, logger)


@api_view([POST])
def updateDocumentEnd(request, docId, userId):
    """
    finish updating the file
    """

    try:
        document = Document(documentId=docId)
        user = DocUser(userId=userId)
        docEdit=isUserUpdatingDocument(document, userId)
        if not docEdit:
            response_data = {RESULT: FAILURE, MESSAGE: 'User is not permforming edits yet.'}
            return JsonResponse(response_data, status=401)
        if request.method == POST:
            try:
                try:
                    doc = Document.objects.get(pk=docId)
                except Document.DoesNotExist:
                    response_data = {RESULT: FAILURE, MESSAGE: 'Document not found'}
                    return JsonResponse(response_data, status=404)
                if userId == doc.ownerId.userId or not isOwnerUpdatingDocument(doc):
                    # TODO: if the edit has been cancelled then remove the edit and ask user to reload
                    if docEdit.editIsValid:
                        uploadFile(request, doc.docPath, doc.docName)
                    # TODO: if file has been opened for other edits then cancel those edits
                        invalidateEdits(document)
                        response_data = {RESULT: SUCCESS}
                        status=200
                    else:
                        response_data = {RESULT: FAILURE, MESSAGE: "Reload the document"}
                        status=406
                    docEdit.delete()

                    return JsonResponse(response_data, status=status)
                else:
                    response_data = {RESULT: FAILURE, MESSAGE: 'Owner is performing edits. Access denied'}
                    return JsonResponse(response_data, status=401)

            except IntegrityError:
                logger.error("Error while fetching user and/or documents")
                response_data = {RESULT: FAILURE, MESSAGE: 'Document/User not found'}
                return JsonResponse(response_data, status=404)
    except Exception as e:
        return returnExceptionResult(e, logger)


#
# @api_view([GET])
# def getDocumentById(request, docId, document=None):
#     try:
#         document = Document.objects.get(pk=docId)
#     except Document.DoesNotExist:
#         return HttpResponse(status=404)
#
#     if request.method == GET:
#         serializer = DocumentSerializer(document)
#         return JsonResponse(serializer.data, status=201)
#
#     if request.method == PUT:
#         # TODO: Check for permission
#         # TODO: if owner then hold for everyone
#         #
#         logger.info("")
#         # TODO: DELETE FILE AND ADD THE @document


@api_view([POST])
def grantDocumentPermission(request):
    """
    grant permission to a user by the owner of the document
    """

    try:
        data = JSONParser().parse(request)
        ownerId = data["ownerId"]
        docId = data["documentId"]
        userId = data["userId"]

        try:
            document = Document.objects.get(pk=docId)
        except Document.DoesNotExist:
            logger.warning("Document with docId: " + str(docId) + " not found")
            response_data = {RESULT: FAILURE, MESSAGE: 'Document not found'}
            return JsonResponse(response_data, status=404)

        # if the requesting user is not the owner, then deny access
        if document.ownerId.userId != ownerId:
            response_data = {RESULT: FAILURE, MESSAGE: 'Not enough permissions to grant access'}
            return JsonResponse(response_data, status=401)

        # try:
        #     user = DocUser.objects.get(pk=userId)
        # except DocUser.DoesNotExist:
        #     logger.warning("User with userId: " + userId + " not found")
        #     response_data = {RESULT: FAILURE, MESSAGE: 'User not found'}
        #     return JsonResponse(response_data, status=404)

        # if owner is requesting access for itself then state that user already has access
        if ownerId == userId:
            response_data = {RESULT: SUCCESS, MESSAGE: 'Already an owner'}
            return JsonResponse(response_data, status=200)

        try:
            # add permissions to DB
            documentPermission = DocumentPermissions(documentId=Document(documentId=data["documentId"]),
                                                     userId=DocUser(userId=data["userId"]))
            documentPermission.save()

            response_data = {RESULT: SUCCESS, MESSAGE: 'Succesfully saved in DB'}
            return JsonResponse(response_data, status=201)

        # in case of permissions being already present, state that permission exists
        except IntegrityError:
            response_data = {RESULT: SUCCESS, MESSAGE: 'Already has permissions'}
            return JsonResponse(response_data, status=200)

    except Exception as e:
        return returnExceptionResult(e, logger)


def createDocument(request):
    """
    create a document
    """
    response_data = {}
    data = JSONParser().parse(request)
    # add timestamp to fileName in case of multiple files with the same fileName
    fileName = data["docName"] + current_milli_time() + ".txt"
    filePath = addFile(fileName)

    if (filePath == False):
        # TODO: Can retry after a milliSecondToSaveIt Again
        # Avoid retry ideally as it could be due to the same Request being sent multiple times
        logger.error('File Already exists with the same name on this milliSecond')
        response_data[RESULT] = FAILURE
        response_data[MESSAGE] = ERROR_MESSAGE
        return JsonResponse(response_data, status=500)

    # save the file details to the DB
    data["docPath"] = filePath
    document = Document(docName=data["docName"], docPath=filePath, ownerId=DocUser(userId=data["ownerId"]))
    document.save()
    # serializer = DocumentRequestSerializer(data=data)
    # if serializer.is_valid():
    #     serializer.save()
    response_data[RESULT] = SUCCESS
    response_data[MESSAGE] = 'Succesfully saved in DB'
    return JsonResponse(response_data, status=201)


def getDocument():
    """
    get the list of all document
    """
    # get document details
    querySet = Document.objects.all()
    serializer = DocumentSerializer(querySet, many=True)
    logger.info("Succesfully fetched all the list of users")
    return JsonResponse(serializer.data, safe=False)


def addFile(fileName):
    """
    add file to the document repository
    """
    filePath = 'documentController/documentRepository/' + fileName
    if not os.path.exists(filePath):
        open(filePath, 'w').close()
        return filePath
    return False


# get current time
def current_milli_time():
    return round(time.time() * 1000).__str__()


def downloadFile(filePath, fileName, isOwner):
    fl = open(filePath, 'r')
    mime_type, _ = mimetypes.guess_type(filePath)
    response = HttpResponse(fl, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % fileName
    if isOwner:
        logger.info("Owner - Download")
    else:
        logger.info("Collaborator - Download")
    return response


def uploadFile(request, filePath, fileName):
    parser_classes = (FileUploadParser,)
    file_obj = request.FILES['file']
    os.remove(filePath)
    destination = open(filePath, 'wb+')
    for chunk in file_obj.chunks():
        destination.write(chunk)
    destination.close()  # File should be closed only after all chuns are added


def isOwnerUpdatingDocument(document):
    """
    Check if owner is updating the document
    """
    return isUserUpdatingDocument(document, document.ownerId)


def isUserUpdatingDocument(document, userId):
    """
    check if user is updating the document
    """
    docEdits = DocumentEdits.objects.filter(documentId=document.documentId, userId=userId)
    if docEdits.count() == 0:
        return False
    return docEdits[0]


def isDocumentPermissionForUser(document, userId):
    """
    check if user has permission for the document
    """
    if document.ownerId.userId == userId:
        return True
    docPermission = DocumentPermissions.objects.filter(documentId=document.documentId, userId=userId)
    if docPermission.count() == 0:
        return False
    return True

def invalidateEdits(document):
    docEdits = DocumentEdits.objects.filter(documentId=document.documentId).update(editIsValid=False)
