FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-distutils \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch with CUDA 12.4 support before ultralytics
RUN pip install --no-cache-dir \
    torch \
    torchvision \
    --index-url https://download.pytorch.org/whl/cu124

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

ENV YOLO_CONFIG_DIR=/app/.yolo

EXPOSE 8000

CMD ["python", "main.py"]
