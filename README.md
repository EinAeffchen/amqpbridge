# amqpbridge

A minimal connector between postgresql and rabbitmq to write directly into queues

## Getting Started

Clone this repo, setup the environment with the appropriate URIs, build the container and fire up the compose:
```
# Clone this repository
git clone https://github.com/EinAeffchen/amqpbridge.git

# Go intoe the repository
cd amqpbridge

# Optionally build the container yourself and replace the image in docker-compose.yml with your local one:
docker build -t amqpbridge .
image: amqpbridge

# Setup the environment in docker-compose.yml
environment: 
    POSTGRESQL_URI: postgres://<user>:<password>@<host>:5432/<database>
    AMQP_URI: amqp://<user>:<password>@<host>:5672/<exchange>
    BRIDGE_CHANNELS: <notify channel>:<routing key>,<notify channel>:<routing key>
    
# Run the container setup
docker-compose up -d
```

### Prerequisites

For this project only docker and docker-compose are necessary

[Quickguide](https://phoenixnap.com/kb/install-docker-compose-ubuntu)

## Running the tests

To test the system or play around you can fire up the docker-compose_tst.yml:
```
docker-compose up -f docker-compose_tst.yml -d
```

This will start a postgresqldb, rabbitmq and the amqpbridge with the default URI for the test environment.
You need to setup two seperate queues in the dev Vhost. Bind the routing key amqpbridge to one queue and amqpbridge1 to another queue. (see BRIDGE_CHANNELS in Dockerfile)
When rabbitmq is setup you can start sending messages like this:
```
NOTIFY pgchannel1, 'test'
NOTIFY pgchannel2, 'test'
```
This should result in one message in each queue with the content "test"

## Built With

* [pika](https://pika.readthedocs.io/en/stable/index.html) - Rabbitmq connector
* [psycopg2](https://www.psycopg.org/) - Postgresql connector


## Authors

* **Leon Dummer** - *Initial work* - [EinAeffchen](https://github.com/EinAeffchen)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

This project is based on the amqpbridge written in rust by [subzerocloud](https://github.com/subzerocloud/pg-amqp-bridge)