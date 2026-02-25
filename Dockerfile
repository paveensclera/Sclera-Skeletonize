FROM alpine

RUN apk add --no-cache potrace imagemagick libxml2-utils

WORKDIR /work

ENTRYPOINT ["sh", "-c"]