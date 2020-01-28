FROM python:3.6-alpine
MAINTAINER m@bitsnbites.eu

RUN apk add --update \
    git \
  && rm -rf /var/cache/apk/*

ENV REFREPO_ACE_ROOT_DIR=/var/refrepo           \
    REFREPO_ACE_REPO=refrepo.git                \
    REFREPO_ACE_CONF_DIR=conf                   \
    REFREPO_UPDATER_INTERVAL_SECONDS=60

COPY refrepo-updater.sh /usr/local/bin/
COPY refrepo_ace.py /usr/local/bin/

ENTRYPOINT []
CMD ["refrepo-updater.sh"]
