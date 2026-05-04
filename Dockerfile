# ---------- STAGE 1: build ----------
FROM debian:stable-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    autoconf automake libtool \
    gettext autopoint intltool pkg-config \
    libpng-dev libjpeg-dev libtiff-dev \
    libmagickcore-dev libpstoedit-dev \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone https://github.com/autotrace/autotrace.git . && \
    git checkout 2d0b8cce456681ef5baf13f7264980330d1e443b && \
    ./autogen.sh && \
    ./configure --prefix=/usr/local && \
    make -j$(nproc) && \
    make install

# ---------- STAGE 2: runtime ----------
FROM debian:stable-slim

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    potrace imagemagick libxml2-utils \
    libpstoedit0t64 \
    libgl1 libglib2.0-0 \
    ca-certificates \
    time \
    && rm -rf /var/lib/apt/lists/*

# ---------- FIX IMAGEMAGICK LIMITS ----------
RUN find /etc /usr -name policy.xml -print0 | xargs -0 -r sed -i \
    -e 's/name="memory" value="[^"]*"/name="memory" value="16GiB"/' \
    -e 's/name="map" value="[^"]*"/name="map" value="32GiB"/' \
    -e 's/name="disk" value="[^"]*"/name="disk" value="64GiB"/'

# ---------- copy autotrace from builder ----------
COPY --from=builder /usr/local /usr/local
RUN ldconfig

# ---------- python ----------
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN /opt/venv/bin/pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    scikit-image \
    svgpathtools \
    scipy \
    pillow \
    fastapi \
    "uvicorn[standard]" \
    runpod

# ---------- app ----------
WORKDIR /app
COPY skeletonize.py .
COPY linearize.py .
COPY merge.sh .
COPY pipeline.sh .
COPY app.py .
COPY handler.py .

RUN sed -i 's/\r$//' merge.sh pipeline.sh && chmod +x merge.sh pipeline.sh

ENTRYPOINT ["python3", "-u", "/app/handler.py"]