FROM alpine

RUN apk add --no-cache potrace imagemagick libxml2-utils

WORKDIR /work

CMD sh -c "magick reco1.png -threshold 99% reco1.pbm && \
           potrace reco1.pbm -s -o reco1.svg"