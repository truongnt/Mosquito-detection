FROM docker:27-cli

RUN apk add --no-cache bash git openssh-client ca-certificates tzdata

WORKDIR /opt/mosquito/Mosquito-detection

COPY deploy-loop.sh /usr/local/bin/deploy-loop.sh
RUN chmod +x /usr/local/bin/deploy-loop.sh

CMD ["/usr/local/bin/deploy-loop.sh"]
