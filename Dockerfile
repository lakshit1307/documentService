#FROM python:3.9-buster

FROM python:3.9
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /opt/app
RUN mkdir -p /opt/app/pip_cache
WORKDIR /opt/app

COPY documentService/requirements.txt /opt/app
COPY documentService /opt/app

RUN pip install -r requirements.txt

#RUN pip install -r requirements.txt --cache-dir /opt/app/pip_cache

#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "documentService/wsgi.py"]
#RUN python manage.py runserver
#EXPOSE 8000
#STOPSIGNAL SIGTERM