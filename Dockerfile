FROM python:3-alpine

COPY requirements.txt /
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
RUN pip3 install -r requirements.txt
RUN rm requirements.txt

COPY /src /src/amqpbridge

ENV POSTGRESQL_URI=postgres://admin:postgres@postgresql:5432/dev
ENV AMQP_URI=amqp://rabbitmq:rabbitmq@rabbitmq:5672/DEV
ENV BRIDGE_CHANNELS=pgchannel1:amqpbridge,pgchannel2:amqpbridge1
WORKDIR /src/amqpbridge
CMD ["python","./amqpbridge.py"]