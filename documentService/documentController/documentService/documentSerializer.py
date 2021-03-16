from documentController.models import Document,DocumentPermissions
from rest_framework import serializers

class DocumentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Document
        fields = ['documentId', 'docName', 'ownerId', 'docPath']

class DocumentRequestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Document
        fields = ['docName', 'ownerId', 'docPath']

class DocumentPermissionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = DocumentPermissions
        fields = ['userId', 'documentId']