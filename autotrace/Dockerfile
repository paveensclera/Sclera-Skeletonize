FROM alpine:latest

WORKDIR /app

# Copy binary + needed libs
COPY autotrace /usr/local/bin/autotrace
COPY libs/* /usr/local/lib/

ENV LD_LIBRARY_PATH="/usr/local/lib"

ENTRYPOINT ["/usr/local/bin/autotrace"]
